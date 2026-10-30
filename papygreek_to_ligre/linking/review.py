import csv
from collections import Counter
from dataclasses import dataclass

from .. import settings
from .lemma_bank import normalize_lemma
from .linker import LINKING_STEPS, LinkStep

STATUS_BY_STEP = {
    LinkStep.UNDECIDED_POS_CLASH: "undecided",
    LinkStep.REJECTED: "reject",
    LinkStep.AMBIGUOUS: "ambiguous",
}


@dataclass
class PosClash:
    status: str
    ligre_lemmas: str
    tokens: int = 0


def pos_clash_status(result):
    if result.step is LinkStep.LEMMA_DECISION:
        return result.decision.value
    return STATUS_BY_STEP[result.step]


def ligre_pos(candidates):
    return "/".join(sorted({tag for candidate in candidates for tag in candidate.universal_tags})) or "?"


def write_tsv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.writer(output_file, delimiter="\t")
        writer.writerow(header)
        writer.writerows(rows)


class LinkingReview:
    def __init__(self):
        self.step_counts = Counter()
        self.pos_clashes = {}

    def record(self, token, result):
        self.step_counts[result.step] += 1
        if result.pos_clash:
            self.record_pos_clash(normalize_lemma(token.word.lemma), result)

    def record_pos_clash(self, lemma, result):
        key = (lemma, result.papygreek_pos, ligre_pos(result.candidates))
        clash = self.pos_clashes.get(key)
        if clash is None:
            ligre_lemmas = " ".join(candidate.describe() for candidate in result.candidates)
            clash = self.pos_clashes[key] = PosClash(pos_clash_status(result), ligre_lemmas)
        clash.tokens += 1

    def summary(self):
        total = sum(self.step_counts.values())
        linked = sum(self.step_counts[step] for step in LINKING_STEPS)
        steps = ", ".join(f"{count} {step.value}" for step, count in self.step_counts.most_common())
        return f"Lemmas: {linked}/{total} tokens linked ({linked / total if total else 0:.1%}): {steps}"

    def write(self, review_directory):
        review_directory.mkdir(parents=True, exist_ok=True)
        self.write_linking_summary(review_directory / settings.LINKING_SUMMARY_FILENAME)
        self.write_pos_clash_lemmas(review_directory / settings.POS_CLASH_LEMMAS_FILENAME)

    def write_linking_summary(self, path):
        total = sum(self.step_counts.values())
        rows = [
            [step.value, "linked" if step in LINKING_STEPS else "unlinked", self.step_counts[step],
             f"{self.step_counts[step] / total:.1%}" if total else ""]
            for step in LinkStep
        ]
        write_tsv(path, ["step", "result", "tokens", "share"], rows + [["total", "", total, ""]])

    def write_pos_clash_lemmas(self, path):
        def undecided_first_then_most_frequent(item):
            return (item[1].status != "undecided", -item[1].tokens, item[0])

        rows = [
            [clash.status, lemma, papygreek_pos, clash_ligre_pos, clash.ligre_lemmas]
            for (lemma, papygreek_pos, clash_ligre_pos), clash
            in sorted(self.pos_clashes.items(), key=undecided_first_then_most_frequent)
        ]
        write_tsv(path, ["status", "lemma", "papygreek_pos", "ligre_pos", "ligre_lemmas"], rows)
