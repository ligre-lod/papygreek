from pathlib import Path

PAPYGREEK_ARCHIVE_URL = "https://codeload.github.com/papygreek/papygreek-treebanks/zip/refs/heads/main"
PAPYGREEK_REPOSITORY_URL = "https://github.com/papygreek/papygreek-treebanks"
PAPYGREEK_PORTAL_URL = "https://papygreek.com/"
PAPYGREEK_LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"

LIGRE_LEMMA_BANK_URL = "https://raw.githubusercontent.com/ligre-lod/ligre_lemmabank/main/ttl/ligreTTLRDF.ttl"

TRISMEGISTOS_TEXT_URL = "https://www.trismegistos.org/text/{}"
PAPYRI_INFO_HGV_URL = "https://papyri.info/hgv/{}"

DEFAULT_BASE_IRI = "https://ligre.ugent.be"
CORPUS_NAME = "PapyGreek"
CORPUS_TITLE = "PapyGreek Treebanks"

DEFAULT_DATA_DIRECTORY = Path("data")
DEFAULT_OUTPUT_DIRECTORY = Path("ttl")

PAPYGREEK_ARCHIVE_FILENAME = "papygreek-treebanks.zip"
PAPYGREEK_EXTRACTION_DIRECTORY = "papygreek-treebanks"
LEMMA_BANK_FILENAME = "ligreTTLRDF.ttl"

TEXTS_OUTPUT_DIRECTORY = "texts"
CORPUS_OUTPUT_FILENAME = "PapyGreek_corpus.ttl"
COMPLETE_OUTPUT_FILENAME = "complete_papygreek.ttl.gz"
UNLINKED_LEMMAS_FILENAME = "unlinked_lemmas.tsv"
