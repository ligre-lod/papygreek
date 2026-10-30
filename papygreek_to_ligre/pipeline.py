import gzip
import logging
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

from . import settings
from .linking.lemma_bank import LemmaBank
from .linking.linker import LemmaLinker
from .linking.pos_decisions import load_pos_decisions
from .linking.review import LinkingReview
from .rdf.graph_builder import DocumentGraphBuilder, build_corpus_graph
from .rdf.iris import CorpusIris
from .rdf.namespaces import ligre_lemma_namespace
from .rdf.turtle_writer import OrderedTurtleWriter
from .sources.downloads import fetch_ligre_lemma_bank, fetch_papygreek_treebanks, find_treebank_files
from .sources.treebank_reader import read_treebank_document

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineOptions:
    data_directory: Path = settings.DEFAULT_DATA_DIRECTORY
    output_directory: Path = settings.DEFAULT_OUTPUT_DIRECTORY
    pos_review_directory: Path = settings.DEFAULT_POS_REVIEW_DIRECTORY
    base_iri: str = settings.DEFAULT_BASE_IRI
    refresh_downloads: bool = False
    write_complete_file: bool = True


def write_turtle_file(path, graph, subjects):
    with path.open("w", encoding="utf-8") as output_file:
        writer = OrderedTurtleWriter(output_file, graph.namespace_manager)
        writer.write_prefixes()
        writer.write_subjects(graph, subjects)


def open_complete_file_writer(stack, options, corpus_graph, corpus):
    if not options.write_complete_file:
        return None
    complete_path = options.output_directory / settings.COMPLETE_OUTPUT_FILENAME
    logger.info("Writing complete corpus to %s", complete_path)
    output_file = stack.enter_context(gzip.open(complete_path, "wt", encoding="utf-8"))
    writer = OrderedTurtleWriter(output_file, corpus_graph.namespace_manager)
    writer.write_prefixes()
    writer.write_subject(corpus_graph, corpus)
    return writer


def run_pipeline(options):
    treebank_directory = fetch_papygreek_treebanks(options.data_directory, options.refresh_downloads)
    lemma_bank_path = fetch_ligre_lemma_bank(options.data_directory, options.refresh_downloads)

    lemma_namespace = ligre_lemma_namespace(options.base_iri)
    iris = CorpusIris(options.base_iri)
    pos_decisions = load_pos_decisions(options.pos_review_directory)
    lemma_linker = LemmaLinker(LemmaBank.from_turtle(lemma_bank_path), pos_decisions)
    linking_review = LinkingReview()
    document_builder = DocumentGraphBuilder(iris, lemma_namespace, lemma_linker, linking_review)

    texts_directory = options.output_directory / settings.TEXTS_OUTPUT_DIRECTORY
    texts_directory.mkdir(parents=True, exist_ok=True)

    treebank_files = find_treebank_files(treebank_directory)
    corpus = iris.corpus()
    corpus_graph = build_corpus_graph(iris, lemma_namespace, [path.stem for path in treebank_files])
    write_turtle_file(options.output_directory / settings.CORPUS_OUTPUT_FILENAME, corpus_graph, [corpus])

    logger.info("Converting %d PapyGreek treebanks", len(treebank_files))
    with ExitStack() as stack:
        complete_file_writer = open_complete_file_writer(stack, options, corpus_graph, corpus)
        for treebank_file in treebank_files:
            document = read_treebank_document(treebank_file)
            built_document = document_builder.build(document)
            write_turtle_file(
                texts_directory / f"{document.identifier}.ttl",
                built_document.graph,
                [corpus, *built_document.subjects],
            )
            if complete_file_writer is not None:
                complete_file_writer.write_subjects(built_document.graph, built_document.subjects)

    linking_review.write(options.pos_review_directory)
    logger.info(linking_review.summary())
    logger.info("Wrote the linking review files into %s", options.pos_review_directory)
    logger.info("Converted %d documents into %s", len(treebank_files), options.output_directory)
