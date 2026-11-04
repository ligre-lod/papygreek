"""Plain-language descriptions of AGDT morphological tags and syntactic relations."""

from papygreek_to_ligre.linking.pos_tags import PAPYGREEK_POS_BY_AGDT_TAG

FEATURES = (
    (1, "person", {"1": "1st person", "2": "2nd person", "3": "3rd person"}),
    (2, "number", {"s": "singular", "p": "plural", "d": "dual"}),
    (3, "tense", {"p": "present", "i": "imperfect", "r": "perfect", "l": "pluperfect",
                  "t": "future perfect", "f": "future", "a": "aorist"}),
    (4, "mood", {"i": "indicative", "s": "subjunctive", "o": "optative", "n": "infinitive",
                 "m": "imperative", "p": "participle"}),
    (5, "voice", {"a": "active", "p": "passive", "m": "middle", "e": "middle/passive"}),
    (6, "gender", {"m": "masculine", "f": "feminine", "n": "neuter", "c": "common"}),
    (7, "case", {"n": "nominative", "g": "genitive", "d": "dative", "a": "accusative",
                 "v": "vocative", "l": "locative"}),
    (8, "degree", {"p": "positive", "c": "comparative", "s": "superlative"}),
)

RELATIONS = {
    "PRED": "predicate (main verb)",
    "SBJ": "subject",
    "OBJ": "object",
    "ATR": "attribute (modifies a noun)",
    "ADV": "adverbial",
    "ATV": "complement of subject/object",
    "AtvV": "complement of verb",
    "PNOM": "predicate nominal",
    "OCOMP": "object complement",
    "COORD": "coordinator",
    "APOS": "apposition head",
    "AuxP": "preposition",
    "AuxC": "subordinating conjunction",
    "AuxY": "sentence adverb/particle",
    "AuxZ": "emphasizing particle",
    "AuxX": "comma",
    "AuxG": "bracket/quote",
    "AuxK": "final punctuation",
    "AuxV": "auxiliary verb",
    "ExD": "elliptical dependent",
}
RELATION_SUFFIXES = {"_CO": "coordinated", "_AP": "in apposition"}


def describe_postag(postag):
    """'n-s---fn-' -> 'noun, singular, feminine, nominative'."""
    if not postag:
        return "untagged"
    parts = [PAPYGREEK_POS_BY_AGDT_TAG.get(postag[0], f"unknown ({postag[0]})")]
    for position, _, values in FEATURES:
        value = postag[position:position + 1]
        if value and value not in "-":
            parts.append(values.get(value, f"? ({value})"))
    return ", ".join(parts)


def describe_relation(relation):
    if not relation:
        return ""
    base, suffix = relation, ""
    for code, label in RELATION_SUFFIXES.items():
        if relation.endswith(code):
            base, suffix = relation[: -len(code)], label
    label = RELATIONS.get(base, base)
    return f"{label}, {suffix}" if suffix else label
