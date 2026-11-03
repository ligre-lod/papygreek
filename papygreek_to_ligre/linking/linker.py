from dataclasses import dataclass, replace
from enum import Enum
from typing import Optional

from .lemma_bank import has_homograph_number
from .pos_decisions import LemmaDecision, check_ligre_lemmas
from .pos_tags import lila_gender, papygreek_pos, strict_universal_tags


class LinkStep(Enum):
    STRICT = "strict"
    LEMMA_DECISION = "lemma decision"
    UNDECIDED_POS_CLASH = "undecided pos clash"
    UNDECIDED_HOMOGRAPH = "undecided homograph"
    REJECTED = "rejected"
    AMBIGUOUS = "ambiguous"
    MISSING = "lemma not in LiGre"


LINKING_STEPS = {LinkStep.STRICT, LinkStep.LEMMA_DECISION}


@dataclass(frozen=True)
class LinkResult:
    step: LinkStep
    papygreek_pos: str
    candidates: tuple
    in_review: bool = False
    lemma: Optional[object] = None
    decision: Optional[object] = None
    homograph_check: bool = False

    @property
    def is_linked(self):
        return self.step in LINKING_STEPS


class LemmaLinker:
    def __init__(self, lemma_bank, pos_decisions):
        check_ligre_lemmas(pos_decisions, lemma_bank)
        self.lemma_bank = lemma_bank
        self.pos_decisions = pos_decisions

    def link(self, word):
        pos = papygreek_pos(word.postag)
        candidates = tuple(self.lemma_bank.candidates(word.lemma))
        if not candidates:
            return LinkResult(LinkStep.MISSING, pos, candidates)
        gender = lila_gender(word.postag) if pos == "noun" else None
        expected_tags = strict_universal_tags(pos)
        strict_candidates = [candidate for candidate in candidates if candidate.universal_tags & expected_tags]
        if strict_candidates:
            result = link_single(LinkStep.STRICT, strict_candidates, pos, candidates, gender=gender)
            if result.step is LinkStep.AMBIGUOUS:
                result = self.resolve_ambiguity(word.lemma, result)
        else:
            result = self.resolve_pos_clash(word.lemma, pos, candidates, gender)
        return self.check_homograph(word.lemma, result)

    def check_homograph(self, lemma, result):
        if not (result.is_linked and has_homograph_number(lemma) and len(result.candidates) == 1):
            return result
        ligre_tags = result.candidates[0].universal_tags
        decision = self.pos_decisions.homograph_decision_for(lemma, result.papygreek_pos, ligre_tags)
        if decision is None:
            return replace(result, step=LinkStep.UNDECIDED_HOMOGRAPH, in_review=True, lemma=None, decision=None,
                           homograph_check=True)
        if not decision.links:
            return replace(result, step=LinkStep.REJECTED, in_review=True, lemma=None, decision=decision,
                           homograph_check=True)
        if decision.ligre_lemma:
            return replace(result, step=LinkStep.LEMMA_DECISION, in_review=True, lemma=self.chosen_lemma(decision),
                           decision=decision, homograph_check=True)
        return replace(result, step=LinkStep.LEMMA_DECISION, in_review=True, decision=decision, homograph_check=True)

    def resolve_ambiguity(self, lemma, result):
        ligre_tags = frozenset(tag for candidate in result.candidates for tag in candidate.universal_tags)
        decision = self.pos_decisions.decision_for(lemma, result.papygreek_pos, ligre_tags)
        if decision is None:
            return replace(result, in_review=True)
        if not decision.links:
            return replace(result, step=LinkStep.REJECTED, in_review=True, decision=decision)
        if decision.ligre_lemma is None:
            return replace(result, in_review=True, decision=decision)
        return replace(result, step=LinkStep.LEMMA_DECISION, in_review=True, lemma=self.chosen_lemma(decision),
                       decision=decision)

    def chosen_lemma(self, decision):
        return self.lemma_bank.entry(decision.ligre_lemma).lemma if decision.ligre_lemma else None

    def resolve_pos_clash(self, lemma, pos, candidates, gender):
        decisions = {
            candidate: self.pos_decisions.decision_for(lemma, pos, candidate.universal_tags)
            for candidate in candidates
        }
        decided_links = [candidate for candidate, decision in decisions.items() if decision and decision.links]
        if decided_links:
            decision = decisions[decided_links[0]]
            if decision.ligre_lemma:
                return LinkResult(LinkStep.LEMMA_DECISION, pos, candidates, True, self.chosen_lemma(decision), decision)
            return link_single(LinkStep.LEMMA_DECISION, decided_links, pos, candidates, decision, gender)
        undecided = any(decision is None for decision in decisions.values())
        step = LinkStep.UNDECIDED_POS_CLASH if undecided else LinkStep.REJECTED
        return LinkResult(step, pos, candidates, in_review=True)


def link_single(step, matching_candidates, pos, candidates, decision=None, gender=None):
    in_review = step is not LinkStep.STRICT
    if len(matching_candidates) > 1 and gender is not None:
        same_gender = [candidate for candidate in matching_candidates if gender in candidate.genders]
        matching_candidates = same_gender or matching_candidates
    if len(matching_candidates) > 1:
        return LinkResult(LinkStep.AMBIGUOUS, pos, candidates, in_review, decision=decision)
    return LinkResult(step, pos, candidates, in_review, matching_candidates[0].lemma, decision)
