import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPOSITORY_DIRECTORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_DIRECTORY))

from papygreek_to_ligre import settings
from papygreek_to_ligre.linking.lemma_bank import LemmaBank, lemma_key
from papygreek_to_ligre.linking.linker import LemmaLinker, LinkStep
from papygreek_to_ligre.linking.not_a_word import NotAWord
from papygreek_to_ligre.linking.pos_decisions import load_pos_decisions
from papygreek_to_ligre.linking.review import LinkingReview
from papygreek_to_ligre.linking.variants import lsj_url
from papygreek_to_ligre.rdf.graph_builder import DocumentGraphBuilder
from papygreek_to_ligre.rdf.iris import CorpusIris
from papygreek_to_ligre.rdf.namespaces import ligre_lemma_namespace
from papygreek_to_ligre.sources.downloads import fetch_ligre_lemma_bank, fetch_papygreek_treebanks, find_treebank_files
from papygreek_to_ligre.sources.treebank_reader import read_treebank_document

COLUMNS = ["lemma", "papygreek_pos", "reason", "tokens", "documents", "forms", "examples", "lsj_papygreek"]
NOT_A_WORD = "not a word"
NOT_IN_LIGRE = "not in LiGre"
REASON_ORDER = {NOT_IN_LIGRE: 0, NOT_A_WORD: 1}
EXAMPLE_COUNT = 3
FORM_COUNT = 10


def read_arguments():
    parser = argparse.ArgumentParser(description="List the PapyGreek lemmas whose tokens are not linked to LiGre and "
                                                 "that are in neither decision file.")
    parser.add_argument("--data-dir", type=Path, default=REPOSITORY_DIRECTORY / settings.DEFAULT_DATA_DIRECTORY)
    parser.add_argument("--review-dir", type=Path, default=REPOSITORY_DIRECTORY / settings.DEFAULT_REVIEW_DIRECTORY)
    parser.add_argument("--output", type=Path,
                        default=REPOSITORY_DIRECTORY / settings.DEFAULT_REVIEW_DIRECTORY / settings.UNMATCHED_FILENAME)
    return parser.parse_args()


def decided_elsewhere(review_directory):
    keys = set()
    for filename in (settings.AMBIGUOUS_DECISIONS_FILENAME, settings.WR_LV_DECISIONS_FILENAME):
        path = review_directory / filename
        if path.exists():
            with path.open(encoding="utf-8") as source:
                keys.update((lemma_key(row["lemma"]), row["papygreek_pos"])
                            for row in csv.DictReader(source, delimiter="\t"))
    return keys


class UnmatchedTokens(LinkingReview):
    def __init__(self, listed_elsewhere):
        super().__init__()
        self.listed_elsewhere = listed_elsewhere
        self.tokens = Counter()
        self.documents = defaultdict(set)
        self.forms = defaultdict(Counter)
        self.examples = defaultdict(list)

    def record(self, token, result, document_id=""):
        super().record(token, result, document_id)
        if result.is_linked:
            return
        lemma = lemma_key(token.word.lemma)
        if result.step is LinkStep.NOT_A_WORD:
            reason = f"{NOT_A_WORD}: {result.not_a_word}"
        elif (lemma, result.papygreek_pos) in self.listed_elsewhere:
            return
        else:
            reason = NOT_IN_LIGRE
        key = (lemma, result.papygreek_pos, reason)
        self.tokens[key] += 1
        self.documents[key].add(document_id)
        self.forms[key][token.word.form] += 1
        if len(self.examples[key]) < EXAMPLE_COUNT:
            self.examples[key].append(f"{document_id} l. {token.word.line}".strip())

    def rows(self):
        rows = [{"lemma": lemma, "papygreek_pos": pos, "reason": reason, "tokens": count,
                 "documents": len(self.documents[key]),
                 "forms": " ".join(form for form, _ in self.forms[key].most_common(FORM_COUNT)),
                 "examples": "; ".join(self.examples[key]),
                 "lsj_papygreek": lsj_url(lemma) if reason == NOT_IN_LIGRE else ""}
                for key, count in self.tokens.items() for lemma, pos, reason in [key]]
        return sorted(rows, key=lambda row: (REASON_ORDER[row["reason"].split(":")[0]], -row["tokens"], row["lemma"]))


def main():
    arguments = read_arguments()
    treebank_directory = fetch_papygreek_treebanks(arguments.data_dir, False)
    lemma_bank = LemmaBank.from_turtle(fetch_ligre_lemma_bank(arguments.data_dir, False))
    linker = LemmaLinker(lemma_bank, load_pos_decisions(arguments.review_dir, lemma_bank), NotAWord())
    unmatched = UnmatchedTokens(decided_elsewhere(arguments.review_dir))
    builder = DocumentGraphBuilder(CorpusIris(settings.DEFAULT_BASE_IRI),
                                   ligre_lemma_namespace(settings.DEFAULT_BASE_IRI), linker, unmatched)
    for treebank_file in find_treebank_files(treebank_directory):
        builder.build(read_treebank_document(treebank_file))
    rows = unmatched.rows()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    reasons = Counter()
    for row in rows:
        reasons[row["reason"].split(":")[0]] += row["tokens"]
    print(f"{len(rows)} lemmas ({sum(reasons.values())} tokens) written to {arguments.output}: "
          + ", ".join(f"{count} tokens {reason}" for reason, count in sorted(reasons.items())), file=sys.stderr)
    print(unmatched.summary(), file=sys.stderr)


if __name__ == "__main__":
    main()
