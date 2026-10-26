import re
from dataclasses import dataclass, field

RESTARTING_LINE_NUMBER = 1
LEADING_NUMBER = re.compile(r"\d+")


@dataclass(frozen=True)
class PlacedToken:
    index: int
    sentence_id: int
    word: object
    part_number: int


@dataclass
class TextPart:
    number: int
    tokens_by_line: dict = field(default_factory=dict)
    tokens: list = field(default_factory=list)


@dataclass
class SentenceSpan:
    sentence_id: int
    tokens: list


@dataclass
class DocumentLayout:
    tokens: list
    parts: list
    sentences: list


def leading_line_number(line):
    match = LEADING_NUMBER.match(line)
    return int(match.group()) if match else None


def is_margin_line(line):
    return "," in line


def starts_new_part(line, previous_line_number):
    line_number = leading_line_number(line)
    return (
        line_number is not None
        and not is_margin_line(line)
        and previous_line_number is not None
        and line_number <= RESTARTING_LINE_NUMBER < previous_line_number
    )


def build_document_layout(document):
    tokens = []
    parts = [TextPart(number=1)]
    sentences = []
    previous_line_number = None

    for sentence in document.sentences:
        sentence_tokens = []
        for word in sentence.textual_words:
            if word.line and starts_new_part(word.line, previous_line_number):
                parts.append(TextPart(number=len(parts) + 1))
            line_number = leading_line_number(word.line)
            if line_number is not None and not is_margin_line(word.line):
                previous_line_number = line_number

            current_part = parts[-1]
            token = PlacedToken(len(tokens) + 1, sentence.id, word, current_part.number)
            tokens.append(token)
            sentence_tokens.append(token)
            current_part.tokens.append(token)
            if word.line:
                current_part.tokens_by_line.setdefault(word.line, []).append(token)
        if sentence_tokens:
            sentences.append(SentenceSpan(sentence.id, sentence_tokens))

    return DocumentLayout(
        tokens=tokens,
        parts=[part for part in parts if part.tokens_by_line],
        sentences=sentences,
    )
