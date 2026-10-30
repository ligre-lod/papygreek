from dataclasses import dataclass

from rdflib import Literal, URIRef
from rdflib.namespace import DC, DCTERMS, RDF, RDFS, XSD

from .. import settings
from .document_layout import build_document_layout
from .iris import iri_segment
from .namespaces import LILA, LILA_CORPUS, POWLA, create_graph

PUNCTUATION_TAG = "u"
TEXT_PART_TYPE = "Pars"
LINE_TYPE = "Linea"
SENTENCE_TYPE = "Sentence"


@dataclass(frozen=True)
class BuiltDocument:
    graph: object
    subjects: list


def add_sequence_links(graph, nodes):
    for previous_node, next_node in zip(nodes, nodes[1:]):
        graph.add((previous_node, POWLA.next, next_node))
        graph.add((next_node, POWLA.previous, previous_node))


def add_citation_unit(graph, unit, reference_type, reference_value, citation_level, members, member_predicate):
    graph.add((unit, RDF.type, LILA_CORPUS.citationUnit))
    graph.add((unit, RDFS.label, Literal(f"{reference_type} {reference_value}")))
    graph.add((unit, LILA_CORPUS.hasRefType, Literal(reference_type)))
    graph.add((unit, LILA_CORPUS.hasCitLevel, Literal(citation_level, datatype=XSD.int)))
    graph.add((unit, LILA_CORPUS.hasRefValue, Literal(f"{reference_type}_{reference_value}")))
    for member in members:
        graph.add((unit, member_predicate, member))
    graph.add((unit, LILA_CORPUS.first, members[0]))
    graph.add((unit, LILA_CORPUS.last, members[-1]))


def add_citation_structure(graph, structure, document, title, top_level_units):
    graph.add((structure, RDF.type, LILA_CORPUS.CitationStructure))
    graph.add((structure, DC.title, Literal(title)))
    graph.add((structure, DC.description, Literal(title)))
    graph.add((structure, POWLA.hasDocument, document))
    if top_level_units:
        graph.add((structure, LILA_CORPUS.first, top_level_units[0]))
    for unit in top_level_units:
        graph.add((structure, LILA_CORPUS.isLayer, unit))


def is_linkable(word):
    return (
        word.language == "grc"
        and any(character.isalpha() for character in word.lemma)
        and not word.lemma.startswith("punc")
        and not word.postag.startswith(PUNCTUATION_TAG)
    )


def build_corpus_graph(iris, lemma_namespace, document_ids):
    graph = create_graph(lemma_namespace)
    corpus = iris.corpus()
    graph.add((corpus, RDF.type, POWLA.Corpus))
    graph.add((corpus, DC.title, Literal(settings.CORPUS_TITLE)))
    graph.add((corpus, DCTERMS.license, URIRef(settings.PAPYGREEK_LICENSE_URL)))
    graph.add((corpus, DCTERMS.source, URIRef(settings.PAPYGREEK_REPOSITORY_URL)))
    graph.add((corpus, RDFS.seeAlso, URIRef(settings.PAPYGREEK_PORTAL_URL)))
    for document_id in document_ids:
        graph.add((corpus, POWLA.hasSubDocument, iris.document(document_id)))
    return graph


class DocumentGraphBuilder:
    def __init__(self, iris, lemma_namespace, lemma_linker, linking_review):
        self.iris = iris
        self.lemma_namespace = lemma_namespace
        self.lemma_linker = lemma_linker
        self.linking_review = linking_review

    def build(self, document):
        graph = create_graph(self.lemma_namespace)
        layout = build_document_layout(document)
        self.add_document_description(graph, document)
        self.add_citation_layer(graph, document.identifier, layout)
        self.add_sentence_layer(graph, document.identifier, layout)
        self.add_tokens(graph, document.identifier, layout)
        return BuiltDocument(graph, self.subjects_in_reading_order(document.identifier, layout))

    def subjects_in_reading_order(self, document_id, layout):
        subjects = [
            self.iris.document(document_id),
            self.iris.citation_structure(document_id),
        ]
        for part in layout.parts:
            subjects.append(self.iris.text_part(document_id, part.number))
            subjects.extend(self.iris.line(document_id, part.number, line) for line in part.tokens_by_line)
        subjects.append(self.iris.sentence_layer(document_id))
        subjects.extend(self.iris.sentence(document_id, sentence.sentence_id) for sentence in layout.sentences)
        subjects.extend(self.token_iris(document_id, layout.tokens))
        return subjects

    def token_iris(self, document_id, tokens):
        return [self.iris.token(document_id, token.index) for token in tokens]

    def add_document_description(self, graph, document):
        document_node = self.iris.document(document.identifier)
        graph.add((document_node, RDF.type, POWLA.Document))
        graph.add((document_node, DC.title, Literal(document.identifier)))
        for trismegistos_id in document.metadata.trismegistos_ids:
            graph.add((document_node, DCTERMS.identifier, Literal(f"TM {trismegistos_id}")))
            graph.add((document_node, RDFS.seeAlso, URIRef(settings.TRISMEGISTOS_TEXT_URL.format(iri_segment(trismegistos_id)))))
        for hgv_id in document.metadata.hgv_ids:
            graph.add((document_node, RDFS.seeAlso, URIRef(settings.PAPYRI_INFO_HGV_URL.format(iri_segment(hgv_id)))))
        graph.add((self.iris.corpus(), POWLA.hasSubDocument, document_node))

    def add_citation_layer(self, graph, document_id, layout):
        part_units = []
        for part in layout.parts:
            line_units = []
            for line, tokens in part.tokens_by_line.items():
                line_unit = self.iris.line(document_id, part.number, line)
                add_citation_unit(graph, line_unit, LINE_TYPE, line, 2, self.token_iris(document_id, tokens), POWLA.hasChild)
                line_units.append(line_unit)
            add_sequence_links(graph, line_units)

            part_unit = self.iris.text_part(document_id, part.number)
            add_citation_unit(graph, part_unit, TEXT_PART_TYPE, part.number, 1, line_units, LILA_CORPUS.hasCitSubUnit)
            part_units.append(part_unit)
        add_sequence_links(graph, part_units)

        add_citation_structure(
            graph,
            self.iris.citation_structure(document_id),
            self.iris.document(document_id),
            f"{document_id} Citation Layer",
            part_units,
        )

    def add_sentence_layer(self, graph, document_id, layout):
        sentence_units = []
        for sentence in layout.sentences:
            sentence_unit = self.iris.sentence(document_id, sentence.sentence_id)
            add_citation_unit(
                graph, sentence_unit, SENTENCE_TYPE, sentence.sentence_id, 1,
                self.token_iris(document_id, sentence.tokens), POWLA.hasChild,
            )
            sentence_units.append(sentence_unit)
        add_sequence_links(graph, sentence_units)

        add_citation_structure(
            graph,
            self.iris.sentence_layer(document_id),
            self.iris.document(document_id),
            f"{document_id} Sentence Layer",
            sentence_units,
        )

    def add_tokens(self, graph, document_id, layout):
        citation_structure = self.iris.citation_structure(document_id)
        sentence_layer = self.iris.sentence_layer(document_id)
        for token in layout.tokens:
            token_node = self.iris.token(document_id, token.index)
            word = token.word
            graph.add((token_node, RDF.type, POWLA.Terminal))
            graph.add((token_node, RDFS.label, Literal(word.form)))
            graph.add((token_node, POWLA.hasStringValue, Literal(word.form)))
            self.add_lemma_link(graph, token_node, token)
            if word.line:
                graph.add((token_node, LILA_CORPUS.hasCitStructure, citation_structure))
            graph.add((token_node, LILA_CORPUS.hasCitStructure, sentence_layer))
        for part in layout.parts:
            add_sequence_links(graph, self.token_iris(document_id, part.tokens))

    def add_lemma_link(self, graph, token_node, token):
        if not is_linkable(token.word):
            return
        result = self.lemma_linker.link(token.word)
        self.linking_review.record(token, result)
        if result.is_linked:
            graph.add((token_node, LILA.hasLemma, result.lemma))
