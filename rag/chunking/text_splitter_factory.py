"""
Build configured RecursiveCharacter-style splitters for medical vs medication pipelines.

Splitter behavior mirrors LangChain's RecursiveCharacterTextSplitter without importing it
(so optional heavy LangChain/tensorflow stacks are avoided). Derived from LangChain's
Apache 2.0-licensed implementation.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Iterable
import tiktoken

from rag.config import (
    MEDICAL_CHUNK_OVERLAP_TOKENS,
    MEDICAL_CHUNK_SIZE_TOKENS,
    MEDICATION_CHUNK_OVERLAP_TOKENS,
    MEDICATION_CHUNK_SIZE_TOKENS,
    TIKTOKEN_ENCODING_NAME,
)

logger = logging.getLogger(__name__)


def _split_text_with_regex(
    text: str,
    separator: str,
    *,
    keep_separator: bool,
) -> list[str]:
    if not separator:
        return list(text) if text else []
    splits_ = re.split(separator, text)
    splits = splits_
    # RAG callers use keep_separator=False only (consistent with downstream merge glue).
    if keep_separator:
        raise ValueError("keep_separator paths are unsupported in rag chunking")
    return [s for s in splits if s]


class RecursiveCharacterTextSplitter:
    """
    Recursive splitter that prefers early separators (\n\n, \n, etc.) before hard cuts.
    """

    def __init__(
        self,
        *,
        chunk_size: int,
        chunk_overlap: int,
        separators: list[str] | None = None,
        length_function: Callable[[str], int] = len,
        keep_separator: bool = False,
        strip_whitespace: bool = True,
        is_separator_regex: bool = False,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError(f"chunk_size must be positive, got {chunk_size}")
        if chunk_overlap < 0:
            raise ValueError(f"chunk_overlap must be non-negative, got {chunk_overlap}")
        if chunk_overlap > chunk_size:
            raise ValueError("chunk_overlap must be <= chunk_size")
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._separators = separators if separators is not None else ["\n\n", "\n", " ", ""]
        self._length_function = length_function
        self._keep_separator = keep_separator  # noqa: FBT003
        self._strip_whitespace = strip_whitespace  # noqa: FBT003
        self._is_separator_regex = is_separator_regex  # noqa: FBT003

    def split_text(self, text: str) -> list[str]:
        """Return chunk strings honoring ``chunk_size`` under ``length_function``."""
        return self._split_text(text, self._separators)

    def _join_docs(self, docs: list[str], separator: str) -> str | None:
        result = separator.join(docs)
        if self._strip_whitespace:
            result = result.strip()
        return result or None

    def _merge_splits(self, splits: Iterable[str], separator: str) -> list[str]:
        separator_len = self._length_function(separator)
        docs: list[str] = []
        current_doc: list[str] = []
        total = 0
        for piece in splits:
            len_piece = self._length_function(piece)
            if (
                total + len_piece + (separator_len if len(current_doc) > 0 else 0)
                > self._chunk_size
            ):
                if total > self._chunk_size:
                    logger.warning(
                        "Created chunk metric %s above chunk_size=%s.",
                        total,
                        self._chunk_size,
                    )
                if len(current_doc) > 0:
                    doc = self._join_docs(current_doc, separator)
                    if doc is not None:
                        docs.append(doc)
                    while total > self._chunk_overlap or (
                        total + len_piece + (separator_len if len(current_doc) > 0 else 0)
                        > self._chunk_size
                        and total > 0
                    ):
                        drop = current_doc[0]
                        total -= self._length_function(drop) + (
                            separator_len if len(current_doc) > 1 else 0
                        )
                        current_doc = current_doc[1:]
            current_doc.append(piece)
            total += len_piece + (separator_len if len(current_doc) > 1 else 0)
        tail = self._join_docs(current_doc, separator)
        if tail is not None:
            docs.append(tail)
        return docs

    def _split_text(self, text: str, separators: list[str]) -> list[str]:
        final_chunks: list[str] = []
        separator = separators[-1]
        new_separators: list[str] = []

        for i, candidate in enumerate(separators):
            pattern = candidate if self._is_separator_regex else re.escape(candidate)
            if not candidate:
                separator = candidate
                break
            if re.search(pattern, text):
                separator = candidate
                new_separators = separators[i + 1 :]
                break

        pattern = separator if self._is_separator_regex else re.escape(separator)
        splits_list = _split_text_with_regex(
            text,
            pattern,
            keep_separator=self._keep_separator,
        )

        sep_for_merge = "" if self._keep_separator else separator
        good_splits: list[str] = []
        for s in splits_list:
            if self._length_function(s) < self._chunk_size:
                good_splits.append(s)
            else:
                if good_splits:
                    merged = self._merge_splits(good_splits, sep_for_merge)
                    final_chunks.extend(merged)
                    good_splits = []
                if not new_separators:
                    final_chunks.append(s)
                else:
                    nested = self._split_text(s, new_separators)
                    final_chunks.extend(nested)
        if good_splits:
            merged = self._merge_splits(good_splits, sep_for_merge)
            final_chunks.extend(merged)

        return final_chunks


def create_medical_text_splitter() -> RecursiveCharacterTextSplitter:
    """tiktoken-aware splitter for medical prose; paragraph/newline/word boundaries."""
    enc = tiktoken.get_encoding(TIKTOKEN_ENCODING_NAME)

    def token_len(t: str) -> int:
        return len(enc.encode(t))

    return RecursiveCharacterTextSplitter(
        chunk_size=MEDICAL_CHUNK_SIZE_TOKENS,
        chunk_overlap=MEDICAL_CHUNK_OVERLAP_TOKENS,
        separators=["\n\n", "\n", " ", ""],
        length_function=token_len,
        keep_separator=False,
        strip_whitespace=True,
    )


def create_medication_text_splitter() -> RecursiveCharacterTextSplitter:
    """tiktoken-aware splitter applied only when aggregated prose exceeds token threshold."""
    enc = tiktoken.get_encoding(TIKTOKEN_ENCODING_NAME)

    def token_len(t: str) -> int:
        return len(enc.encode(t))

    return RecursiveCharacterTextSplitter(
        chunk_size=MEDICATION_CHUNK_SIZE_TOKENS,
        chunk_overlap=MEDICATION_CHUNK_OVERLAP_TOKENS,
        separators=["\n\n", "\n", ". ", "; ", ": ", ", ", " ", ""],
        length_function=token_len,
        keep_separator=False,
        strip_whitespace=True,
    )


def medication_group_token_length(text: str) -> int:
    """tiktoken measurement for medication bundle sizing decisions."""
    enc = tiktoken.get_encoding(TIKTOKEN_ENCODING_NAME)
    return len(enc.encode(text))
