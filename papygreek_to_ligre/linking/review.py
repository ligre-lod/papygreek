import csv
from collections import Counter, defaultdict
from dataclasses import dataclass

from .. import settings
from .lemma_bank import lemma_key
from .linker import LINKING_STEPS, LinkStep
from .not_a_word import MARKER_DESCRIPTIONS

CHECK_HOMOGRAPH = "check homograph"
OPEN_STATUSES = {"undecided", "ambiguous", CHECK_HOMOGRAPH}

AUTOMATIC_LINKING = "1 automatic linking"
MANUAL_REVIEW = "2 manual review"
NO_LIGRE_LEMMA = "3 no LiGre lemma"
NOT_A_WORD = "0 not a word"

STATUS_BY_STEP = {
    LinkStep.UNDECIDED_POS_CLASH: "undecided",
    LinkStep.UNDECIDED_HOMOGRAPH: CHECK_HOMOGRAPH,
    LinkStep.REJECTED: "reject",
    LinkStep.AMBIGUOUS: "ambiguous",
}


@dataclass
class PosClash:
    status: str
    ligre_lemmas: str
    tokens: int = 0


def review_status(result):
    if result.homograph_check:
        return result.decision.value if result.decision else CHECK_HOMOGRAPH
    if result.step in (LinkStep.LEMMA_DECISION, LinkStep.REJECTED) and result.decision:
        return result.decision.value
    return STATUS_BY_STEP[result.step]


def workflow_step(result):
    if result.step is LinkStep.NOT_A_WORD:
        return NOT_A_WORD
    if result.step is LinkStep.MISSING:
        return NO_LIGRE_LEMMA
    return MANUAL_REVIEW if result.in_review else AUTOMATIC_LINKING


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
        self.outcome_counts = Counter()
        self.outcome_lemmas = defaultdict(set)
        self.linked_lemmas = defaultdict(set)
        self.pos_clashes = {}
        self.missing_lemmas = Counter()
        self.not_a_word_tokens = []

    def record(self, token, result, document_id=""):
        self.step_counts[result.step] += 1
        self.outcome_counts[(workflow_step(result), result.step)] += 1
        self.outcome_lemmas[(workflow_step(result), result.step)].add(lemma_key(token.word.lemma))
        if result.step in LINKING_STEPS:
            self.linked_lemmas[(workflow_step(result), result.step)].add(lemma_key(token.word.lemma))
        if result.in_review:
            self.record_pos_clash(lemma_key(token.word.lemma), result)
        elif result.step is LinkStep.MISSING:
            self.missing_lemmas[(lemma_key(token.word.lemma), result.papygreek_pos)] += 1
        elif result.step is LinkStep.NOT_A_WORD:
            word = token.word
            self.not_a_word_tokens.append(
                [result.not_a_word, document_id, token.sentence_id, word.id, word.form, word.lemma, word.postag])

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

    def write(self, review_directory):
        review_directory.mkdir(parents=True, exist_ok=True)
        self.write_linking_summary(review_directory / settings.LINKING_SUMMARY_FILENAME)
        self.write_pos_clash_lemmas(review_directory / settings.POS_CLASH_LEMMAS_FILENAME)
        self.write_missing_lemmas(review_directory / settings.NO_LIGRE_LEMMA_FILENAME)
        self.write_not_a_word(review_directory / settings.NOT_A_WORD_FILENAME)

    def write_linking_summary(self, path):
        total = sum(self.step_counts.values())

        def lemmas_of(keys, lemma_sets):
            return len(set().union(*(lemma_sets[key] for key in keys)))

        def row(step, outcome, counts, keys):
            tokens = sum(count for _, count in counts)
            linked = sum(count for link_step, count in counts if link_step in LINKING_STEPS)
            return [step, outcome, tokens, lemmas_of(keys, self.outcome_lemmas), linked,
                    lemmas_of(keys, self.linked_lemmas), f"{linked / total:.1%}" if total else ""]

        rows = self.not_a_word_summary_rows(total)
        for step in (AUTOMATIC_LINKING, MANUAL_REVIEW, NO_LIGRE_LEMMA):
            counts = [(link_step, self.outcome_counts[(step, link_step)]) for link_step in LinkStep
                      if self.outcome_counts[(step, link_step)]]
            rows += [row(step, link_step.value, [(link_step, count)], [(step, link_step)]) for link_step, count in counts]
            rows.append(row(step, "total", counts, [(step, link_step) for link_step, _ in counts]))
        rows.append(row("total", "", list(self.step_counts.items()), list(self.outcome_lemmas)))
        write_tsv(path, ["step", "outcome", "tokens", "lemmas", "linked", "linked_lemmas", "share_linked"], rows)

    def not_a_word_summary_rows(self, total):
        """One row per marker, so the excluded tokens can be traced to the rule that excluded them."""
        if not self.not_a_word_tokens:
            return []
        tokens_by_marker = Counter(row[0] for row in self.not_a_word_tokens)
        lemmas_by_marker = defaultdict(set)
        for row in self.not_a_word_tokens:
            lemmas_by_marker[row[0]].add(lemma_key(row[5]))
        rows = [[NOT_A_WORD, marker, count, len(lemmas_by_marker[marker]), 0, 0, f"{0:.1%}"]
                for marker, count in sorted(tokens_by_marker.items(), key=lambda item: (-item[1], item[0]))]
        rows.append([NOT_A_WORD, "total", len(self.not_a_word_tokens), len(set().union(*lemmas_by_marker.values())),
                     0, 0, f"{0:.1%}"])
        return rows

    def write_not_a_word(self, path):
        order = {marker: index for index, marker in enumerate(MARKER_DESCRIPTIONS)}
        rows = sorted(self.not_a_word_tokens, key=lambda row: (order.get(row[0], len(order)), row[1], row[2], row[3]))
        write_tsv(path, ["marker", "document", "sentence", "word", "form", "lemma", "postag", "marker_description"],
                  [row + [MARKER_DESCRIPTIONS.get(row[0], "")] for row in rows])

    def write_pos_clash_lemmas(self, path):
        def open_first_then_most_frequent(item):
            return (item[1].status not in OPEN_STATUSES, -item[1].tokens, item[0])

        rows = [
            [clash.status, lemma, papygreek_pos, clash_ligre_pos, clash.ligre_lemmas]
            for (lemma, papygreek_pos, clash_ligre_pos), clash
            in sorted(self.pos_clashes.items(), key=open_first_then_most_frequent)
        ]
        write_tsv(path, ["status", "lemma", "papygreek_pos", "ligre_pos", "ligre_lemmas"], rows)

    def write_missing_lemmas(self, path):
        rows = [[lemma, papygreek_pos] for (lemma, papygreek_pos), _ in self.missing_lemmas.most_common()]
        write_tsv(path, ["lemma", "papygreek_pos"], rows)
