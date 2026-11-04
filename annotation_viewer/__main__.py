import argparse
import logging
from pathlib import Path

from papygreek_to_ligre import settings

from .annotations import ANNOTATIONS_FILENAME, AnnotationStore
from .corpus import Corpus
from .server import ViewerApp, serve
from .translations import Translations


def parse_arguments():
    parser = argparse.ArgumentParser(
        prog="python -m annotation_viewer",
        description="Annotate, in context, the PapyGreek tokens whose lemma is missing from LiGre.",
    )
    parser.add_argument("--data-dir", type=Path, default=settings.DEFAULT_DATA_DIRECTORY)
    parser.add_argument("--review-dir", type=Path, default=settings.DEFAULT_REVIEW_DIRECTORY)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--fetch-translations", action="store_true",
                        help="download the papyri.info translations that were not fetched yet "
                             "(one small request per HGV id, cached in data/translations/)")
    return parser.parse_args()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    arguments = parse_arguments()
    corpus = Corpus(arguments.data_dir, arguments.review_dir)
    translations = Translations(arguments.data_dir)
    if arguments.fetch_translations:
        translations.fetch({hgv_id for document in corpus.documents.values() for hgv_id in document.hgv_ids})
    annotations = AnnotationStore(arguments.review_dir / ANNOTATIONS_FILENAME)
    serve(ViewerApp(corpus, annotations, translations), arguments.host, arguments.port)


if __name__ == "__main__":
    main()
