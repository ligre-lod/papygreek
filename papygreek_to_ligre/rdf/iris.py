from urllib.parse import quote

from rdflib import URIRef

from .. import settings

TOKEN_NUMBER_WIDTH = 7


def iri_segment(value):
    return quote(str(value).replace(" ", "_"), safe="._-~")


class CorpusIris:
    def __init__(self, base_iri, corpus_name=settings.CORPUS_NAME):
        self.corpus_root = f"{base_iri.rstrip('/')}/data/corpora/{iri_segment(corpus_name)}/id/corpus"

    def corpus(self):
        return URIRef(self.corpus_root)

    def document_path(self, document_id):
        return f"{self.corpus_root}/{iri_segment(document_id)}"

    def document(self, document_id):
        return URIRef(self.document_path(document_id))

    def citation_structure(self, document_id):
        return URIRef(f"{self.document_path(document_id)}/CiteStructure")

    def text_part(self, document_id, part_number):
        return URIRef(f"{self.citation_structure(document_id)}/Pars_{part_number}")

    def line(self, document_id, part_number, line):
        return URIRef(f"{self.text_part(document_id, part_number)}/Linea_{iri_segment(line)}")

    def sentence_layer(self, document_id):
        return URIRef(f"{self.document_path(document_id)}/SentenceLayer")

    def sentence(self, document_id, sentence_id):
        return URIRef(f"{self.sentence_layer(document_id)}/Sentence_{sentence_id}")

    def token(self, document_id, token_index):
        token_name = f"{document_id}_t_{token_index:0{TOKEN_NUMBER_WIDTH}d}"
        return URIRef(f"{self.document_path(document_id)}/{iri_segment(token_name)}")
