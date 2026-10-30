import logging
import shutil
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from .. import settings

logger = logging.getLogger(__name__)


def download_file(url, destination, refresh=False):
    if destination.exists() and not refresh:
        logger.info("Using cached %s", destination)
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_destination = destination.with_suffix(destination.suffix + ".part")
    logger.info("Downloading %s", url)
    with urllib.request.urlopen(url) as response, temporary_destination.open("wb") as output_file:
        shutil.copyfileobj(response, output_file)
    temporary_destination.replace(destination)
    return destination


def extract_treebank_files(archive_path, extraction_directory, refresh=False):
    if extraction_directory.exists() and not refresh:
        logger.info("Using extracted treebanks in %s", extraction_directory)
        return extraction_directory
    if extraction_directory.exists():
        shutil.rmtree(extraction_directory)
    extraction_directory.mkdir(parents=True)
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            relative_path = treebank_member_path(member)
            if relative_path is None:
                continue
            target_path = extraction_directory.joinpath(*relative_path.parts)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target_path.open("wb") as target:
                shutil.copyfileobj(source, target)
    return extraction_directory


def treebank_member_path(member):
    if member.is_dir():
        return None
    member_path = PurePosixPath(member.filename)
    relative_path = PurePosixPath(*member_path.parts[1:])
    if member_path.suffix != ".xml" or ".." in relative_path.parts or relative_path.is_absolute():
        return None
    return relative_path


def fetch_papygreek_treebanks(data_directory, refresh=False):
    archive_path = download_file(
        settings.PAPYGREEK_ARCHIVE_URL,
        data_directory / settings.PAPYGREEK_ARCHIVE_FILENAME,
        refresh,
    )
    return extract_treebank_files(
        archive_path,
        data_directory / settings.PAPYGREEK_EXTRACTION_DIRECTORY,
        refresh,
    )


def fetch_ligre_lemma_bank(data_directory, refresh=False):
    return download_file(
        settings.LIGRE_LEMMA_BANK_URL,
        data_directory / settings.LEMMA_BANK_FILENAME,
        refresh,
    )


def find_treebank_files(treebank_directory):
    return sorted(Path(treebank_directory).rglob("*.xml"))
