import csv
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .. import settings
from .lemma_bank import lemma_key, normalize_lemma
from .pos_tags import PAPYGREEK_POS_NAMES, UNIVERSAL_TAGS

logger = logging.getLogger(__name__)

LEMMA_DECISION_COLUMNS = ["lemma", "papygreek_pos", "ligre_pos", "decision", "ligre_lemma", "note"]
CORRECTED = "corrected"


class LemmaDecision(Enum):
    CONVENTION = "convention"
    LIGRE_POS_WRONG = "ligre-pos-wrong"
    PAPYGREEK_POS_WRONG = "papygreek-pos-wrong"
    SAME_WORD = "same-word"
    REJECT = "reject"

    @property
    def links(self):
        return self is not LemmaDecision.REJECT


@dataclass(frozen=True)
class Decision:
    kind: Optional[LemmaDecision]
    ligre_lemma: Optional[str] = None

    @property
    def links(self):
        return self.kind is None or self.kind.links

    @property
    def value(self):
        return self.kind.value if self.kind else CORRECTED


@dataclass(frozen=True)
class PosDecisions:
    lemma_decisions: dict = field(default_factory=dict)

    def decision_for(self, lemma, papygreek_pos, ligre_tags):
        return (self.homograph_decision_for(lemma, papygreek_pos, ligre_tags)
                or self.find(normalize_lemma(lemma), papygreek_pos, ligre_tags))

    def homograph_decision_for(self, lemma, papygreek_pos, ligre_tags):
        return self.find(lemma_key(lemma), papygreek_pos, ligre_tags)

    def find(self, key, papygreek_pos, ligre_tags):
        for tag in sorted(ligre_tags):
            decision = self.lemma_decisions.get((key, papygreek_pos, tag))
            if decision is not None:
                return decision
        return None


class DecisionFileError(ValueError):
    pass


def read_decision_rows(path, columns):
    with path.open(newline="", encoding="utf-8") as decision_file:
        reader = csv.DictReader(decision_file, delimiter="\t")
        if reader.fieldnames != columns:
            raise DecisionFileError(f"{path}: expected the columns {columns}, found {reader.fieldnames}")
        for line_number, row in enumerate(reader, start=2):
            values = {column: (row[column] or "").strip() for column in columns}
            if any(values.values()):
                yield line_number, values


def check_pos_names(path, line_number, row):
    if row["papygreek_pos"] not in PAPYGREEK_POS_NAMES:
        raise DecisionFileError(
            f"{path}:{line_number}: unknown papygreek_pos {row['papygreek_pos']!r}, "
            f"use one of {sorted(PAPYGREEK_POS_NAMES)}"
        )
    if row["ligre_pos"] not in UNIVERSAL_TAGS:
        raise DecisionFileError(
            f"{path}:{line_number}: unknown ligre_pos {row['ligre_pos']!r}, use one of {sorted(UNIVERSAL_TAGS)}"
        )


def read_lemma_decisions(path):
    lemma_decisions = {}
    decision_values = [decision.value for decision in LemmaDecision]
    for line_number, row in read_decision_rows(path, LEMMA_DECISION_COLUMNS):
        check_pos_names(path, line_number, row)
        ligre_lemma = row["ligre_lemma"] or None
        if not row["decision"] and not ligre_lemma:
            raise DecisionFileError(f"{path}:{line_number}: give a decision, a ligre_lemma or both")
        if row["decision"] and row["decision"] not in decision_values:
            raise DecisionFileError(
                f"{path}:{line_number}: unknown decision {row['decision']!r}, use one of {decision_values}"
            )
        kind = LemmaDecision(row["decision"]) if row["decision"] else None
        if kind is LemmaDecision.REJECT and ligre_lemma:
            raise DecisionFileError(f"{path}:{line_number}: a rejected lemma cannot have a ligre_lemma")
        key = (lemma_key(row["lemma"]), row["papygreek_pos"], row["ligre_pos"])
        if key in lemma_decisions:
            raise DecisionFileError(f"{path}:{line_number}: a decision for {key} is already given above")
        lemma_decisions[key] = Decision(kind, ligre_lemma)
    return lemma_decisions


def check_ligre_lemmas(decisions, lemma_bank):
    unknown = sorted({
        decision.ligre_lemma for decision in decisions.lemma_decisions.values()
        if decision.ligre_lemma and lemma_bank.entry(decision.ligre_lemma) is None
    })
    if unknown:
        raise DecisionFileError(f"unknown LiGre lemma ids in ligre_lemma: {', '.join(unknown)}")


def write_header_if_missing(path, columns):
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as decision_file:
        csv.writer(decision_file, delimiter="\t").writerow(columns)
    logger.info("Created the empty decision file %s", path)


def load_pos_decisions(decisions_directory):
    lemma_decisions_path = decisions_directory / settings.LEMMA_POS_DECISIONS_FILENAME
    write_header_if_missing(lemma_decisions_path, LEMMA_DECISION_COLUMNS)
    decisions = PosDecisions(read_lemma_decisions(lemma_decisions_path))
    logger.info("Loaded %d lemma PoS decisions from %s", len(decisions.lemma_decisions), decisions_directory)
    return decisions
