import argparse
import csv
import sys
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, OWL, RDFS

REPOSITORY_DIRECTORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_DIRECTORY))

from papygreek_to_ligre import settings
from papygreek_to_ligre.linking.lemma_bank import LemmaBank, lemma_rows_from_graph
from papygreek_to_ligre.linking.pos_decisions import LigreChangeKind, complete_decision_rows, decision_rows
from papygreek_to_ligre.linking.pos_tags import LILA_GENDER_BY_AGDT_TAG, UNIVERSAL_TAG_BY_LILA_PART_OF_SPEECH
from papygreek_to_ligre.rdf.namespaces import LILA, ONTOLEX

COLUMNS = ["action", "ligre_id", "lemma", "pos", "gender", "new_lemma", "new_pos", "new_gender", "replaced_by",
           "reason", "evidence", "submitted_by"]
REVIEW_DIRECTORY = REPOSITORY_DIRECTORY / settings.DEFAULT_REVIEW_DIRECTORY
LEMMA_BANK = REPOSITORY_DIRECTORY / settings.DEFAULT_DATA_DIRECTORY / settings.LEMMA_BANK_FILENAME
OUTPUT = REPOSITORY_DIRECTORY / "ligre_corrections" / "papygreek-review.tsv"
LEMMA_IRI = "https://w3id.org/ligre/data/id/lemma/"
AGDT_TAG_BY_LILA_GENDER = {gender: tag for tag, gender in LILA_GENDER_BY_AGDT_TAG.items()}


def read_arguments():
    parser = argparse.ArgumentParser(description="Write the LiGre changes in the decision files in review/ as a LiGre "
                                                 "corrections file.")
    parser.add_argument("--review-dir", type=Path, default=REVIEW_DIRECTORY)
    parser.add_argument("--lemma-bank", type=Path, default=LEMMA_BANK, help="the LiGre dump the decisions refer to")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--submitted-by", default=settings.CORPUS_CREATORS[0]["iri"])
    return parser.parse_args()


class LigreState:
    def __init__(self, graph):
        self.graph = graph
        self.ids_by_written_form = {}
        for iri in graph.subjects(RDFS.label, None):
            lemma_id = self.id_of(iri)
            if lemma_id and self.analysis(lemma_id):
                for written_form in graph.objects(iri, ONTOLEX.writtenRep):
                    self.ids_by_written_form.setdefault(str(written_form), set()).add(lemma_id)

    @staticmethod
    def id_of(iri):
        return str(iri)[len(LEMMA_IRI):] if str(iri).startswith(LEMMA_IRI) else None

    @staticmethod
    def iri(lemma_id):
        return URIRef(LEMMA_IRI + lemma_id)

    def analysis(self, lemma_id):
        iri = self.iri(lemma_id)
        label = self.graph.value(iri, RDFS.label)
        if label is None or (iri, OWL.deprecated, Literal(True)) in self.graph:
            return None
        pos = [UNIVERSAL_TAG_BY_LILA_PART_OF_SPEECH.get(p) for p in self.graph.objects(iri, LILA.hasPOS)]
        genders = [AGDT_TAG_BY_LILA_GENDER.get(g) for g in self.graph.objects(iri, LILA.hasGender)]
        if len(pos) != 1 or len(genders) > 1:
            return None
        return str(label), pos[0], genders[0] if genders and pos[0] in ("NOUN", "PROPN") else ""

    def lemma_with(self, lemma, pos, gender):
        for lemma_id in sorted(self.ids_by_written_form.get(lemma, ()), key=int):
            analysis = self.analysis(lemma_id)
            if analysis and analysis[1:] == (pos, gender or ""):
                return lemma_id
        return None

    def is_replaced(self, lemma_id):
        return self.graph.value(self.iri(lemma_id), DCTERMS.isReplacedBy) is not None

    def has_written_form(self, lemma_id, written_form):
        return (self.iri(lemma_id), ONTOLEX.writtenRep, Literal(written_form, lang="grc")) in self.graph

    def are_variants(self, lemma_id, other_id):
        return (self.iri(lemma_id), LILA.lemmaVariant, self.iri(other_id)) in self.graph


def change_of(row):
    return (row["ligre_change"], row["ligre_id"], row["ligre_new_lemma"], row["ligre_new_pos"], row["ligre_new_gender"],
            row["ligre_variant_of"])


def key_of(row):
    if row["ligre_change"] == LigreChangeKind.ADD_WR.value:
        return ("add-wr", row["ligre_id"], row["ligre_new_lemma"])
    return row["ligre_id"] or (row["ligre_new_lemma"], row["ligre_new_pos"], row["ligre_new_gender"])


def group_changes(rows):
    groups, errors = {}, []
    for where, row in rows:
        if row["ligre_change"] in ("", LigreChangeKind.NONE.value):
            continue
        key = key_of(row)
        group = groups.setdefault(key, {"change": change_of(row), "rows": []})
        if group["change"] != change_of(row):
            errors.append(f"{where}: another row gives LiGre lemma {key} another change")
        group["rows"].append(row)
    if errors:
        raise SystemExit("\n".join(errors))
    return groups


def reason_of(current, new):
    if current is None:
        return "lemma missing from LiGre"
    names = ("spelling", "part of speech", "gender")
    wrong = [name for name, old, value in zip(names, current, new) if old != value]
    if "part of speech" in wrong and "gender" in wrong:
        wrong.remove("gender")
    return f"wrong {' and '.join(wrong)} in LiGre"


def evidence_of(rows):
    attested = "; ".join(sorted({f"{row['lemma']} as {row['papygreek_pos']}" for row in rows}))
    return f"PapyGreek Treebanks {settings.PAPYGREEK_VERSION} ({settings.PAPYGREEK_DOI}): {attested}"


def correction_rows(groups, state, submitted_by):
    corrects, merges, adds, written_forms, variants = [], [], [], [], []
    kept_by_target = {}
    after, skipped, problems = {}, [], []

    def current(ligre_id, rows):
        analysis = state.analysis(ligre_id)
        if analysis is None:
            problems.append(f"LiGre lemma {ligre_id} is deprecated or not in the pinned LiGre dump "
                            f"({', '.join(sorted({row['lemma'] for row in rows}))}); its change is left out")
        return analysis
    for key, group in sorted(groups.items(), key=lambda item: (isinstance(item[0], tuple), item[0] if isinstance(item[0], tuple) else int(item[0]))):
        kind, ligre_id, new_lemma, new_pos, new_gender, variant_of = group["change"]
        rows = group["rows"]
        common = {"evidence": evidence_of(rows), "submitted_by": submitted_by}
        if kind == LigreChangeKind.ADD.value:
            existing = state.lemma_with(new_lemma, new_pos, new_gender)
            if existing:
                skipped.append(f"add {new_lemma} {new_pos}")
            else:
                adds.append({"action": "add", "new_lemma": new_lemma, "new_pos": new_pos, "new_gender": new_gender,
                             "reason": reason_of(None, None), **common})
            if variant_of:
                if existing and state.are_variants(existing, variant_of):
                    skipped.append(f"add-variant {variant_of} {new_lemma}")
                else:
                    variants.append((variant_of, (new_lemma, new_pos, new_gender), common, rows))
            continue
        if kind == LigreChangeKind.ADD_WR.value:
            if state.has_written_form(ligre_id, new_lemma):
                skipped.append(f"add-wr {ligre_id} {new_lemma}")
                continue
            analysis = current(ligre_id, rows)
            if analysis is None:
                continue
            lemma, pos, gender = analysis
            written_forms.append({"action": "add-wr", "ligre_id": ligre_id, "lemma": lemma, "pos": pos,
                                  "gender": gender, "new_lemma": new_lemma, "reason": "spelling missing from LiGre",
                                  **common})
            continue
        if state.is_replaced(ligre_id):
            skipped.append(f"merge {ligre_id}")
            continue
        analysis = current(ligre_id, rows)
        if analysis is None:
            continue
        lemma, pos, gender = analysis
        target = (new_lemma or lemma, new_pos, new_gender)
        if analysis == target:
            skipped.append(f"correct {ligre_id} {lemma}")
            after[ligre_id] = target
            kept_by_target.setdefault(target, ligre_id)
            continue
        now = {"ligre_id": ligre_id, "lemma": lemma, "pos": pos, "gender": gender}
        if target in kept_by_target:
            merges.append({"action": "merge", **now, "replaced_by": kept_by_target[target],
                           "reason": f"the same lemma as {kept_by_target[target]} once both are corrected", **common})
            continue
        kept_by_target[target] = ligre_id
        after[ligre_id] = target
        corrects.append({"action": "correct", **now, "new_lemma": target[0], "new_pos": new_pos,
                         "new_gender": new_gender, "reason": reason_of((lemma, pos, gender), target), **common})
    variant_rows = []
    for variant_of, (new_lemma, new_pos, new_gender), common, rows in variants:
        analysis = after.get(variant_of) or current(variant_of, rows)
        if analysis is None:
            continue
        lemma, pos, gender = analysis
        variant_rows.append({"action": "add-variant", "ligre_id": variant_of, "lemma": lemma, "pos": pos,
                             "gender": gender, "new_lemma": new_lemma, "new_pos": new_pos, "new_gender": new_gender,
                             "reason": "another inflected form of the same word, used as lemma", **common})
    return corrects + merges + adds + written_forms + variant_rows, skipped, problems


def main():
    arguments = read_arguments()
    graph = Graph()
    graph.parse(arguments.lemma_bank, format="turtle")
    lemma_bank = LemmaBank.from_rows(lemma_rows_from_graph(graph))
    groups = group_changes(complete_decision_rows(decision_rows(arguments.review_dir, lemma_bank), lemma_bank))
    rows, skipped, problems = correction_rows(groups, LigreState(graph), arguments.submitted_by)
    for problem in problems:
        print(f"Warning: {problem}", file=sys.stderr)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, COLUMNS, delimiter="\t", lineterminator="\n", restval="")
        writer.writeheader()
        writer.writerows(rows)
    counts = {action: sum(row["action"] == action for row in rows)
              for action in ("correct", "merge", "add", "add-wr", "add-variant")}
    print(f"Wrote {len(rows)} LiGre corrections to {arguments.output}: "
          + ", ".join(f"{count} {action}" for action, count in counts.items())
          + f"; {len(skipped)} changes are already in the pinned LiGre release and left out")


if __name__ == "__main__":
    main()
