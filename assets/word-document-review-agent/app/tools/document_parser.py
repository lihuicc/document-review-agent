"""Document parser tool — reads a .docx file and extracts paragraph content."""
import logging
from pathlib import Path
from typing import Any

from docx import Document

logger = logging.getLogger(__name__)


def parse_document(file_path: str) -> dict[str, Any]:
    """Parse a .docx file and return structured paragraph data.

    Args:
        file_path: Path to the .docx file to parse.

    Returns:
        A dict with key 'paragraphs', each containing:
            - index: int (0-based paragraph index)
            - text: str (full paragraph text)
            - runs: list of run texts within the paragraph

    Raises:
        ValueError: If the file does not exist or is not a valid .docx.
    """
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"File not found: {file_path}")
    if path.suffix.lower() != ".docx":
        raise ValueError(f"File is not a .docx: {file_path}")

    try:
        doc = Document(str(path))
    except Exception as e:
        raise ValueError(f"Could not open document: {e}") from e

    paragraphs = []
    for idx, para in enumerate(doc.paragraphs):
        paragraphs.append({
            "index": idx,
            "text": para.text,
            "runs": [run.text for run in para.runs],
        })

    logger.info("Parsed %d paragraphs from %s", len(paragraphs), file_path)
    return {"paragraphs": paragraphs}
