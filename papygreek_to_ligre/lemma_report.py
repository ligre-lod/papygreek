import csv
from collections import Counter

from .lemma_bank import LinkStatus, normalize_lemma


class LemmaLinkingReport:
    def __init__(self):
        self.status_counts = Counter()
        self.unlinked_occurrences = Counter()

    def record(self, lemma, postag, match):
        self.status_counts[match.status] += 1
        if match.status is not LinkStatus.LINKED:
            key = (normalize_lemma(lemma), postag[:1], match.status.value, match.candidate_count)
            self.unlinked_occurrences[key] += 1

    def summary(self):
        total = sum(self.status_counts.values())
        linked = self.status_counts[LinkStatus.LINKED]
        linked_share = linked / total if total else 0
        return (
            f"Lemmas: {linked}/{total} tokens linked ({linked_share:.1%}), "
            f"{self.status_counts[LinkStatus.MISSING]} missing, "
            f"{self.status_counts[LinkStatus.AMBIGUOUS]} ambiguous"
        )

    def write_tsv(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as output_file:
            writer = csv.writer(output_file, delimiter="\t")
            writer.writerow(["lemma", "agdt_pos", "status", "candidates", "occurrences"])
            for key, occurrences in self.unlinked_occurrences.most_common():
                writer.writerow([*key, occurrences])
