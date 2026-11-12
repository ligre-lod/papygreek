import csv
import logging
from enum import Enum

from .lemma_bank import lemma_key, normalize_lemma
from .pos_tags import LILA_GENDER_BY_AGDT_TAG, UNIVERSAL_TAGS

DECISION_COLUMNS = ["lemma", "ligre_lemma", "decision", "new_pos", "new_gender", "note"]
INFORMATION_COLUMNS = ["papygreek_pos", "tokens", "rule", "candidates", "lsj_papygreek", "lsj_ligre"]
WR_LV_COLUMNS = [*DECISION_COLUMNS, *INFORMATION_COLUMNS]
KEPT_COLUMNS = ["ligre_lemma", "decision", "new_pos", "new_gender", "note"]
GENDERED_TAGS = {"NOUN", "PROPN"}
AGDT_GENDER_BY_LILA_GENDER = {gender: tag for tag, gender in LILA_GENDER_BY_AGDT_TAG.items()}

logger = logging.getLogger(__name__)


class WrLvDecision(Enum):
    LINK = "link"
    WR = "wr"
    LV = "lv"
    CORRECT_LIGRE = "correct-ligre"
    NEW = "new"


NEEDS_LIGRE_LEMMA = {WrLvDecision.LINK, WrLvDecision.WR, WrLvDecision.LV, WrLvDecision.CORRECT_LIGRE}


class WrLvDecisionError(ValueError):
    pass


def row_key(row):
    return lemma_key(row["lemma"]), row["papygreek_pos"]


def read_wr_lv_rows(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as decision_file:
        reader = csv.DictReader(decision_file, delimiter="\t")
        rows = [{column: (row.get(column) or "").strip() for column in WR_LV_COLUMNS} for row in reader]
        if (reader.fieldnames or [])[:len(DECISION_COLUMNS)] != DECISION_COLUMNS and rows:
            raise WrLvDecisionError(f"{path}: expected the columns {WR_LV_COLUMNS}, found {reader.fieldnames}")
    return rows


def ligre_analysis(lemma_bank, ligre_id):
    entry = lemma_bank.entry(ligre_id)
    tag = sorted(entry.universal_tags)[0]
    genders = sorted(AGDT_GENDER_BY_LILA_GENDER[gender] for gender in entry.genders if gender in AGDT_GENDER_BY_LILA_GENDER)
    return tag, genders[0] if tag in GENDERED_TAGS and genders else ""


def check_new_analysis(where, pos, gender):
    if pos not in UNIVERSAL_TAGS:
        raise WrLvDecisionError(f"{where}: new_pos is one of {sorted(UNIVERSAL_TAGS)}, not {pos!r}")
    if (pos in GENDERED_TAGS) != bool(gender) or (gender and gender not in LILA_GENDER_BY_AGDT_TAG):
        raise WrLvDecisionError(f"{where}: NOUN and PROPN need new_gender m, f or n; other parts of speech none")


def lemma_decision_row(where, row, lemma_bank):
    values = [decision.value for decision in WrLvDecision]
    if row["decision"] not in values:
        raise WrLvDecisionError(f"{where}: decision is one of {values} or empty, not {row['decision']!r}")
    decision = WrLvDecision(row["decision"])
    ligre_id = row["ligre_lemma"]
    if decision in NEEDS_LIGRE_LEMMA and (not ligre_id or lemma_bank.entry(ligre_id) is None):
        raise WrLvDecisionError(f"{where}: {decision.value} needs the id of a LiGre lemma in ligre_lemma")
    if decision is WrLvDecision.NEW and ligre_id:
        raise WrLvDecisionError(f"{where}: new adds a lemma that is not in LiGre, so leave ligre_lemma empty")
    spelling = normalize_lemma(row["lemma"])
    common = {"lemma": row["lemma"], "papygreek_pos": row["papygreek_pos"], "ligre_lemma": "", "ligre_id": "",
              "ligre_new_lemma": "", "ligre_new_pos": "", "ligre_new_gender": "", "ligre_variant_of": ""}
    if decision is WrLvDecision.NEW:
        check_new_analysis(where, row["new_pos"], row["new_gender"])
        return {**common, "ligre_pos": row["new_pos"], "decision": "ligre-lemma-missing", "ligre_change": "add",
                "ligre_new_lemma": spelling, "ligre_new_pos": row["new_pos"], "ligre_new_gender": row["new_gender"]}
    ligre_pos, ligre_gender = ligre_analysis(lemma_bank, ligre_id)
    common["ligre_pos"] = ligre_pos
    if decision is WrLvDecision.LINK:
        return {**common, "decision": "papygreek-lemma-wrong", "ligre_lemma": ligre_id, "ligre_change": "none"}
    if decision is WrLvDecision.WR:
        return {**common, "decision": "ligre-spelling-missing", "ligre_change": "add-wr", "ligre_id": ligre_id,
                "ligre_new_lemma": spelling}
    pos = row["new_pos"] or ligre_pos
    gender = row["new_gender"] if row["new_pos"] else ligre_gender
    check_new_analysis(where, pos, gender)
    if decision is WrLvDecision.LV:
        return {**common, "decision": "ligre-lemma-missing", "ligre_change": "add", "ligre_new_lemma": spelling,
                "ligre_new_pos": pos, "ligre_new_gender": gender, "ligre_variant_of": ligre_id}
    return {**common, "decision": "ligre-spelling-wrong", "ligre_change": "correct", "ligre_id": ligre_id,
            "ligre_new_lemma": spelling, "ligre_new_pos": pos, "ligre_new_gender": gender}


def lemma_decision_rows(path, rows, lemma_bank):
    decided = []
    for line, row in enumerate(rows, start=2):
        if not row["decision"]:
            continue
        where = f"{path}:{line}"
        try:
            decided.append((where, lemma_decision_row(where, row, lemma_bank)))
        except WrLvDecisionError as error:
            logger.warning("%s; the row is skipped until it is complete", error)
    return decided


def updated_rows(existing_rows, candidates, rule_order):
    existing = {row_key(row): row for row in existing_rows}
    candidate_keys = set()
    rows = []
    for candidate in candidates:
        key = row_key(candidate)
        candidate_keys.add(key)
        row = {**candidate}
        if key in existing:
            row.update({column: existing[key][column] for column in KEPT_COLUMNS})
        rows.append(row)
    rows += [row for key, row in existing.items() if key not in candidate_keys and row["decision"]]

    def order(row):
        decided = bool(row["decision"])
        return (decided, rule_order.get(row["rule"], len(rule_order)), -int(row["tokens"] or 0), row["lemma"])

    return sorted(rows, key=order)


def write_wr_lv_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as decision_file:
        writer = csv.DictWriter(decision_file, WR_LV_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
