import csv
from collections import Counter
from dataclasses import dataclass

from .. import settings
from .lemma_bank import lemma_key
from .linker import LINKING_STEPS, LinkStep
from .pos_decisions import POS_DECISION_FILE_COLUMNS, is_undecided, read_pos_file_rows
from .variants import RULE_ORDER, variant_candidates
from .wr_lv_decisions import read_wr_lv_rows, updated_rows, write_wr_lv_rows

CHECK_HOMOGRAPH = "check homograph"
HOMOGRAPH = "homograph, linked to the only LiGre lemma"
OPEN_STATUSES = {"undecided", "ambiguous", CHECK_HOMOGRAPH}

STATUS_BY_STEP = {
    LinkStep.UNDECIDED_POS_CLASH: "undecided",
    LinkStep.UNDECIDED_HOMOGRAPH: CHECK_HOMOGRAPH,
    LinkStep.REJECTED: "reject",
    LinkStep.TO_ADD_TO_LIGRE: "waits for LiGre",
    LinkStep.AMBIGUOUS: "ambiguous",
}


@dataclass
class PosClash:
    status: str
    ligre_lemmas: str
    tokens: int = 0


def review_status(result):
    if result.decision is not None and result.decision.adds_to_ligre:
        return f"{result.decision.value} (in LiGre)" if result.is_linked else f"{result.decision.value} (waits for LiGre)"
    if result.homograph_check:
        if result.decision:
            return result.decision.value
        return HOMOGRAPH if result.step is LinkStep.HOMOGRAPH else CHECK_HOMOGRAPH
    if result.step in (LinkStep.LEMMA_DECISION, LinkStep.REJECTED, LinkStep.TO_ADD_TO_LIGRE) and result.decision:
        return result.decision.value
    return STATUS_BY_STEP[result.step]


def ligre_pos(candidates):
    return "/".join(sorted({tag for candidate in candidates for tag in candidate.universal_tags})) or "?"


def write_rows(path, columns, rows):
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


class LinkingReview:
    def __init__(self):
        self.step_counts = Counter()
        self.pos_clashes = {}
        self.missing_lemmas = Counter()

    def record(self, token, result, document_id=""):
        self.step_counts[result.step] += 1
        if result.in_review:
            self.record_pos_clash(lemma_key(token.word.lemma), result)
        elif result.step is LinkStep.MISSING:
            self.missing_lemmas[(lemma_key(token.word.lemma), result.papygreek_pos)] += 1

    def record_pos_clash(self, lemma, result):
        key = (lemma, result.papygreek_pos, ligre_pos(result.candidates))
        clash = self.pos_clashes.get(key)
        if clash is None:
            ligre_lemmas = " ".join(candidate.describe() for candidate in result.candidates)
            clash = self.pos_clashes[key] = PosClash(review_status(result), ligre_lemmas)
        clash.tokens += 1

    def summary(self):
        total = sum(self.step_counts.values())
        linked = sum(self.step_counts[step] for step in LINKING_STEPS)
        steps = ", ".join(f"{count} {step.value}" for step, count in self.step_counts.most_common())
        return f"Lemmas: {linked}/{total} tokens linked ({linked / total if total else 0:.1%}): {steps}"

    def write(self, review_directory, lemma_bank):
        review_directory.mkdir(parents=True, exist_ok=True)
        self.update_ambiguous_decisions(review_directory / settings.AMBIGUOUS_DECISIONS_FILENAME)
        self.update_wr_lv_decisions(review_directory / settings.WR_LV_DECISIONS_FILENAME, lemma_bank)

    def update_ambiguous_decisions(self, path):
        clashes = {key: clash for key, clash in self.pos_clashes.items()}
        kept, seen = [], set()
        for row in read_pos_file_rows(path):
            key = (lemma_key(row["lemma"]), row["papygreek_pos"], row["ligre_pos"])
            clash = clashes.get(key)
            if clash is not None:
                seen.add(key)
                row.update(status=clash.status, tokens=str(clash.tokens), candidates=clash.ligre_lemmas)
            if not is_undecided(row) or (clash is not None and clash.status in OPEN_STATUSES):
                kept.append(row)
        new_rows = [
            {**dict.fromkeys(POS_DECISION_FILE_COLUMNS, ""), "lemma": lemma, "papygreek_pos": papygreek_pos,
             "ligre_pos": clash_ligre_pos, "status": clash.status, "tokens": str(clash.tokens),
             "candidates": clash.ligre_lemmas}
            for (lemma, papygreek_pos, clash_ligre_pos), clash in clashes.items()
            if (lemma, papygreek_pos, clash_ligre_pos) not in seen and clash.status in OPEN_STATUSES
        ]
        undecided = sorted([row for row in kept if is_undecided(row)] + new_rows,
                           key=lambda row: (-int(row["tokens"] or 0), row["lemma"]))
        write_rows(path, POS_DECISION_FILE_COLUMNS, undecided + [row for row in kept if not is_undecided(row)])

    def update_wr_lv_decisions(self, path, lemma_bank):
        candidates = variant_candidates(self.missing_lemmas, lemma_bank)
        write_wr_lv_rows(path, updated_rows(read_wr_lv_rows(path), candidates, RULE_ORDER))
