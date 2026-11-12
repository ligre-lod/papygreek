import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass

from .lemma_bank import normalize_lemma
from .pos_tags import strict_universal_tags

IOTA_SUBSCRIPT = "ͅ"
SKIPPED_POS = {"numeral"}
LSJ_PAGE_URL = "https://lsj.gr/wiki/"

SPELLING_RULES = [
    (re.compile("ττ"), "σσ"),
    (re.compile("ρρ"), "ρσ"),
    (re.compile("γιγν"), "γιν"),
    (re.compile("μειγ"), "μιγ"),
    (re.compile("^ξυν"), "συν"),
]

VOICE_ENDINGS = [
    ("ομαι", "ω"),
    ("ουμαι", "εω"),
    ("ουμαι", "αω"),
    ("ουμαι", "οω"),
]


def strip_marks(text, keep=()):
    decomposed = unicodedata.normalize("NFD", text)
    kept = "".join(char for char in decomposed if not unicodedata.combining(char) or char in keep)
    return unicodedata.normalize("NFC", kept).replace("ς", "σ")


def without_accents(text):
    return strip_marks(text, keep=(IOTA_SUBSCRIPT,))


def without_marks(text):
    return strip_marks(text)


def lowercase(text):
    return without_marks(text).lower()


def spelling(text):
    normalized = lowercase(text)
    for pattern, replacement in SPELLING_RULES:
        normalized = pattern.sub(replacement, normalized)
    return normalized


@dataclass(frozen=True)
class Rule:
    name: str
    key: object


CAPITALISATION_RULE = Rule("capitalisation", lowercase)
RULES = [
    Rule("accents, breathings or editorial signs", without_accents),
    Rule("iota subscript", without_marks),
    CAPITALISATION_RULE,
    Rule("spelling (σσ/ττ, ρσ/ρρ, γιν/γιγν, μιγ/μειγ, συν/ξυν)", spelling),
]
VOICE_RULE = Rule("voice (-ομαι/-ω, -ουμαι/-εω, -αω, -οω)", lowercase)
RULE_ORDER = {rule.name: index for index, rule in enumerate([*RULES, VOICE_RULE])}


def voice_counterparts(normalized):
    for middle, active in VOICE_ENDINGS:
        if normalized.endswith(middle):
            yield normalized[: -len(middle)] + active
        if normalized.endswith(active):
            yield normalized[: -len(active)] + middle


class VariantFinder:
    def __init__(self, lemma_bank):
        self.indexes = {rule.name: defaultdict(list) for rule in RULES}
        for written_representation, entries in lemma_bank.entries_by_written_representation.items():
            for rule in RULES:
                for entry in entries:
                    self.indexes[rule.name][rule.key(written_representation)].append((written_representation, entry))

    def candidates(self, written_form, papygreek_pos):
        for rule in RULES:
            matches = self.indexes[rule.name].get(rule.key(written_form), [])
            if matches:
                return rule, matches
        if papygreek_pos == "verb":
            lowercase_index = self.indexes[CAPITALISATION_RULE.name]
            matches = [match for counterpart in voice_counterparts(lowercase(written_form))
                       for match in lowercase_index.get(counterpart, [])
                       if "VERB" in match[1].universal_tags]
            if matches:
                return VOICE_RULE, matches
        return None, []


def describe_matches(matches):
    return " ".join(f"{written_representation} {entry.describe()}" for written_representation, entry in matches)


def same_pos_matches(papygreek_pos, matches):
    expected = strict_universal_tags(papygreek_pos)
    return [match for match in matches if match[1].universal_tags & expected]


def lsj_url(form):
    return LSJ_PAGE_URL + form


def prefilled_ligre_lemma(preferred):
    ids = {entry.lemma_id for _, entry in preferred}
    return ids.pop() if len(ids) == 1 else ""


def variant_candidates(missing_lemmas, lemma_bank):
    finder = VariantFinder(lemma_bank)
    candidates = []
    for (lemma, papygreek_pos), tokens in missing_lemmas.items():
        if papygreek_pos in SKIPPED_POS:
            continue
        written_form = normalize_lemma(lemma)
        rule, matches = finder.candidates(written_form, papygreek_pos)
        if rule is None:
            continue
        preferred = same_pos_matches(papygreek_pos, matches) or matches
        ligre_forms = list(dict.fromkeys(form for form, _ in preferred))
        candidates.append({
            "lemma": lemma, "ligre_lemma": prefilled_ligre_lemma(preferred), "decision": "",
            "new_pos": "", "new_gender": "", "note": "", "papygreek_pos": papygreek_pos, "tokens": str(tokens),
            "rule": rule.name, "candidates": describe_matches(matches),
            "lsj_papygreek": lsj_url(written_form), "lsj_ligre": " ".join(lsj_url(form) for form in ligre_forms),
        })
    return candidates
