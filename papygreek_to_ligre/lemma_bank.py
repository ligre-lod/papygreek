import logging
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from rdflib import Graph
from rdflib.namespace import RDF

from .namespaces import LILA, ONTOLEX

logger = logging.getLogger(__name__)

HOMOGRAPH_NUMBER = re.compile(r"(?<=\D)\d+$")

UNIVERSAL_TAGS_BY_AGDT_TAG = {
    "n": {"NOUN", "PROPN"},
    "v": {"VERB", "AUX"},
    "t": {"VERB"},
    "a": {"ADJ"},
    "d": {"ADV"},
    "l": {"DET"},
    "g": {"PART"},
    "c": {"CCONJ", "SCONJ"},
    "r": {"ADP"},
    "p": {"PRON", "DET"},
    "m": {"NUM", "ADJ"},
    "i": {"INTJ"},
    "e": {"INTJ"},
    "u": {"PUNCT"},
    "x": {"X"},
}

UNIVERSAL_TAG_BY_LILA_PART_OF_SPEECH = {
    LILA.adjective: "ADJ",
    LILA.adposition: "ADP",
    LILA.adverb: "ADV",
    LILA.auxiliary: "AUX",
    LILA.coordinating_conjunction: "CCONJ",
    LILA.determiner: "DET",
    LILA.interjection: "INTJ",
    LILA.noun: "NOUN",
    LILA.numeral: "NUM",
    LILA.particle: "PART",
    LILA.pronoun: "PRON",
    LILA.proper_noun: "PROPN",
    LILA.punctuation: "PUNCT",
    LILA.subordinating_conjunction: "SCONJ",
    LILA.symbol: "SYM",
    LILA.verb: "VERB",
    LILA.other: "X",
}


class LinkStatus(Enum):
    LINKED = "linked"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class LemmaMatch:
    status: LinkStatus
    lemma: Optional[object] = None
    candidate_count: int = 0


@dataclass(frozen=True)
class LemmaEntry:
    lemma: object
    universal_tags: frozenset


def normalize_lemma(lemma):
    return HOMOGRAPH_NUMBER.sub("", unicodedata.normalize("NFC", lemma.strip()))


def universal_tags_for(postag):
    return UNIVERSAL_TAGS_BY_AGDT_TAG.get(postag[:1], set())


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

    def link(self, lemma, postag):
        candidates = self.entries_by_written_representation.get(normalize_lemma(lemma), [])
        if not candidates:
            return LemmaMatch(LinkStatus.MISSING)
        if len(candidates) == 1:
            return LemmaMatch(LinkStatus.LINKED, candidates[0].lemma, 1)
        expected_tags = universal_tags_for(postag)
        matching_candidates = [candidate for candidate in candidates if candidate.universal_tags & expected_tags]
        if len(matching_candidates) == 1:
            return LemmaMatch(LinkStatus.LINKED, matching_candidates[0].lemma, len(candidates))
        return LemmaMatch(LinkStatus.AMBIGUOUS, candidate_count=len(candidates))


def lemma_rows_from_graph(graph):
    for lemma_iri in graph.subjects(RDF.type, LILA.Lemma):
        universal_tags = [
            UNIVERSAL_TAG_BY_LILA_PART_OF_SPEECH.get(part_of_speech)
            for part_of_speech in graph.objects(lemma_iri, LILA.hasPOS)
        ] or [None]
        for written_representation in graph.objects(lemma_iri, ONTOLEX.writtenRep):
            for universal_tag in universal_tags:
                yield lemma_iri, str(written_representation), universal_tag
