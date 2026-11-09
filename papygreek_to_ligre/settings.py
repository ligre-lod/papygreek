import re
from pathlib import Path

CITATION_PATH = Path(__file__).resolve().parent.parent / "CITATION.cff"


def citation_field(name):
    """The release metadata is set in CITATION.cff only (see RELEASING.md)."""
    match = re.search(rf"^{name}:\s*\"?([^\s\"]+)\"?\s*$", CITATION_PATH.read_text(encoding="utf-8"), re.M)
    return match.group(1) if match else ""


PAPYGREEK_VERSION = "v3.0"
PAPYGREEK_DOI = "https://doi.org/10.5281/zenodo.8428823"
PAPYGREEK_ARCHIVE_URL = f"https://codeload.github.com/papygreek/papygreek-treebanks/zip/refs/tags/{PAPYGREEK_VERSION}"
PAPYGREEK_REPOSITORY_URL = "https://github.com/papygreek/papygreek-treebanks"
PAPYGREEK_PORTAL_URL = "https://papygreek.com/"
PAPYGREEK_LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"

LIGRE_LEMMA_BANK_VERSION = "v0.1.0"
LIGRE_LEMMA_BANK_URL = (
    f"https://raw.githubusercontent.com/ligre-lod/ligre_lemmabank/{LIGRE_LEMMA_BANK_VERSION}/ttl/ligre_lemmabank.ttl"
)

TRISMEGISTOS_TEXT_URL = "https://www.trismegistos.org/text/{}"
PAPYRI_INFO_HGV_URL = "https://papyri.info/hgv/{}"

DEFAULT_BASE_IRI = "https://w3id.org/ligre"
CORPUS_NAME = "PapyGreek"
CORPUS_TITLE = "PapyGreek Treebanks"

CORPUS_VERSION = citation_field("version")
CORPUS_REPOSITORY_URL = "https://github.com/ligre-lod/papygreek"
CORPUS_RELEASE_URL = f"{CORPUS_REPOSITORY_URL}/releases/tag/v{CORPUS_VERSION}"
CORPUS_DOWNLOAD_URL = (
    CORPUS_REPOSITORY_URL.replace("github.com", "raw.githubusercontent.com")
    + f"/v{CORPUS_VERSION}/ttl/complete_papygreek.ttl.gz"
)
KNOWLEDGE_BASE_HOMEPAGE = "https://ligre-lod.github.io/"
CORPUS_DESCRIPTION = (
    "The PapyGreek treebanks (558 documentary papyri in Postclassical Greek, ca. 300 BCE-700 CE, morphosyntactically "
    "annotated by the Digital Grammar of Greek Documentary Papyri project) as linked data, with every token linked "
    "to its lemma in the LiGre Lemma Bank for Ancient Greek, following the model of the LiLa Knowledge Base corpora."
)
CORPUS_KEYWORDS = ("Ancient Greek", "Postclassical Greek", "documentary papyri", "treebank", "lemmatization",
                   "linked data", "LiGre")
CORPUS_CREATORS = (
    {"name": "Paulien Lemay", "iri": "https://orcid.org/0009-0004-2388-9233"},
)
CORPUS_PUBLISHER = {"name": "Ghent University", "iri": "https://ror.org/00cv9y106"}
CORPUS_ISSUED = citation_field("date-released")
CORPUS_DOI = f"https://doi.org/{citation_field('doi')}" if citation_field("doi") else ""
CORPUS_BIBLIOGRAPHIC_CITATION = ""

DEFAULT_DATA_DIRECTORY = Path("data")
DEFAULT_OUTPUT_DIRECTORY = Path("ttl")
DEFAULT_REVIEW_DIRECTORY = Path("review")

PAPYGREEK_ARCHIVE_FILENAME = "papygreek-treebanks.zip"
PAPYGREEK_EXTRACTION_DIRECTORY = "papygreek-treebanks"
LEMMA_BANK_FILENAME = "ligre_lemmabank.ttl"

TEXTS_OUTPUT_DIRECTORY = "texts"
CORPUS_OUTPUT_FILENAME = "PapyGreek_corpus.ttl"
COMPLETE_OUTPUT_FILENAME = "complete_papygreek.ttl.gz"

LEMMA_POS_DECISIONS_FILENAME = "decisions_lemmas.tsv"

LINKING_SUMMARY_FILENAME = "review_summary.tsv"
POS_CLASH_LEMMAS_FILENAME = "review_lemmas.tsv"
NO_LIGRE_LEMMA_FILENAME = "review_no_ligre_lemma.tsv"
NOT_A_WORD_FILENAME = "review_not_a_word.tsv"
