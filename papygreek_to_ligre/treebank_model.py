from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Word:
    id: int
    form: str
    lemma: str
    postag: str
    line: str
    language: str
    artificial_type: Optional[str]

    @property
    def is_artificial(self):
        return self.artificial_type is not None


@dataclass(frozen=True)
class Sentence:
    id: int
    words: list

    @property
    def textual_words(self):
        return [word for word in self.words if not word.is_artificial]


@dataclass(frozen=True)
class DocumentMetadata:
    trismegistos_ids: list
    hgv_ids: list


@dataclass(frozen=True)
class TreebankDocument:
    identifier: str
    metadata: DocumentMetadata
    sentences: list = field(default_factory=list)
