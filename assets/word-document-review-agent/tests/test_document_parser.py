"""Unit tests for document_parser tool."""
import sys
import os
from pathlib import Path

# Add app/ to path for peer-level imports
APP_DIR = Path(__file__).parent.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import pytest
import tempfile
from docx import Document

from tools.document_parser import parse_document


def _make_temp_docx(paragraphs: list[str]) -> str:
    """Create a temporary .docx file with the given paragraphs."""
    doc = Document()
    for text in paragraphs:
        doc.add_paragraph(text)
    tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
    doc.save(tmp.name)
    tmp.close()
    return tmp.name


def test_parse_document_returns_paragraphs():
    path = _make_temp_docx(["Hello world.", "Second paragraph."])
    try:
        result = parse_document(path)
        assert "paragraphs" in result
        texts = [p["text"] for p in result["paragraphs"]]
        assert "Hello world." in texts
        assert "Second paragraph." in texts
    finally:
        os.unlink(path)


def test_parse_document_paragraph_count():
    path = _make_temp_docx(["Para one.", "Para two.", "Para three."])
    try:
        result = parse_document(path)
        non_empty = [p for p in result["paragraphs"] if p["text"].strip()]
        assert len(non_empty) >= 3
    finally:
        os.unlink(path)


def test_parse_document_paragraph_index():
    path = _make_temp_docx(["First.", "Second."])
    try:
        result = parse_document(path)
        for i, para in enumerate(result["paragraphs"]):
            assert para["index"] == i
    finally:
        os.unlink(path)


def test_parse_document_file_not_found():
    with pytest.raises(ValueError, match="not found"):
        parse_document("/nonexistent/path/file.docx")


def test_parse_document_non_docx():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp.write(b"some text")
        path = tmp.name
    try:
        with pytest.raises(ValueError, match="not a .docx"):
            parse_document(path)
    finally:
        os.unlink(path)


def test_parse_document_runs_present():
    path = _make_temp_docx(["Run text here."])
    try:
        result = parse_document(path)
        non_empty = [p for p in result["paragraphs"] if p["text"].strip()]
        assert len(non_empty) > 0
        assert "runs" in non_empty[0]
        assert isinstance(non_empty[0]["runs"], list)
    finally:
        os.unlink(path)
