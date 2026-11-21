#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "bm25s>=0.3.9,<1",
# ]
# ///
"""Rank line-windows in a parsed text file with BM25."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TypedDict

import bm25s


class LineRecord(TypedDict):
    index: int  # 1-based line number in the source file
    content: str


def _load_corpus(file_path: Path) -> list[LineRecord]:
    text = file_path.read_text(encoding="utf-8", errors="replace")
    return [
        {"index": i + 1, "content": line}
        for i, line in enumerate(text.splitlines())
    ]


def _expand(corpus: list[LineRecord], match: LineRecord, n: int) -> str:
    idx = match["index"] - 1
    start = max(0, idx - n)
    end = min(len(corpus) - 1, idx + n)
    header = f"Lines {corpus[start]['index']} - {corpus[end]['index']}"
    body = "\n".join(c["content"] for c in corpus[start : end + 1])
    return f"{header}\n\n{body}"


def retrieve(
    file_path: Path,
    query: str,
    top_k: int = 10,
    expand: int = 5,
) -> list[str]:
    corpus = _load_corpus(file_path)
    if not corpus or top_k <= 0:
        return []

    k = min(top_k, len(corpus))
    corpus_tokens = bm25s.tokenize([c["content"] for c in corpus], show_progress=False)
    retriever = bm25s.BM25(corpus=corpus)
    retriever.index(corpus_tokens, show_progress=False)
    query_tokens = bm25s.tokenize(query, show_progress=False)
    docs, scores = retriever.retrieve(query_tokens, k=k, show_progress=False)

    results: list[str] = []
    for doc, score in zip(docs[0].tolist(), scores[0].tolist()):
        if float(score) <= 0.0:
            continue
        results.append(_expand(corpus, doc, max(0, expand)))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="BM25 ranked line-window search over a parsed text file."
    )
    parser.add_argument("file_path", type=Path, help="Path to the text file to search")
    parser.add_argument(
        "-q", "--query", help="Keyword-based query to search for", required=True
    )
    parser.add_argument(
        "-k",
        "--top-k",
        help="Top K matches to retrieve (default: 10)",
        type=int,
        default=10,
    )
    parser.add_argument(
        "-e",
        "--expand",
        help="Context lines before and after each match (default: 5; 0 = matched line only)",
        type=int,
        default=5,
    )
    args = parser.parse_args()

    if not args.file_path.is_file():
        sys.exit(f"error: file not found: {args.file_path}")

    results = retrieve(args.file_path, args.query, top_k=args.top_k, expand=args.expand)
    if results:
        separator = "\n" + "─" * 60 + "\n"
        for i, match_text in enumerate(results):
            print(f"Match #{i}")
            print(match_text.strip("\n"))
            if i < len(results) - 1:
                print(separator)
    else:
        print("No relevant matches found")


if __name__ == "__main__":
    main()
