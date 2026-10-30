from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .pos_decisions import LemmaDecision
from .pos_tags import papygreek_pos, strict_universal_tags


class LinkStep(Enum):
    STRICT = "strict"
    LEMMA_DECISION = "lemma decision"
    UNDECIDED_POS_CLASH = "undecided pos clash"
    REJECTED = "rejected"
    AMBIGUOUS = "ambiguous"
    MISSING = "lemma not in LiGre"


LINKING_STEPS = {LinkStep.STRICT, LinkStep.LEMMA_DECISION}


@dataclass(frozen=True)
class LinkResult:
    step: LinkStep
    papygreek_pos: str
    candidates: tuple
    pos_clash: bool = False
    lemma: Optional[object] = None
    decision: Optional[LemmaDecision] = None

    @property
    def is_linked(self):
        return self.step in LINKING_STEPS


class LemmaLinker:
    def __init__(self, lemma_bank, pos_decisions):
        self.lemma_bank = lemma_bank
        self.pos_decisions = pos_decisions

    def link(self, word):
        pos = papygreek_pos(word.postag)
        candidates = tuple(self.lemma_bank.candidates(word.lemma))
        if not candidates:
            return LinkResult(LinkStep.MISSING, pos, candidates)
        expected_tags = strict_universal_tags(pos)
        strict_candidates = [candidate for candidate in candidates if candidate.universal_tags & expected_tags]
        if strict_candidates:
            return link_single(LinkStep.STRICT, strict_candidates, pos, candidates)
        return self.resolve_pos_clash(word.lemma, pos, candidates)

    def resolve_pos_clash(self, lemma, pos, candidates):
        decisions = {
            candidate: self.pos_decisions.decision_for(lemma, pos, candidate.universal_tags)
            for candidate in candidates
        }
        decided_links = [candidate for candidate, decision in decisions.items() if decision and decision.links]
        if decided_links:
            return link_single(LinkStep.LEMMA_DECISION, decided_links, pos, candidates, decisions[decided_links[0]])
        undecided = any(decision is None for decision in decisions.values())
        step = LinkStep.UNDECIDED_POS_CLASH if undecided else LinkStep.REJECTED
        return LinkResult(step, pos, candidates, pos_clash=True)


def link_single(step, matching_candidates, pos, candidates, decision=None):
    pos_clash = step is not LinkStep.STRICT
    if len(matching_candidates) > 1:
        return LinkResult(LinkStep.AMBIGUOUS, pos, candidates, pos_clash)
    return LinkResult(step, pos, candidates, pos_clash, matching_candidates[0].lemma, decision)
