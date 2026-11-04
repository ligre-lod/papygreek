"""A small local HTTP server: static files plus a JSON API over the corpus and the annotations."""

import json
import logging
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from papygreek_to_ligre.linking.pos_tags import UNIVERSAL_TAGS

from papygreek_to_ligre.linking.not_a_word import MARKER_DESCRIPTIONS, NOT_A_WORD_STATUS

from .annotations import RELATIONS, STATUSES

logger = logging.getLogger(__name__)

STATIC_DIRECTORY = Path(__file__).parent / "static"
# Punctuation and symbols are left out: punctuation tokens are never linked.
POS_ORDER = ("PROPN", "NOUN", "ADJ", "VERB", "AUX", "ADV", "NUM", "PRON", "DET", "ADP",
             "CCONJ", "SCONJ", "PART", "INTJ", "X")


class ApiError(Exception):
    pass


class ViewerApp:
    def __init__(self, corpus, annotations, translations):
        self.corpus = corpus
        self.annotations = annotations
        self.translations = translations
        self.translated_documents = {identifier for identifier, document in corpus.documents.items()
                                     if translations.has_translation(document.hgv_ids)}
        self.ligre_tag_counts = {tag: 0 for tag in POS_ORDER}
        for entry in corpus.lemma_bank.entries_by_id.values():
            for tag in entry.universal_tags:
                if tag in self.ligre_tag_counts:
                    self.ligre_tag_counts[tag] += 1
        self.fill_token_counts()

    def fill_token_counts(self):
        """Rows converted from the token-level file have no token count yet."""
        changed = False
        for key, row in self.annotations.rows.items():
            group = self.corpus.groups.get(key)
            if group and row["tokens"] != str(len(group.targets)):
                row["tokens"] = str(len(group.targets))
                changed = True
        if changed:
            self.annotations.save()

    def public_annotations(self):
        return {key: {**{column: row[column] for column in ("lemma", "pos", "ligre_lemma", "relation", "related",
                                                             "status", "note")},
                      "related_label": self.related_label(row["related"])}
                for key, row in self.annotations.rows.items() if key in self.corpus.groups}

    def related_label(self, related):
        """A LiGre lemma id, or the key of another PapyGreek lemma (with its annotated lemma, if any)."""
        if not related:
            return ""
        if related in self.corpus.groups:
            row = self.annotations.rows.get(related)
            group = self.corpus.groups[related]
            annotated = f" → {row['lemma']} · {row['pos']}" if row and row["lemma"] else ", not annotated yet"
            return f"{group.lemma} (PapyGreek {group.pos}{annotated})"
        return self.corpus.ligre_label(related)

    def check_relation(self, group, relation, related):
        if relation not in RELATIONS:
            raise ApiError(f"unknown relation {relation!r}")
        if not relation:
            return
        if not related:
            raise ApiError("choose the lemma this one is related to")
        if related == group.key:
            raise ApiError("a lemma cannot be related to itself")
        if related not in self.corpus.groups and self.corpus.lemma_bank.entry(related) is None:
            raise ApiError(f"{related!r} is neither a LiGre lemma id nor a PapyGreek lemma here")
        if relation != "written_rep":
            return
        # Spellings point straight at their lemma: no chains of spellings.
        target = self.annotations.rows.get(related)
        if target and target["relation"] == "written_rep":
            raise ApiError(f"{self.corpus.groups[related].lemma} is itself a spelling of "
                           f"{self.related_label(target['related'])}: choose that lemma instead")
        pointing_here = [self.corpus.groups[key].lemma for key, row in self.annotations.rows.items()
                         if row["relation"] == "written_rep" and row["related"] == group.key and key in self.corpus.groups]
        if pointing_here:
            raise ApiError(f"{', '.join(pointing_here)} already point here as other spellings of this lemma: "
                           f"make this the lemma, or point those at the other lemma first")

    def overview(self, _query):
        groups = sorted(self.corpus.groups.values(), key=lambda group: (-len(group.targets), group.lemma))
        annotations = self.public_annotations()
        return {
            "lemmas": [{**self.corpus.summary(group), "translated": self.translated_texts(group)} for group in groups],
            "annotations": annotations,
            "stale_annotations": len(self.annotations.rows) - len(annotations),
            "tokens_total": len(self.corpus.targets),
            "tags": [{"tag": tag, "ligre": self.ligre_tag_counts[tag]} for tag in POS_ORDER if tag in UNIVERSAL_TAGS],
            "annotations_file": str(self.annotations.path),
            "not_a_word": self.not_a_word_summary(annotations),
        }

    def translated_texts(self, group):
        """How many of the texts this lemma occurs in have a papyri.info translation."""
        return len({target.document for target in group.targets} & self.translated_documents)

    def not_a_word_summary(self, annotations):
        """Tokens left out as not a word, per marker: automatic (pipeline rules) and by hand (here)."""
        manual = [self.corpus.groups[key] for key, row in annotations.items() if row["status"] == NOT_A_WORD_STATUS]
        markers = [{"marker": marker, "tokens": count, "description": MARKER_DESCRIPTIONS.get(marker, "")}
                   for marker, count in self.corpus.automatic_not_a_word.most_common()]
        if manual:
            markers.append({"marker": "manual", "tokens": sum(len(group.targets) for group in manual),
                            "lemmas": len(manual), "description": MARKER_DESCRIPTIONS["manual"]})
        return {"tokens": sum(item["tokens"] for item in markers), "markers": markers}

    def lemma(self, query):
        key = query.get("key", [""])[0]
        if key not in self.corpus.groups:
            raise ApiError(f"unknown lemma {key!r}")
        payload = self.corpus.lemma_payload(key)
        for occurrence in payload["occurrences"]:
            occurrence["translated"] = occurrence["document"] in self.translated_documents
        return payload

    def document(self, query):
        document_id = query.get("id", [""])[0]
        lemma_key = query.get("lemma", [""])[0]
        if document_id not in self.corpus.documents:
            raise ApiError(f"unknown document {document_id!r}")
        payload = self.corpus.document_payload(document_id, lemma_key)
        payload["translations"] = self.translations.for_document(payload["hgv_ids"])
        payload["translations_probed"] = self.translations.probed(payload["hgv_ids"])
        return payload

    def ligre(self, query):
        return {"results": self.corpus.search_ligre(query.get("q", [""])[0])}

    def annotate(self, body):
        group = self.corpus.groups.get(body.get("key", ""))
        lemma = str(body.get("lemma", "")).strip()
        pos = body.get("pos", "")
        ligre_lemma = str(body.get("ligre_lemma", "") or "").strip()
        relation = str(body.get("relation", "") or "")
        related = str(body.get("related", "") or "").strip()
        status = body.get("status", "")
        if group is None:
            raise ApiError(f"unknown lemma {body.get('key')!r}")
        if status == NOT_A_WORD_STATUS:
            lemma, pos, ligre_lemma, relation, related = "", "", "", "", ""
        elif not lemma:
            raise ApiError("the lemma is empty")
        elif pos not in UNIVERSAL_TAGS:
            raise ApiError(f"unknown part of speech {pos!r}")
        if ligre_lemma and self.corpus.lemma_bank.entry(ligre_lemma) is None:
            raise ApiError(f"LiGre has no lemma with id {ligre_lemma!r}")
        if status not in STATUSES:
            raise ApiError(f"unknown status {status!r}")
        if not relation:
            related = ""
        self.check_relation(group, relation, related)
        if relation == "written_rep" and related not in self.corpus.groups:
            ligre_lemma = related  # another spelling of a LiGre lemma: its tokens link to that lemma
        self.annotations.annotate(group, lemma, pos, ligre_lemma, relation, related, status,
                                  str(body.get("note", "")).strip())
        return self.overview({})

    def remove(self, body):
        self.annotations.remove(body.get("key", ""))
        return self.overview({})


def make_handler(app):
    get_routes = {"/api/overview": app.overview, "/api/lemma": app.lemma,
                  "/api/document": app.document, "/api/ligre": app.ligre}
    post_routes = {"/api/annotate": app.annotate, "/api/remove": app.remove}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            logger.debug(format, *args)

        def send_json(self, payload, status=HTTPStatus.OK):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def run(self, route, argument):
            try:
                self.send_json(route(argument))
            except ApiError as error:
                self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            except Exception as error:  # keep the server running; show the error in the page
                logger.exception("Request failed")
                self.send_json({"error": f"server error: {error}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path in get_routes:
                return self.run(get_routes[url.path], parse_qs(url.query))
            self.send_static(url.path)

        def do_POST(self):
            url = urlparse(self.path)
            if url.path not in post_routes:
                return self.send_error(HTTPStatus.NOT_FOUND)
            length = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return self.send_json({"error": "invalid JSON"}, HTTPStatus.BAD_REQUEST)
            self.run(post_routes[url.path], body)

        def send_static(self, path):
            relative = "index.html" if path in ("", "/") else path.lstrip("/")
            file_path = (STATIC_DIRECTORY / relative).resolve()
            if STATIC_DIRECTORY.resolve() not in file_path.parents or not file_path.is_file():
                return self.send_error(HTTPStatus.NOT_FOUND)
            body = file_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    return Handler


def serve(app, host, port):
    server = ThreadingHTTPServer((host, port), make_handler(app))
    logger.info("Annotation viewer running at http://%s:%d/ (stop with Ctrl+C)", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopped; annotations are in %s", app.annotations.path)
    finally:
        server.server_close()
