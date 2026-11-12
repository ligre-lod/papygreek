import csv
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .. import settings
from .lemma_bank import lemma_key, normalize_lemma
from .pos_tags import LILA_GENDER_BY_AGDT_TAG, PAPYGREEK_POS_NAMES, UNIVERSAL_TAGS
from .wr_lv_decisions import lemma_decision_rows, read_wr_lv_rows

logger = logging.getLogger(__name__)

LIGRE_CHANGE_COLUMNS = ["ligre_change", "ligre_id", "ligre_new_lemma", "ligre_new_pos", "ligre_new_gender",
                        "ligre_variant_of"]
LEMMA_DECISION_COLUMNS = ["lemma", "papygreek_pos", "ligre_pos", "decision", "ligre_lemma",
                          *LIGRE_CHANGE_COLUMNS]
POS_INFORMATION_COLUMNS = ["status", "tokens", "candidates"]
POS_DECISION_FILE_COLUMNS = [*LEMMA_DECISION_COLUMNS, *POS_INFORMATION_COLUMNS]
DECIDING_COLUMNS = ["decision", "ligre_lemma", *LIGRE_CHANGE_COLUMNS]
CORRECTED = "corrected"
GENDERED_TAGS = {"NOUN", "PROPN"}


class LigreChangeKind(Enum):
    NONE = "none"
    CORRECT = "correct"
    ADD = "add"
    ADD_WR = "add-wr"


@dataclass(frozen=True)
class LigreChange:
    kind: LigreChangeKind
    ligre_id: Optional[str] = None
    lemma: Optional[str] = None
    universal_tag: Optional[str] = None
    gender: Optional[str] = None
    variant_of: Optional[str] = None


class LemmaDecision(Enum):
    CONVENTION = "convention"
    LIGRE_POS_WRONG = "ligre-pos-wrong"
    PAPYGREEK_POS_WRONG = "papygreek-pos-wrong"
    SAME_WORD = "same-word"
    PAPYGREEK_LEMMA_DIFFERS = "papygreek-lemma-differs"
    PAPYGREEK_LEMMA_WRONG = "papygreek-lemma-wrong"
    LIGRE_LEMMA_MISSING = "ligre-lemma-missing"
    LIGRE_SPELLING_MISSING = "ligre-spelling-missing"
    LIGRE_SPELLING_WRONG = "ligre-spelling-wrong"
    CRASIS = "crasis"


@dataclass(frozen=True)
class Decision:
    kind: Optional[LemmaDecision]
    ligre_lemmas: tuple = ()
    ligre_change: LigreChange = LigreChange(LigreChangeKind.NONE)

    @property
    def adds_to_ligre(self):
        return self.ligre_change.kind is LigreChangeKind.ADD

    @property
    def adds_spelling_to_ligre(self):
        return self.ligre_change.kind is LigreChangeKind.ADD_WR

    @property
    def value(self):
        return self.kind.value if self.kind else CORRECTED


@dataclass(frozen=True)
class PosDecisions:
    lemma_decisions: dict = field(default_factory=dict)

    def decision_for(self, lemma, papygreek_pos, ligre_tags):
        return (self.homograph_decision_for(lemma, papygreek_pos, ligre_tags)
                or self.find(normalize_lemma(lemma), papygreek_pos, ligre_tags))

    def missing_lemma_decision_for(self, lemma, papygreek_pos):
        return self.decision_for(lemma, papygreek_pos, UNIVERSAL_TAGS)

    def homograph_decision_for(self, lemma, papygreek_pos, ligre_tags):
        return self.find(lemma_key(lemma), papygreek_pos, ligre_tags)

    def find(self, key, papygreek_pos, ligre_tags):
        for tag in sorted(ligre_tags):
            decision = self.lemma_decisions.get((key, papygreek_pos, tag))
            if decision is not None:
                return decision
        return None

    def outdated_decision_for(self, lemma, papygreek_pos, current_tags):
        for key in (lemma_key(lemma), normalize_lemma(lemma)):
            decisions = [decision for (decided_lemma, decided_pos, tag), decision in self.lemma_decisions.items()
                         if decided_lemma == key and decided_pos == papygreek_pos and tag not in current_tags]
            targets = {decision.ligre_lemmas or (decision.ligre_change.ligre_id,) for decision in decisions}
            if decisions and len(targets) == 1:
                return decisions[0]
            if decisions:
                return None
        return None


class DecisionFileError(ValueError):
    pass


def is_undecided(row):
    return not any(row[column] for column in DECIDING_COLUMNS)


def read_pos_file_rows(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as decision_file:
        reader = csv.DictReader(decision_file, delimiter="\t")
        if (reader.fieldnames or [])[:len(LEMMA_DECISION_COLUMNS)] != LEMMA_DECISION_COLUMNS:
            raise DecisionFileError(f"{path}: expected the columns {POS_DECISION_FILE_COLUMNS}, found {reader.fieldnames}")
        return [{column: (row.get(column) or "").strip() for column in POS_DECISION_FILE_COLUMNS} for row in reader]


def read_decision_rows(path):
    for line_number, row in enumerate(read_pos_file_rows(path), start=2):
        if not is_undecided(row):
            yield line_number, {column: row[column] for column in LEMMA_DECISION_COLUMNS}


def check_pos_names(where, row):
    if row["papygreek_pos"] not in PAPYGREEK_POS_NAMES:
        raise DecisionFileError(
            f"{where}: unknown papygreek_pos {row['papygreek_pos']!r}, use one of {sorted(PAPYGREEK_POS_NAMES)}"
        )
    if row["ligre_pos"] not in UNIVERSAL_TAGS:
        raise DecisionFileError(f"{where}: unknown ligre_pos {row['ligre_pos']!r}, use one of {sorted(UNIVERSAL_TAGS)}")


def unknown_ids(decision, lemma_bank):
    ids = (*decision.ligre_lemmas, decision.ligre_change.variant_of)
    return sorted(lemma_id for lemma_id in ids if lemma_id and lemma_bank.entry(lemma_id) is None)


def accepted_decisions(rows, lemma_bank):
    keys = set()
    for where, row in rows:
        try:
            key, decision = parse_decision_row(where, row)
            unknown = unknown_ids(decision, lemma_bank)
            if unknown:
                raise DecisionFileError(f"{where}: unknown LiGre lemma ids {', '.join(unknown)}")
            if key in keys:
                raise DecisionFileError(f"{where}: a decision for {key} is already given in an earlier row or file")
        except DecisionFileError as error:
            logger.warning("%s; the row is skipped until it is complete", error)
            continue
        keys.add(key)
        yield where, row, key, decision


def parse_lemma_decisions(rows, lemma_bank):
    return {key: decision for _, _, key, decision in accepted_decisions(rows, lemma_bank)}


def complete_decision_rows(rows, lemma_bank):
    return [(where, row) for where, row, _, _ in accepted_decisions(rows, lemma_bank)]


def parse_decision_row(where, row):
    decision_values = [decision.value for decision in LemmaDecision]
    check_pos_names(where, row)
    ligre_lemmas = tuple(row["ligre_lemma"].split())
    if row["decision"] == "reject":
        raise DecisionFileError(
            f"{where}: every decision links its tokens: give the LiGre lemma in ligre_lemma, or the lemma LiGre "
            f"will get (ligre_change add); tokens that are no word are left out by linking/not_a_word.py"
        )
    if not row["decision"] and not ligre_lemmas:
        raise DecisionFileError(f"{where}: give a decision, a ligre_lemma or both")
    if row["decision"] and row["decision"] not in decision_values:
        raise DecisionFileError(f"{where}: unknown decision {row['decision']!r}, use one of {decision_values}")
    kind = LemmaDecision(row["decision"]) if row["decision"] else None
    ligre_change = read_ligre_change(where, row)
    if ligre_change.kind is LigreChangeKind.ADD and ligre_lemmas:
        raise DecisionFileError(f"{where}: the tokens link to the lemma LiGre will add, so leave ligre_lemma empty")
    if ligre_change.kind is LigreChangeKind.ADD_WR and ligre_lemmas:
        raise DecisionFileError(f"{where}: the tokens link to ligre_id, the lemma that gets the spelling, so leave "
                                f"ligre_lemma empty")
    if kind is LemmaDecision.LIGRE_LEMMA_MISSING and ligre_change.kind is not LigreChangeKind.ADD:
        raise DecisionFileError(f"{where}: {kind.value} needs ligre_change add with the lemma LiGre will get")
    if (kind is LemmaDecision.LIGRE_SPELLING_MISSING) != (ligre_change.kind is LigreChangeKind.ADD_WR):
        raise DecisionFileError(f"{where}: ligre_change add-wr goes with the decision "
                                f"{LemmaDecision.LIGRE_SPELLING_MISSING.value}, and only with it")
    if kind is LemmaDecision.LIGRE_SPELLING_WRONG and not (ligre_change.kind is LigreChangeKind.CORRECT
                                                          and row["ligre_new_lemma"]):
        raise DecisionFileError(f"{where}: {kind.value} needs ligre_change correct with the right spelling in "
                                f"ligre_new_lemma")
    if (kind is LemmaDecision.CRASIS) != (len(ligre_lemmas) > 1):
        raise DecisionFileError(f"{where}: a crasis links to several LiGre lemmas (ids separated by a space), "
                                f"other decisions to one")
    key = (lemma_key(row["lemma"]), row["papygreek_pos"], row["ligre_pos"])
    return key, Decision(kind, ligre_lemmas, ligre_change)


def read_ligre_change(where, row):
    values = [change.value for change in LigreChangeKind]
    change = row["ligre_change"] or LigreChangeKind.NONE.value
    if change not in values:
        raise DecisionFileError(f"{where}: ligre_change is one of {values} (empty means none), not {change!r}")
    kind = LigreChangeKind(change)
    if kind is LigreChangeKind.NONE:
        if any(row[column] for column in LIGRE_CHANGE_COLUMNS[1:]):
            raise DecisionFileError(f"{where}: ligre_change is none, so leave {', '.join(LIGRE_CHANGE_COLUMNS[1:])} empty")
        return LigreChange(kind)
    if row["ligre_variant_of"] and kind is not LigreChangeKind.ADD:
        raise DecisionFileError(f"{where}: ligre_variant_of is only for a lemma to add (ligre_change add)")
    if kind is LigreChangeKind.CORRECT and not row["ligre_id"]:
        raise DecisionFileError(f"{where}: a correction needs the ligre_id of the LiGre lemma to correct")
    if kind is LigreChangeKind.ADD_WR:
        if not row["ligre_id"] or not row["ligre_new_lemma"]:
            raise DecisionFileError(f"{where}: add-wr needs the ligre_id of the LiGre lemma and the spelling it gets "
                                    f"in ligre_new_lemma")
        if row["ligre_new_pos"] or row["ligre_new_gender"]:
            raise DecisionFileError(f"{where}: add-wr keeps the part of speech and gender of the LiGre lemma, so "
                                    f"leave ligre_new_pos and ligre_new_gender empty")
        return LigreChange(kind, row["ligre_id"], lemma_key(row["ligre_new_lemma"]))
    if kind is LigreChangeKind.ADD:
        if row["ligre_id"]:
            raise DecisionFileError(f"{where}: a lemma to add has no ligre_id yet")
        if not row["ligre_new_lemma"]:
            raise DecisionFileError(f"{where}: a lemma to add needs ligre_new_lemma")
    if row["ligre_new_pos"] not in UNIVERSAL_TAGS:
        raise DecisionFileError(f"{where}: ligre_new_pos is one of {sorted(UNIVERSAL_TAGS)}, not {row['ligre_new_pos']!r}")
    if row["ligre_new_gender"] and row["ligre_new_gender"] not in LILA_GENDER_BY_AGDT_TAG:
        raise DecisionFileError(f"{where}: ligre_new_gender is one of {sorted(LILA_GENDER_BY_AGDT_TAG)} or empty")
    if (row["ligre_new_pos"] in GENDERED_TAGS) != bool(row["ligre_new_gender"]):
        raise DecisionFileError(f"{where}: NOUN and PROPN lemmas have a ligre_new_gender, other lemmas none")
    return LigreChange(kind, row["ligre_id"] or None, lemma_key(row["ligre_new_lemma"]) or None,
                       row["ligre_new_pos"], row["ligre_new_gender"] or None, row["ligre_variant_of"] or None)


def check_ligre_lemmas(decisions, lemma_bank):
    for (lemma, papygreek_pos, ligre_pos), decision in decisions.lemma_decisions.items():
        change = decision.ligre_change
        if change.kind is LigreChangeKind.ADD:
            present = [entry for entry in lemma_bank.candidates(change.lemma) if change.universal_tag in entry.universal_tags]
            if present:
                logger.warning("%s %s %s: the lemma to add, %s %s, is already in LiGre (%s): the tokens link to "
                               "it; set ligre_change to none",
                               lemma, papygreek_pos, ligre_pos, change.lemma, change.universal_tag,
                               ", ".join(entry.lemma_id for entry in present))
        if change.kind is LigreChangeKind.ADD_WR and lemma_bank.entry(change.ligre_id) in lemma_bank.candidates(change.lemma):
            logger.warning("%s %s %s: LiGre lemma %s already has the spelling %s; set ligre_change to none",
                           lemma, papygreek_pos, ligre_pos, change.ligre_id, change.lemma)


def decision_rows(decisions_directory, lemma_bank):
    pos_path = decisions_directory / settings.AMBIGUOUS_DECISIONS_FILENAME
    wr_lv_path = decisions_directory / settings.WR_LV_DECISIONS_FILENAME
    return [
        *((f"{pos_path}:{line}", row) for line, row in read_decision_rows(pos_path)),
        *lemma_decision_rows(wr_lv_path, read_wr_lv_rows(wr_lv_path), lemma_bank),
    ]


def load_pos_decisions(decisions_directory, lemma_bank):
    decisions = PosDecisions(parse_lemma_decisions(decision_rows(decisions_directory, lemma_bank), lemma_bank))
    logger.info("Loaded %d lemma decisions from %s", len(decisions.lemma_decisions), decisions_directory)
    return decisions
