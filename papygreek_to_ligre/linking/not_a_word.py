"""Tokens that are not a word to link: PapyGreek marks them in the lemma field.

Each token gets the name of the first marker that matches, so every not-a-word token is
counted once, under the marker that excluded it. Besides the automatic markers, a lemma can
be marked by hand as not a word in the annotation viewer (status `not-a-word` in
review/annotations_no_ligre_lemma.tsv); its tokens get the marker `manual`.
"""

import csv
import logging
import re
from dataclasses import dataclass

from .. import settings
from .lemma_bank import lemma_key
from .pos_tags import papygreek_pos

logger = logging.getLogger(__name__)

NOT_A_WORD_STATUS = "not-a-word"
MANUAL_MARKER = "manual"
POSTAG_AS_LEMMA = re.compile(r"[a-z][-_a-z0-9]{8}")


@dataclass(frozen=True)
class Marker:
    name: str
    description: str
    test: object


MARKERS = (
    Marker("vacat", "lemma |vac:…|: blank space on the papyrus",
           lambda word: "|vac:" in word.lemma),
    Marker("lemma gap", "lemma contains |gap:…|: the word is partly lost and its lemma unknown",
           lambda word: "|gap:" in word.lemma),
    Marker("lemma gap G", "lemma contains the Latin letter G for lost letters (Gη, προGG)",
           lambda word: "G" in word.lemma),
    Marker("placeholder γ", "untagged token with the placeholder lemma γ: an illegible word",
           lambda word: word.lemma == "γ" and not word.postag.strip("-_")),
    Marker("unresolved abbreviation", "lemma ends in …: an abbreviation PapyGreek did not resolve",
           lambda word: word.lemma.endswith("…")),
    Marker("placeholder TO_ADD", "lemma TO_ADD: a placeholder left in the annotation",
           lambda word: word.lemma == "TO_ADD"),
    Marker("postag as lemma", "the lemma field holds a part-of-speech tag (u--------)",
           lambda word: "-" in word.lemma and POSTAG_AS_LEMMA.fullmatch(word.lemma) is not None),
)
MARKER_DESCRIPTIONS = {marker.name: marker.description for marker in MARKERS}
MARKER_DESCRIPTIONS[MANUAL_MARKER] = f"marked by hand in {settings.NO_LIGRE_LEMMA_ANNOTATIONS_FILENAME}"


def annotation_key(lemma, pos):
    return f"{lemma_key(lemma)}|{pos}"


class NotAWord:
    def __init__(self, manual_keys=frozenset()):
        self.manual_keys = frozenset(manual_keys)

    @classmethod
    def load(cls, review_directory):
        """The automatic markers plus the lemmas marked by hand in the annotation viewer."""
        path = review_directory / settings.NO_LIGRE_LEMMA_ANNOTATIONS_FILENAME
        keys = set()
        if path.exists():
            with path.open(newline="", encoding="utf-8") as annotations_file:
                for row in csv.DictReader(annotations_file, delimiter="\t"):
                    if row.get("status") == NOT_A_WORD_STATUS and row.get("papygreek_pos"):
                        keys.add(annotation_key(row["papygreek_lemma"], row["papygreek_pos"]))
        logger.info("Loaded %d lemmas marked by hand as not a word from %s", len(keys), path)
        return cls(keys)

    def marker(self, word):
        for marker in MARKERS:
            if marker.test(word):
                return marker.name
        if annotation_key(word.lemma, papygreek_pos(word.postag)) in self.manual_keys:
            return MANUAL_MARKER
        return None
