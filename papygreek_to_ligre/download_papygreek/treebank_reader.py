import xml.etree.ElementTree as ElementTree
from pathlib import Path

from .treebank_model import DocumentMetadata, Sentence, TreebankDocument, Word


def read_treebank_document(path):
    root = ElementTree.parse(path).getroot()
    return TreebankDocument(
        identifier=Path(path).stem,
        metadata=read_document_metadata(root.find("document_meta")),
        sentences=[read_sentence(element) for element in root.iter("sentence")],
    )


def read_document_metadata(element):
    attributes = element.attrib if element is not None else {}
    return DocumentMetadata(
        trismegistos_ids=split_identifiers(attributes.get("tm_id", "")),
        hgv_ids=split_identifiers(attributes.get("hgv_id", "")),
    )


def read_sentence(element):
    return Sentence(
        id=int(element.get("id")),
        words=[read_word(word_element) for word_element in element.iter("word")],
    )


def read_word(element):
    return Word(
        id=int(element.get("id")),
        form=remove_expansion_wrappers(element.get("orig_form", "").strip()),
        lemma=element.get("lemma_reg", "").strip(),
        postag=element.get("postag_reg", "").strip(),
        line=element.get("line_n", "").strip(),
        language=element.get("lang", "").strip(),
        artificial_type=element.get("artificial") or None,
    )


def remove_expansion_wrappers(form):
    """Drop the extra parentheses PapyGreek puts around abbreviated words.

    PapyGreek writes both the abbreviated word and its expansion in
    parentheses, so "κώ(μης)" comes out as "(κώ(μης))" and the symbol
    expansion "(ἔτους)" as "((ἔτους))". In Leiden, parentheses only mark the
    expansion and never nest, so any pair that contains another pair is this
    wrapper and is removed. "(|...|)" groups are a different PapyGreek mark
    and are left alone.
    """
    stack, groups = [], []
    for position, character in enumerate(form):
        if character == "(":
            stack.append([position, False])
        elif character == ")" and stack:
            start, has_inner_group = stack.pop()
            if stack:
                stack[-1][1] = True
            if has_inner_group and not form.startswith("(|", start):
                groups.extend((start, position))
    if not groups:
        return form
    return "".join(character for position, character in enumerate(form) if position not in groups)


def split_identifiers(value):
    return list(dict.fromkeys(value.split()))
