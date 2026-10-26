import argparse
import logging
from pathlib import Path

from . import settings
from .pipeline import PipelineOptions, run_pipeline


def parse_arguments():
    parser = argparse.ArgumentParser(
        prog="python -m papygreek_to_ligre",
        description="Convert the PapyGreek treebanks into LiLa-style RDF linked to the LiGre lemma bank.",
    )
    parser.add_argument("--data-dir", type=Path, default=settings.DEFAULT_DATA_DIRECTORY)
    parser.add_argument("--output-dir", type=Path, default=settings.DEFAULT_OUTPUT_DIRECTORY)
    parser.add_argument("--base-iri", default=settings.DEFAULT_BASE_IRI)
    parser.add_argument("--refresh", action="store_true", help="download the sources again")
    parser.add_argument("--skip-complete-file", action="store_true", help="only write one Turtle file per text")
    return parser.parse_args()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    arguments = parse_arguments()
    run_pipeline(PipelineOptions(
        data_directory=arguments.data_dir,
        output_directory=arguments.output_dir,
        base_iri=arguments.base_iri,
        refresh_downloads=arguments.refresh,
        write_complete_file=not arguments.skip_complete_file,
    ))


if __name__ == "__main__":
    main()
