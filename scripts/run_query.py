import argparse
import csv
import gzip
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

LILA_ENDPOINT = "https://lila-erc.eu/sparql/lila_knowledge_base/sparql"


def read_settings_from_command_line():
    parser = argparse.ArgumentParser(description="Run a SPARQL query on Turtle files or on a SPARQL endpoint.")
    parser.add_argument("query", type=Path, help="a .rq file, e.g. queries/examples/01_documents_and_coverage.rq")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--data", type=Path, nargs="+", help="query these Turtle files (needs pyoxigraph)")
    source.add_argument("--endpoint", nargs="?", const=LILA_ENDPOINT,
                        help=f"send the query to this SPARQL endpoint (default: {LILA_ENDPOINT})")
    parser.add_argument("--output", type=Path, help="also write the results to this CSV file")
    return parser.parse_args()


def open_turtle(path):
    return gzip.open(path, "rb") if path.suffix == ".gz" else open(path, "rb")


def query_turtle_files(paths, query):
    from pyoxigraph import RdfFormat, Store

    store = Store()
    for path in paths:
        with open_turtle(path) as turtle:
            store.load(turtle, format=RdfFormat.TURTLE)
    solutions = store.query(query)
    variables = [variable.value for variable in solutions.variables]
    rows = [["" if solution[variable] is None else solution[variable].value for variable in variables] for solution in solutions]
    return variables, rows


def query_endpoint(endpoint, query):
    body = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
    request = urllib.request.Request(endpoint, data=body, headers={"Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        results = json.load(response)
    variables = results["head"]["vars"]
    rows = [[binding.get(variable, {}).get("value", "") for variable in variables] for binding in results["results"]["bindings"]]
    return variables, rows


def write_solutions(variables, rows, output_path):
    writer = csv.writer(sys.stdout, delimiter="\t")
    writer.writerow(variables)
    writer.writerows(rows)
    if output_path:
        with open(output_path, "w", newline="", encoding="utf-8") as output_file:
            csv.writer(output_file).writerows([variables] + rows)


def main():
    settings = read_settings_from_command_line()
    query = settings.query.read_text(encoding="utf-8")
    if settings.endpoint:
        variables, rows = query_endpoint(settings.endpoint, query)
    else:
        variables, rows = query_turtle_files(settings.data, query)
    write_solutions(variables, rows, settings.output)


if __name__ == "__main__":
    main()
