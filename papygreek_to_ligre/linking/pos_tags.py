from ..rdf.namespaces import LILA

UNTAGGED = "untagged"

PAPYGREEK_POS_BY_AGDT_TAG = {
    "n": "noun",
    "v": "verb",
    "t": "participle",
    "a": "adjective",
    "d": "adverb",
    "l": "article",
    "g": "particle",
    "c": "conjunction",
    "r": "preposition",
    "p": "pronoun",
    "m": "numeral",
    "i": "interjection",
    "e": "exclamation",
    "u": "punctuation",
    "x": "other",
}
PAPYGREEK_POS_NAMES = frozenset(PAPYGREEK_POS_BY_AGDT_TAG.values()) | {UNTAGGED}

STRICT_UNIVERSAL_TAGS_BY_PAPYGREEK_POS = {
    "noun": {"NOUN", "PROPN"},
    "verb": {"VERB", "AUX"},
    "participle": {"VERB"},
    "adjective": {"ADJ"},
    "adverb": {"ADV"},
    "article": {"DET"},
    "particle": {"PART"},
    "conjunction": {"CCONJ", "SCONJ"},
    "preposition": {"ADP"},
    "pronoun": {"PRON", "DET"},
    "numeral": {"NUM"},
    "interjection": {"INTJ"},
    "exclamation": {"INTJ"},
    "punctuation": {"PUNCT"},
    "other": {"X"},
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
UNIVERSAL_TAGS = frozenset(UNIVERSAL_TAG_BY_LILA_PART_OF_SPEECH.values())


def papygreek_pos(postag):
    return PAPYGREEK_POS_BY_AGDT_TAG.get(postag[:1], UNTAGGED)


def strict_universal_tags(papygreek_pos_name):
    return STRICT_UNIVERSAL_TAGS_BY_PAPYGREEK_POS.get(papygreek_pos_name, set())
