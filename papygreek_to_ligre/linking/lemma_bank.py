import logging
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass

from rdflib import Graph
from rdflib.namespace import RDF

from ..rdf.namespaces import LILA, ONTOLEX
from .pos_tags import UNIVERSAL_TAG_BY_LILA_PART_OF_SPEECH

logger = logging.getLogger(__name__)

HOMOGRAPH_NUMBER = re.compile(r"(?<=\D)\d+$")


@dataclass(frozen=True)
class LemmaEntry:
    lemma: object
    universal_tags: frozenset

    @property
    def lemma_id(self):
        return str(self.lemma).rsplit("/", 1)[-1]

    def describe(self):
        return f"{'/'.join(sorted(self.universal_tags)) or '?'} {self.lemma_id}"


def normalize_lemma(lemma):
    return HOMOGRAPH_NUMBER.sub("", unicodedata.normalize("NFC", lemma.strip()))


class LemmaBank:
    def __init__(self, entries_by_written_representation):
        self.entries_by_written_representation = entries_by_written_representation

    @classmethod
    def from_rows(cls, rows):
        universal_tags_by_lemma = defaultdict(set)
        written_representations_by_lemma = defaultdict(set)
        for lemma, written_representation, universal_tag in rows:
            written_representations_by_lemma[lemma].add(normalize_lemma(written_representation))
            if universal_tag:
                universal_tags_by_lemma[lemma].add(universal_tag)

        entries_by_written_representation = defaultdict(list)
        for lemma, written_representations in written_representations_by_lemma.items():
            entry = LemmaEntry(lemma, frozenset(universal_tags_by_lemma[lemma]))
            for written_representation in written_representations:
                entries_by_written_representation[written_representation].append(entry)
        logger.info("Indexed %d written representations", len(entries_by_written_representation))
        return cls(dict(entries_by_written_representation))

    @classmethod
    def from_turtle(cls, path):
        logger.info("Loading LiGre lemma bank from %s", path)
        graph = Graph()
        graph.parse(path, format="turtle")
        return cls.from_rows(lemma_rows_from_graph(graph))

    def candidates(self, lemma):
        return self.entries_by_written_representation.get(normalize_lemma(lemma), [])


def lemma_rows_from_graph(graph):
    for lemma_iri in graph.subjects(RDF.type, LILA.Lemma):
        universal_tags = [
            UNIVERSAL_TAG_BY_LILA_PART_OF_SPEECH.get(part_of_speech)
            for part_of_speech in graph.objects(lemma_iri, LILA.hasPOS)
        ] or [None]
        for written_representation in graph.objects(lemma_iri, ONTOLEX.writtenRep):
            for universal_tag in universal_tags:
                yield lemma_iri, str(written_representation), universal_tag
