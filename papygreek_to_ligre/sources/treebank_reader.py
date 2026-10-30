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
        form=(element.get("form_reg") or element.get("orig_form") or "").strip(),
        lemma=element.get("lemma_reg", "").strip(),
        postag=element.get("postag_reg", "").strip(),
        line=element.get("line_n", "").strip(),
        language=element.get("lang", "").strip(),
        artificial_type=element.get("artificial") or None,
    )


def split_identifiers(value):
    return list(dict.fromkeys(value.split()))
