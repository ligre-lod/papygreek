"""The hand annotations, one row per PapyGreek lemma, in a TSV file rewritten after every change."""

import csv
import datetime
import logging
import os
import threading

from papygreek_to_ligre import settings
from papygreek_to_ligre.linking.lemma_bank import lemma_key
from papygreek_to_ligre.linking.not_a_word import NOT_A_WORD_STATUS
from papygreek_to_ligre.linking.pos_tags import papygreek_pos

logger = logging.getLogger(__name__)

ANNOTATIONS_FILENAME = settings.NO_LIGRE_LEMMA_ANNOTATIONS_FILENAME
TOKEN_LEVEL_BACKUP_SUFFIX = ".token-level.tsv"
STATUSES = ("checked", "unsure", NOT_A_WORD_STATUS)
# How a lemma relates to another one, given in `related` (a LiGre lemma id, or the key of another PapyGreek lemma here):
# written_rep: the same lemma in another spelling, an extra ontolex:writtenRep of that lemma (Σεραπίων of Σαραπίων);
# lemma_variant: a lemma of its own, linked to the other with lila:lemmaVariant (ἑκατέρως of ἑκάτερος).
RELATIONS = ("", "written_rep", "lemma_variant")
COLUMNS = (
    "papygreek_lemma", "papygreek_pos", "tokens", "lemma", "pos", "ligre_lemma", "relation", "related",
    "status", "note", "annotated",
)
ANNOTATION_FIELDS = ("lemma", "pos", "ligre_lemma", "relation", "related", "status", "note", "annotated")


def row_key(row):
    return f"{lemma_key(row['papygreek_lemma'])}|{row['papygreek_pos']}"


class AnnotationStore:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.rows = {}
        if not path.exists():
            return
        with path.open(newline="", encoding="utf-8") as input_file:
            reader = csv.DictReader(input_file, delimiter="\t")
            rows = list(reader)
            token_level = "token" in (reader.fieldnames or [])
        if token_level:
            self.convert_token_level(rows)
        else:
            for row in rows:
                self.rows[row_key(row)] = {column: row.get(column) or "" for column in COLUMNS}

    def convert_token_level(self, token_rows):
        """The first version stored one row per token: keep one row per lemma, back up the old file."""
        for row in token_rows:
            converted = {
                "papygreek_lemma": row["papygreek_lemma"],
                "papygreek_pos": papygreek_pos(row["papygreek_postag"]),
                "tokens": "",
                **{column: row.get(column, "") for column in ANNOTATION_FIELDS},
            }
            key = row_key(converted)
            previous = self.rows.get(key)
            if previous and (previous["lemma"], previous["pos"]) != (converted["lemma"], converted["pos"]):
                converted["status"] = "unsure"
                converted["note"] = "; ".join(filter(None, (
                    previous["note"], f"token-level annotations disagreed: {previous['lemma']} {previous['pos']}")))
            self.rows[key] = converted
        backup = self.path.with_name(self.path.stem + TOKEN_LEVEL_BACKUP_SUFFIX)
        self.path.replace(backup)
        logger.info("Converted %d token annotations into %d lemma annotations; the old file is %s",
                    len(token_rows), len(self.rows), backup)
        self.save()

    def annotate(self, group, lemma, pos, ligre_lemma, relation, related, status, note):
        if status not in STATUSES:
            raise ValueError(f"unknown status {status!r}")
        if relation not in RELATIONS:
            raise ValueError(f"unknown relation {relation!r}")
        with self.lock:
            self.rows[group.key] = {
                "papygreek_lemma": group.lemma,
                "papygreek_pos": group.pos,
                "tokens": str(len(group.targets)),
                "lemma": lemma,
                "pos": pos,
                "ligre_lemma": ligre_lemma,
                "relation": relation,
                "related": related,
                "status": status,
                "note": note,
                "annotated": datetime.datetime.now().isoformat(timespec="seconds"),
            }
            self.save()

    def remove(self, key):
        with self.lock:
            if self.rows.pop(key, None) is not None:
                self.save()

    def save(self):
        temporary_path = self.path.with_suffix(".tsv.part")
        with temporary_path.open("w", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(output_file, COLUMNS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            for key in sorted(self.rows):
                writer.writerow(self.rows[key])
            output_file.flush()
            os.fsync(output_file.fileno())
        temporary_path.replace(self.path)
