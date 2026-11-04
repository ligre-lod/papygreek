"""Loads the treebanks and groups the tokens whose lemma is missing from LiGre by lemma.

The tokens are selected exactly as the pipeline selects them: the same reader, the same
document layout (parts and lines), the same linkability test and the same linker with the
hand-made decisions in review/. A lemma is a PapyGreek lemma with its PapyGreek part of
speech, as in review/review_no_ligre_lemma.tsv.
"""

import bisect
import logging
import pickle
import re
import unicodedata
import xml.etree.ElementTree as ElementTree
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from papygreek_to_ligre import settings
from papygreek_to_ligre.download_papygreek.downloads import find_treebank_files
from papygreek_to_ligre.download_papygreek.treebank_model import TreebankDocument
from papygreek_to_ligre.download_papygreek.treebank_reader import read_document_metadata, read_sentence
from papygreek_to_ligre.linking.lemma_bank import LemmaBank, lemma_key, normalize_lemma
from papygreek_to_ligre.linking.linker import LemmaLinker, LinkStep
from papygreek_to_ligre.linking.not_a_word import NotAWord
from papygreek_to_ligre.linking.pos_decisions import load_pos_decisions
from papygreek_to_ligre.linking.pos_tags import papygreek_pos, strict_universal_tags
from papygreek_to_ligre.rdf.document_layout import build_document_layout
from papygreek_to_ligre.rdf.graph_builder import is_linkable

from .morphology import describe_postag, describe_relation

logger = logging.getLogger(__name__)

LEMMA_BANK_CACHE_FILENAME = "viewer_lemma_bank.pickle"
NATURAL_SORT_PART = re.compile(r"(\d+)")
GENDERS = {"m": "masculine", "f": "feminine", "n": "neuter", "c": "common"}


@dataclass(frozen=True)
class Target:
    key: str
    document: str
    sentence: int
    word: int
    form: str
    lemma: str
    postag: str
    line: str
    snippet: tuple  # (forms before, form, forms after) on the same line


@dataclass
class LemmaGroup:
    key: str
    lemma: str
    pos: str
    targets: list = field(default_factory=list)
    variants: list = field(default_factory=list)      # keys of other missing lemmas spelled alike
    near_ligre: list = field(default_factory=list)    # LiGre lemmas spelled alike

    @property
    def genders(self):
        if self.pos != "noun":
            return {}
        counts = Counter(target.postag[6:7] for target in self.targets)
        return {GENDERS[code]: count for code, count in counts.most_common() if code in GENDERS}

    @property
    def flags(self):
        flags = []
        if len(self.genders) > 1:
            flags.append("mixed gender")
        if self.variants:
            flags.append("PapyGreek variants")
        if self.near_ligre:
            flags.append("near LiGre match")
        return flags


@dataclass
class LoadedDocument:
    identifier: str
    path: Path
    hgv_ids: list


def target_key(document_id, sentence_id, word_id):
    return f"{document_id}#{sentence_id}.{word_id}"


def group_key(lemma, pos):
    return f"{lemma_key(lemma)}|{pos}"


def natural_key(text):
    return [int(part) if part.isdigit() else part for part in NATURAL_SORT_PART.split(text)]


def fold(text):
    """Accent-, breathing- and case-insensitive form."""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(character for character in decomposed if not unicodedata.combining(character))
    return unicodedata.normalize("NFC", stripped).lower().replace("ς", "σ")


def load_lemma_bank(data_directory):
    turtle_path = data_directory / settings.LEMMA_BANK_FILENAME
    cache_path = data_directory / LEMMA_BANK_CACHE_FILENAME
    stamp = (turtle_path.stat().st_size, turtle_path.stat().st_mtime_ns)
    if cache_path.exists():
        with cache_path.open("rb") as cache_file:
            cached_stamp, lemma_bank = pickle.load(cache_file)
        if cached_stamp == stamp:
            logger.info("Using cached LiGre lemma bank %s", cache_path)
            return lemma_bank
    lemma_bank = LemmaBank.from_turtle(turtle_path)
    with cache_path.open("wb") as cache_file:
        pickle.dump((stamp, lemma_bank), cache_file)
    return lemma_bank


def read_document(path):
    root = ElementTree.parse(path).getroot()
    document = TreebankDocument(
        identifier=path.stem,
        metadata=read_document_metadata(root.find("document_meta")),
        sentences=[read_sentence(element) for element in root.iter("sentence")],
    )
    return root, document


def word_details(root):
    """Attributes the pipeline does not read, per (sentence id, word id)."""
    details = {}
    for sentence in root.iter("sentence"):
        sentence_id = int(sentence.get("id"))
        for word in sentence.iter("word"):
            details[(sentence_id, int(word.get("id")))] = word.attrib
    return details


def document_metadata(root):
    meta = root.find("document_meta")
    attributes = meta.attrib if meta is not None else {}
    text_types, people, seen_people = [], [], set()
    for hand in root.iter("hand_meta"):
        for text_type in hand.iter("text_type"):
            label = " / ".join(filter(None, (text_type.get("category"), text_type.get("subcategory"))))
            if label and label not in text_types:
                text_types.append(label)
        for person in hand.iter("person"):
            entry = (person.get("name", ""), person.get("role", ""), person.get("tm_id", ""))
            if entry[0] and entry not in seen_people:
                seen_people.add(entry)
                people.append({"name": entry[0], "role": entry[1], "tm_id": entry[2]})
    return {
        "date_not_before": attributes.get("date_not_before", ""),
        "date_not_after": attributes.get("date_not_after", ""),
        "place": attributes.get("place_name", ""),
        "text_types": text_types,
        "people": people,
    }


def placed_lines(layout):
    """[(part number, line, [tokens])] in reading order, plus the tokens without a line."""
    lines = [(part.number, line, tokens) for part in layout.parts for line, tokens in part.tokens_by_line.items()]
    unplaced = [token for token in layout.tokens if not token.word.line]
    return lines, unplaced


class Corpus:
    def __init__(self, data_directory, review_directory):
        treebank_directory = data_directory / settings.PAPYGREEK_EXTRACTION_DIRECTORY
        if not treebank_directory.exists():
            raise SystemExit(f"{treebank_directory} not found: run `python -m papygreek_to_ligre` first")
        self.lemma_bank = load_lemma_bank(data_directory)
        # Only the automatic not-a-word markers: lemmas marked by hand stay here, so they can be undone.
        self.linker = LemmaLinker(self.lemma_bank, load_pos_decisions(review_directory), NotAWord())
        self.automatic_not_a_word = Counter()
        self.documents = {}
        self.targets = {}
        self.groups = {}
        self.group_of_target = {}
        for path in sorted(find_treebank_files(treebank_directory), key=lambda path: natural_key(path.stem)):
            self.load(path)
        self.search_index = sorted(
            (fold(written), written, entries)
            for written, entries in self.lemma_bank.entries_by_written_representation.items()
        )
        self.find_look_alikes()
        logger.info("%d lemmas to annotate (%d tokens in %d documents)",
                    len(self.groups), len(self.targets), len(self.documents))

    def load(self, path):
        _, document = read_document(path)
        layout = build_document_layout(document)
        lines, _ = placed_lines(layout)
        line_of_token = {token.index: tokens for _, _, tokens in lines for token in tokens}
        found = False
        for token in layout.tokens:
            word = token.word
            if not is_linkable(word):
                continue
            result = self.linker.link(word)
            if result.step is LinkStep.NOT_A_WORD:
                self.automatic_not_a_word[result.not_a_word] += 1
            if result.step is not LinkStep.MISSING:
                continue
            line_tokens = line_of_token.get(token.index, [token])
            position = next(i for i, other in enumerate(line_tokens) if other.index == token.index)
            target = Target(
                key=target_key(document.identifier, token.sentence_id, word.id),
                document=document.identifier,
                sentence=token.sentence_id,
                word=word.id,
                form=word.form,
                lemma=word.lemma,
                postag=word.postag,
                line=word.line,
                snippet=(
                    " ".join(other.word.form for other in line_tokens[:position]),
                    word.form,
                    " ".join(other.word.form for other in line_tokens[position + 1:]),
                ),
            )
            pos = papygreek_pos(word.postag)
            key = group_key(word.lemma, pos)
            group = self.groups.setdefault(key, LemmaGroup(key, lemma_key(word.lemma), pos))
            group.targets.append(target)
            self.targets[target.key] = target
            self.group_of_target[target.key] = key
            found = True
        if found:
            self.documents[document.identifier] = LoadedDocument(document.identifier, path, document.metadata.hgv_ids)

    def find_look_alikes(self):
        """Spellings that differ only in accents, breathings or capitals."""
        groups_by_fold = defaultdict(list)
        for group in self.groups.values():
            groups_by_fold[fold(normalize_lemma(group.lemma))].append(group.key)
        ligre_by_fold = defaultdict(list)
        for folded, written, entries in self.search_index:
            ligre_by_fold[folded].extend(
                {"written": written, "id": entry.lemma_id, "tags": sorted(entry.universal_tags)} for entry in entries)
        for group in self.groups.values():
            folded = fold(normalize_lemma(group.lemma))
            group.variants = [key for key in groups_by_fold[folded] if key != group.key]
            group.near_ligre = ligre_by_fold.get(folded, [])

    def summary(self, group):
        return {"key": group.key, "lemma": group.lemma, "pos": group.pos,
                "tokens": len(group.targets), "flags": group.flags}

    def lemma_payload(self, key):
        group = self.groups[key]
        return {
            **self.summary(group),
            "genders": group.genders,
            "suggested_tags": sorted(strict_universal_tags(group.pos)),
            "variants": [self.summary(self.groups[variant]) for variant in group.variants],
            "near_ligre": group.near_ligre,
            "occurrences": [
                {"key": target.key, "document": target.document, "line": target.line,
                 "before": target.snippet[0], "form": target.snippet[1], "after": target.snippet[2],
                 "info": describe_postag(target.postag)}
                for target in group.targets
            ],
        }

    def document_payload(self, document_id, lemma_group_key):
        loaded = self.documents[document_id]
        root, document = read_document(loaded.path)
        layout = build_document_layout(document)
        details = word_details(root)
        lines, unplaced = placed_lines(layout)

        def token_payload(token):
            word = token.word
            key = target_key(document_id, token.sentence_id, word.id)
            payload = {"form": word.form, "lemma": word.lemma, "info": describe_postag(word.postag),
                       "sentence": token.sentence_id, "word": word.id}
            if self.group_of_target.get(key) == lemma_group_key:
                payload["key"] = key
                payload["details"] = self.token_details(self.targets[key], details)
            return payload

        return {
            "id": document_id,
            "hgv_ids": document.metadata.hgv_ids,
            "tm_ids": document.metadata.trismegistos_ids,
            "meta": document_metadata(root),
            "lines": [
                {"part": part, "line": line, "tokens": [token_payload(token) for token in tokens]}
                for part, line, tokens in lines
            ],
            "unplaced": [token_payload(token) for token in unplaced],
        }

    def token_details(self, target, details):
        attributes = details.get((target.sentence, target.word), {})
        head_id = attributes.get("head_reg", "")
        head = details.get((target.sentence, int(head_id)), {}) if head_id.isdigit() else {}
        return {
            "form": target.form,
            "line": target.line,
            "regularized_form": attributes.get("form_reg", ""),
            "original_lemma": attributes.get("lemma_orig", ""),
            "postag": target.postag,
            "info": describe_postag(target.postag),
            "relation": attributes.get("relation_reg", ""),
            "relation_info": describe_relation(attributes.get("relation_reg", "")),
            "head": {"form": head.get("orig_form", ""), "lemma": head.get("lemma_reg", ""),
                     "sentence": target.sentence, "word": int(head_id)} if head else None,
        }

    def search_ligre(self, query, limit=30):
        folded = fold(query.strip())
        if not folded:
            return []
        results = []
        start = bisect.bisect_left(self.search_index, (folded,))
        for folded_written, written, entries in self.search_index[start:start + limit]:
            if not folded_written.startswith(folded):
                break
            for entry in entries:
                results.append({"written": written, "id": entry.lemma_id, "tags": sorted(entry.universal_tags)})
        return results[:limit]
