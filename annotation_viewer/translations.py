"""Translations from papyri.info (the Translations folder of github.com/papyri/idp.data).

Only some documentary papyri have one. Files are named <HGV id>-<n>.xml and sorted into
folders by HGV id // 1000. They are probed one by one on raw.githubusercontent.com (no API
rate limit) and cached in data/translations/, including the ids that have none, so every
id is requested only once.
"""

import json
import logging
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ElementTree

logger = logging.getLogger(__name__)

TRANSLATION_URL = "https://raw.githubusercontent.com/papyri/idp.data/master/Translations/{folder}/{name}"
TRANSLATIONS_DIRECTORY = "translations"
INDEX_FILENAME = "index.json"
TEI = "{http://www.tei-c.org/ns/1.0}"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
LEADING_NUMBER = re.compile(r"\d+")
MAX_TRANSLATIONS_PER_TEXT = 9


def translation_folder(hgv_id):
    match = LEADING_NUMBER.match(hgv_id)
    return str(int(match.group()) // 1000) if match else None


def download(url, timeout=20):
    request = urllib.request.Request(url, headers={"User-Agent": "papygreek-to-ligre annotation viewer"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


class Translations:
    def __init__(self, data_directory):
        self.directory = data_directory / TRANSLATIONS_DIRECTORY
        self.index_path = self.directory / INDEX_FILENAME
        self.index = json.loads(self.index_path.read_text(encoding="utf-8")) if self.index_path.exists() else {}

    def fetch(self, hgv_ids):
        """Download the translations of the ids that were never probed."""
        self.directory.mkdir(parents=True, exist_ok=True)
        to_probe = sorted({hgv_id for hgv_id in hgv_ids if hgv_id not in self.index and translation_folder(hgv_id)})
        logger.info("Probing papyri.info translations for %d HGV ids", len(to_probe))
        for count, hgv_id in enumerate(to_probe, 1):
            names = []
            for number in range(1, MAX_TRANSLATIONS_PER_TEXT + 1):
                name = f"{hgv_id}-{number}.xml"
                content = download(TRANSLATION_URL.format(folder=translation_folder(hgv_id), name=name))
                if content is None:
                    break
                (self.directory / name).write_bytes(content)
                names.append(name)
            self.index[hgv_id] = names
            if count % 50 == 0 or count == len(to_probe):
                self.save_index()
                logger.info("Probed %d/%d ids, %d with a translation so far", count, len(to_probe),
                            sum(1 for found in self.index.values() if found))

    def save_index(self):
        temporary_path = self.index_path.with_suffix(".part")
        temporary_path.write_text(json.dumps(self.index, indent=1, sort_keys=True), encoding="utf-8")
        temporary_path.replace(self.index_path)

    def has_translation(self, hgv_ids):
        return any(self.index.get(hgv_id) for hgv_id in hgv_ids)

    def probed(self, hgv_ids):
        return all(hgv_id in self.index for hgv_id in hgv_ids)

    def for_document(self, hgv_ids):
        translations = []
        for hgv_id in hgv_ids:
            for name in self.index.get(hgv_id, []):
                path = self.directory / name
                if path.exists():
                    translations.extend(parse_translation(path, hgv_id))
        return translations


def parse_translation(path, hgv_id):
    root = ElementTree.parse(path).getroot()
    translations = []
    for division in root.iter(f"{TEI}div"):
        if division.get("type") != "translation":
            continue
        pieces = []
        collect_text(division, pieces)
        text = re.sub(r"[ \t]+", " ", "".join(pieces))
        text = re.sub(r" *\n *", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if text:
            translations.append({"hgv_id": hgv_id, "language": division.get(XML_LANG, ""), "text": text})
    return translations


def collect_text(element, pieces):
    """Text of a TEI translation; line milestones become (n) markers, blocks become paragraphs."""
    tag = element.tag.replace(TEI, "")
    if tag in ("milestone", "lb") and element.get("n"):
        pieces.append(f" ({element.get('n')}) ")
    if tag in ("p", "ab"):
        pieces.append("\n\n")
    if element.text:
        pieces.append(element.text)
    for child in element:
        collect_text(child, pieces)
        if child.tail:
            pieces.append(child.tail)
    if tag in ("p", "ab"):
        pieces.append("\n\n")
