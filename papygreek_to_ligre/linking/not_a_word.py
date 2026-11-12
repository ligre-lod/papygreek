import re
from dataclasses import dataclass

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


class NotAWord:
    def marker(self, word):
        for marker in MARKERS:
            if marker.test(word):
                return marker.name
        return None
