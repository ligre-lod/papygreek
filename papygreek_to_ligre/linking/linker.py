from dataclasses import dataclass, replace
from enum import Enum
from typing import Optional

from .lemma_bank import has_homograph_number
from .not_a_word import NotAWord
from .pos_decisions import LigreChangeKind, check_ligre_lemmas
from .pos_tags import LILA_GENDER_BY_AGDT_TAG, lila_gender, papygreek_pos, strict_universal_tags


class LinkStep(Enum):
    STRICT = "strict"
    LEMMA_DECISION = "lemma decision"
    UNDECIDED_POS_CLASH = "undecided pos clash"
    UNDECIDED_HOMOGRAPH = "undecided homograph"
    HOMOGRAPH = "homograph linked to the only LiGre lemma"
    REJECTED = "rejected"
    TO_ADD_TO_LIGRE = "waits for a lemma LiGre will add"
    AMBIGUOUS = "ambiguous"
    MISSING = "lemma not in LiGre"
    NOT_A_WORD = "not a word"


LINKING_STEPS = {LinkStep.STRICT, LinkStep.LEMMA_DECISION, LinkStep.HOMOGRAPH}


@dataclass(frozen=True)
class LinkResult:
    step: LinkStep
    papygreek_pos: str
    candidates: tuple
    in_review: bool = False
    lemma: Optional[object] = None
    decision: Optional[object] = None
    homograph_check: bool = False
    not_a_word: Optional[str] = None
    extra_lemmas: tuple = ()

    @property
    def is_linked(self):
        return self.step in LINKING_STEPS


class LemmaLinker:
    def __init__(self, lemma_bank, pos_decisions, not_a_word=None):
        check_ligre_lemmas(pos_decisions, lemma_bank)
        self.lemma_bank = lemma_bank
        self.pos_decisions = pos_decisions
        self.not_a_word = not_a_word or NotAWord()

    def link(self, word):
        pos = papygreek_pos(word.postag)
        marker = self.not_a_word.marker(word)
        if marker is not None:
            return LinkResult(LinkStep.NOT_A_WORD, pos, (), not_a_word=marker)
        candidates = tuple(self.lemma_bank.candidates(word.lemma))
        if not candidates:
            decision = self.pos_decisions.missing_lemma_decision_for(word.lemma, pos)
            if decision is None:
                return LinkResult(LinkStep.MISSING, pos, candidates)
            return self.apply_decision(pos, candidates, decision, [])
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
            # LiGre does not distinguish homographs (it has one lemma per spelling, part of speech and gender),
            # so a numbered PapyGreek homograph links to the only LiGre lemma with its spelling, unless a
            # decision links it elsewhere.
            return replace(result, step=LinkStep.HOMOGRAPH, in_review=True, homograph_check=True)
        return self.apply_decision(result.papygreek_pos, result.candidates, decision, list(result.candidates),
                                   homograph_check=True)

    def resolve_ambiguity(self, lemma, result):
        ligre_tags = frozenset(tag for candidate in result.candidates for tag in candidate.universal_tags)
        decision = self.pos_decisions.decision_for(lemma, result.papygreek_pos, ligre_tags)
        if decision is None:
            return replace(result, in_review=True)
        return self.apply_decision(result.papygreek_pos, result.candidates, decision, list(result.candidates))

    def resolve_pos_clash(self, lemma, pos, candidates, gender):
        decisions = {
            candidate: self.pos_decisions.decision_for(lemma, pos, candidate.universal_tags)
            for candidate in candidates
        }
        decided = [candidate for candidate, decision in decisions.items() if decision]
        if decided:
            return self.apply_decision(pos, candidates, decisions[decided[0]], decided, gender)
        current_tags = frozenset(tag for candidate in candidates for tag in candidate.universal_tags)
        decision = self.pos_decisions.outdated_decision_for(lemma, pos, current_tags)
        if decision is None:
            return LinkResult(LinkStep.UNDECIDED_POS_CLASH, pos, candidates, in_review=True)
        corrected = [candidate for candidate in candidates if candidate.lemma_id == decision.ligre_change.ligre_id]
        return self.apply_decision(pos, candidates, decision, corrected or list(candidates), gender)

    def apply_decision(self, pos, candidates, decision, matching, gender=None, homograph_check=False):
        """Link the tokens where the decision says: to the lemma LiGre will add, to the LiGre lemmas in
        ligre_lemma, or else to the LiGre lemma with PapyGreek's spelling."""
        if decision.adds_to_ligre:
            added = self.added_lemma(decision.ligre_change)
            if added is None:
                return LinkResult(LinkStep.TO_ADD_TO_LIGRE, pos, candidates, True, decision=decision,
                                  homograph_check=homograph_check)
            return LinkResult(LinkStep.LEMMA_DECISION, pos, candidates, True, added, decision, homograph_check)
        corrected_entry = self.lemma_bank.entry(decision.ligre_change.ligre_id) if decision.ligre_change.ligre_id else None
        if decision.adds_spelling_to_ligre:
            if corrected_entry is None:
                return LinkResult(LinkStep.MISSING, pos, candidates, decision=decision)
            return LinkResult(LinkStep.LEMMA_DECISION, pos, candidates, True, corrected_entry.lemma, decision,
                              homograph_check)
        if not matching and not decision.ligre_lemmas and decision.ligre_change.kind is LigreChangeKind.CORRECT \
                and corrected_entry is not None:
            lemma = corrected_entry.lemma
            return LinkResult(LinkStep.LEMMA_DECISION, pos, candidates, True, lemma, decision, homograph_check)
        if not matching and not decision.ligre_lemmas:
            return LinkResult(LinkStep.MISSING, pos, candidates, decision=decision)
        if decision.ligre_lemmas:
            first, *others = [self.lemma_bank.entry(lemma_id).lemma for lemma_id in decision.ligre_lemmas]
            return LinkResult(LinkStep.LEMMA_DECISION, pos, candidates, True, first, decision, homograph_check,
                              extra_lemmas=tuple(others))
        return replace(link_single(LinkStep.LEMMA_DECISION, matching, pos, candidates, decision, gender),
                       homograph_check=homograph_check)

    def added_lemma(self, change):
        gender = LILA_GENDER_BY_AGDT_TAG.get(change.gender) if change.gender else None
        matches = [
            entry for entry in self.lemma_bank.candidates(change.lemma)
            if change.universal_tag in entry.universal_tags and (gender is None or gender in entry.genders)
        ]
        return matches[0].lemma if len(matches) == 1 else None


def link_single(step, matching_candidates, pos, candidates, decision=None, gender=None):
    in_review = step is not LinkStep.STRICT
    if len(matching_candidates) > 1 and gender is not None:
        same_gender = [candidate for candidate in matching_candidates if gender in candidate.genders]
        matching_candidates = same_gender or matching_candidates
    if len(matching_candidates) > 1:
        return LinkResult(LinkStep.AMBIGUOUS, pos, candidates, in_review, decision=decision)
    return LinkResult(step, pos, candidates, in_review, matching_candidates[0].lemma, decision)
