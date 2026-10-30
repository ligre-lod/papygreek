import re

from rdflib import Literal, URIRef
from rdflib.namespace import DC, RDF, RDFS

from .namespaces import LILA, LILA_CORPUS, POWLA

NUMBER_CHUNKS = re.compile(r"(\d+)")
VALID_LOCAL_NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_-]*$")
OBJECT_INDENT = " " * 8
PREDICATE_INDENT = " " * 4

PREDICATE_ORDER = [
    RDF.type,
    DC.title,
    DC.description,
    RDFS.label,
    POWLA.hasStringValue,
    LILA.hasLemma,
    LILA_CORPUS.hasRefType,
    LILA_CORPUS.hasCitLevel,
    LILA_CORPUS.hasRefValue,
    POWLA.hasDocument,
    POWLA.hasSubDocument,
    LILA_CORPUS.hasCitSubUnit,
    POWLA.hasChild,
    LILA_CORPUS.first,
    LILA_CORPUS.isLayer,
    LILA_CORPUS.last,
    LILA_CORPUS.hasCitStructure,
    POWLA.next,
    POWLA.previous,
]
PREDICATE_RANK = {predicate: rank for rank, predicate in enumerate(PREDICATE_ORDER)}


def natural_sort_key(term):
    return [int(chunk) if chunk.isdigit() else chunk for chunk in NUMBER_CHUNKS.split(str(term))]


def predicate_sort_key(predicate):
    return (PREDICATE_RANK.get(predicate, len(PREDICATE_ORDER)), str(predicate))


class OrderedTurtleWriter:
    def __init__(self, output_file, namespace_manager):
        self.output_file = output_file
        self.prefixes = sorted(
            ((prefix, str(namespace)) for prefix, namespace in namespace_manager.namespaces()),
            key=lambda prefix_and_namespace: len(prefix_and_namespace[1]),
            reverse=True,
        )

    def write_prefixes(self):
        for prefix, namespace in sorted(self.prefixes):
            self.output_file.write(f"@prefix {prefix}: <{namespace}> .\n")
        self.output_file.write("\n")

    def write_subjects(self, graph, subjects):
        for subject in subjects:
            self.write_subject(graph, subject)

    def write_subject(self, graph, subject):
        predicates = sorted(set(graph.predicates(subject)), key=predicate_sort_key)
        if not predicates:
            return
        predicate_lines = [self.format_predicate_objects(graph, subject, predicate) for predicate in predicates]
        separator = f" ;\n{PREDICATE_INDENT}"
        self.output_file.write(f"{self.format_term(subject)} {separator.join(predicate_lines)} .\n\n")

    def format_predicate_objects(self, graph, subject, predicate):
        objects = sorted(graph.objects(subject, predicate), key=natural_sort_key)
        formatted_objects = f",\n{OBJECT_INDENT}".join(self.format_term(term) for term in objects)
        return f"{self.format_predicate(predicate)} {formatted_objects}"

    def format_predicate(self, predicate):
        return "a" if predicate == RDF.type else self.format_term(predicate)

    def format_term(self, term):
        if isinstance(term, Literal):
            return self.format_literal(term)
        return self.format_iri(term)

    def format_literal(self, literal):
        if literal.datatype is None:
            return literal.n3()
        return f"{Literal(str(literal)).n3()}^^{self.format_iri(literal.datatype)}"

    def format_iri(self, iri):
        iri_text = str(iri)
        for prefix, namespace in self.prefixes:
            local_name = iri_text[len(namespace):]
            if iri_text.startswith(namespace) and VALID_LOCAL_NAME.match(local_name):
                return f"{prefix}:{local_name}"
        return URIRef(iri_text).n3()
