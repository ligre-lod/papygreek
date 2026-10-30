import argparse
import csv
import gzip
import sys
import urllib.request
from pathlib import Path

from pyoxigraph import QueryTriples, RdfFormat, Store, serialize

QUERIES_DIRECTORY = Path(__file__).resolve().parent
REPOSITORY_DIRECTORY = QUERIES_DIRECTORY.parent
DATA_DIRECTORY = REPOSITORY_DIRECTORY / "data" / "queries"
STORE_DIRECTORY = DATA_DIRECTORY / "store"
CLASSES_DIRECTORY = DATA_DIRECTORY / "classes"
CLASSES_URL = "https://raw.githubusercontent.com/CIRCSE/CLaSSES/main/ttl/{}.ttl"
CLASSES_PARTS = ["CEL", "BTT", "CIL", "GORDON", "ILLRP"]
PAPYGREEK_TURTLE = REPOSITORY_DIRECTORY / "ttl" / "complete_papygreek.ttl.gz"
DEFAULT_LIGRE_TURTLE = REPOSITORY_DIRECTORY.parent / "ligre-webinterface" / "ligre_lemmabank" / "ttl" / "ligreTTLRDF.ttl"
DEFAULT_IGVLL_TURTLE = REPOSITORY_DIRECTORY.parent.parent / "index-graecorum-vocabulorum" / "IGVLL.ttl"
TURTLE_PREFIXES = {
    "lemonEty": "http://lari-datasets.ilc.cnr.it/lemonEty#",
    "lila_corpus": "http://lila-erc.eu/ontologies/lila_corpora/",
    "lilaLemma": "http://lila-erc.eu/data/id/lemma/",
    "lilaOntology": "http://lila-erc.eu/ontologies/lila/",
    "ligreLemma": "https://w3id.org/ligre/data/id/lemma/",
    "ontolex": "http://www.w3.org/ns/lemon/ontolex#",
    "powla": "http://purl.org/powla/powla.owl#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
}


def read_settings_from_command_line():
    parser = argparse.ArgumentParser(description="Run a SPARQL query over PapyGreek, LiGre, IGVLL and CLaSSES.")
    parser.add_argument("query", type=Path, help="a .rq file, e.g. queries/shared_loanwords.rq")
    parser.add_argument("--ligre-turtle", type=Path, default=DEFAULT_LIGRE_TURTLE)
    parser.add_argument("--igvll-turtle", type=Path, default=DEFAULT_IGVLL_TURTLE)
    parser.add_argument("--output", type=Path, help="also write the results to this CSV file (Turtle for a CONSTRUCT query)")
    parser.add_argument("--data", type=Path, nargs="+", help="query only these Turtle files instead of the full store")
    parser.add_argument("--reload", action="store_true", help="build the store again from the Turtle files")
    return parser.parse_args()


def download_classes_if_missing():
    CLASSES_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for part in CLASSES_PARTS:
        path = CLASSES_DIRECTORY / f"{part}.ttl"
        if not path.exists():
            urllib.request.urlretrieve(CLASSES_URL.format(part), path)


def turtle_files(settings):
    return [settings.ligre_turtle, PAPYGREEK_TURTLE, settings.igvll_turtle] + [
        CLASSES_DIRECTORY / f"{part}.ttl" for part in CLASSES_PARTS
    ]


def open_turtle(path):
    return gzip.open(path, "rb") if path.suffix == ".gz" else open(path, "rb")


def build_store(settings):
    download_classes_if_missing()
    store = Store(str(STORE_DIRECTORY))
    store.clear()
    for path in turtle_files(settings):
        print(f"loading {path.name}", file=sys.stderr, flush=True)
        with open_turtle(path) as turtle:
            store.bulk_load(turtle, format=RdfFormat.TURTLE)
    store.optimize()
    return store


def load_into_memory(paths):
    store = Store()
    for path in paths:
        with open_turtle(path) as turtle:
            store.load(turtle, format=RdfFormat.TURTLE)
    return store


def open_store(settings):
    if settings.data:
        return load_into_memory(settings.data)
    if settings.reload or not STORE_DIRECTORY.exists():
        return build_store(settings)
    return Store(str(STORE_DIRECTORY))


def value_of(term):
    return "" if term is None else term.value


def write_triples(triples, output_path):
    triples = list(dict.fromkeys(triples))
    with open(output_path, "wb") as output_file:
        serialize(triples, output_file, format=RdfFormat.TURTLE, prefixes=TURTLE_PREFIXES)
    print(f"wrote {len(triples)} triples to {output_path}", file=sys.stderr)


def write_solutions(solutions, output_path):
    variables = [variable.value for variable in solutions.variables]
    rows = [[value_of(solution[variable]) for variable in variables] for solution in solutions]
    writer = csv.writer(sys.stdout, delimiter="\t")
    writer.writerow(variables)
    writer.writerows(rows)
    if output_path:
        with open(output_path, "w", newline="", encoding="utf-8") as output_file:
            csv.writer(output_file).writerows([variables] + rows)


def main():
    settings = read_settings_from_command_line()
    results = open_store(settings).query(settings.query.read_text(encoding="utf-8"))
    if isinstance(results, QueryTriples):
        if not settings.output:
            sys.exit("a CONSTRUCT query needs --output for its Turtle file")
        write_triples(results, settings.output)
    else:
        write_solutions(results, settings.output)


if __name__ == "__main__":
    main()
