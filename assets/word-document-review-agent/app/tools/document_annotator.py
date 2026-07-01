"""Document annotator tool — writes inline Word comments into a .docx file."""
import logging
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from lxml import etree

logger = logging.getLogger(__name__)

REVIEW_AUTHOR = "AI Review Agent"
REVIEW_DATE = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _add_comment_to_paragraph(doc: Document, para_idx: int, comment_text: str, comment_id: int) -> None:
    """Insert a Word comment at the specified paragraph index."""
    paragraphs = doc.paragraphs
    if para_idx >= len(paragraphs):
        # Fall back to last paragraph
        para_idx = len(paragraphs) - 1
    if not paragraphs:
        return

    para = paragraphs[para_idx]

    # Build the comment XML element
    comments_part = _get_or_create_comments_part(doc)

    comment_elem = OxmlElement("w:comment")
    comment_elem.set(qn("w:id"), str(comment_id))
    comment_elem.set(qn("w:author"), REVIEW_AUTHOR)
    comment_elem.set(qn("w:date"), REVIEW_DATE)
    comment_elem.set(qn("w:initials"), "AI")

    comment_para = OxmlElement("w:p")
    comment_run = OxmlElement("w:r")
    comment_rpr = OxmlElement("w:rPr")
    comment_run.append(comment_rpr)
    comment_text_elem = OxmlElement("w:t")
    comment_text_elem.text = comment_text
    comment_text_elem.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    comment_run.append(comment_text_elem)
    comment_para.append(comment_run)
    comment_elem.append(comment_para)
    comments_part.append(comment_elem)

    # Add comment reference marks to the paragraph
    comment_start = OxmlElement("w:commentRangeStart")
    comment_start.set(qn("w:id"), str(comment_id))

    comment_end = OxmlElement("w:commentRangeEnd")
    comment_end.set(qn("w:id"), str(comment_id))

    comment_ref_run = OxmlElement("w:r")
    comment_ref = OxmlElement("w:commentReference")
    comment_ref.set(qn("w:id"), str(comment_id))
    comment_ref_run.append(comment_ref)

    # Insert at the start of the paragraph element
    para._element.insert(0, comment_start)
    para._element.append(comment_end)
    para._element.append(comment_ref_run)


def _get_or_create_comments_part(doc: Document):
    """Get or create the w:comments element in the document XML."""
    body = doc.element.body
    # Try to find existing comments element in document body (not standard location)
    # Comments live in a separate part: word/comments.xml
    # We use a simplified approach: attach to document body's parent (document element)
    document_element = doc.element

    # Check if comments part already exists in the document's part relationships
    try:
        from docx.opc.constants import RELATIONSHIP_TYPE as RT
        comments_part = doc.part.part_related_by("http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments")
        return comments_part._element
    except Exception:
        pass

    # Create a minimal comments XML structure directly on the document element
    # This is a simplified approach — attach comments as a child of the body
    # In a real implementation, comments live in word/comments.xml
    # Here we embed them in the document for simplicity
    existing = document_element.find(qn("w:comments"))
    if existing is not None:
        return existing

    comments_elem = OxmlElement("w:comments")
    document_element.append(comments_elem)
    return comments_elem


def annotate_document(file_path: str, issues: list[dict[str, Any]], output_path: str) -> str:
    """Write inline Word comments for each identified issue.

    Args:
        file_path: Path to the original .docx file.
        issues: List of issue dicts, each with keys:
            - paragraph_index: int
            - issue_type: str
            - explanation: str
            - suggestion: str
        output_path: Where to save the annotated .docx.

    Returns:
        The output_path on success.

    Raises:
        ValueError: If the source file is not found or unreadable.
        IOError: If writing the output file fails.
    """
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"Source file not found: {file_path}")

    try:
        doc = Document(str(path))
    except Exception as e:
        raise ValueError(f"Could not open document: {e}") from e

    # If no issues, save original copy unchanged
    if not issues:
        doc.save(output_path)
        logger.info("No issues to annotate. Saved copy to %s", output_path)
        return output_path

    # Add a comment for each issue
    for comment_id, issue in enumerate(issues):
        para_idx = issue.get("paragraph_index", 0)
        issue_type = issue.get("issue_type", "unknown")
        explanation = issue.get("explanation", "")
        suggestion = issue.get("suggestion", "")

        comment_text = f"[{issue_type.upper()}] {explanation}"
        if suggestion:
            comment_text += f" → Suggestion: {suggestion}"

        try:
            _add_comment_to_paragraph(doc, para_idx, comment_text, comment_id)
        except Exception as e:
            logger.warning("Failed to add comment %d (para %d): %s", comment_id, para_idx, e)

    try:
        doc.save(output_path)
        logger.info("Saved annotated document to %s with %d comment(s)", output_path, len(issues))
    except Exception as e:
        raise IOError(f"Failed to save annotated document: {e}") from e

    return output_path
