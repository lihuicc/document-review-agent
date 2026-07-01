# Specification: word-document-review-agent

> **Guidelines**: Read [guidelines.md](../guidelines.md) and [guidelines-agent.md](../guidelines-agent.md) before executing ANY tasks below. Follow all constraints described there throughout execution.

## Basic Setup

- [ ] Read `product-requirements-document.md` and `intent.md` for full context
- [ ] Bootstrap agent code in `assets/word-document-review-agent/` using skill `sap-agent-bootstrap` (invoke from inside `assets/word-document-review-agent/`, use copy commands — do NOT create files manually)
- [ ] Install dependencies, validate the agent starts and responds at `/.well-known/agent.json`

## Dependencies

- [ ] Add the following to `requirements.txt`:
  - `python-docx` — read and write .docx files, insert comments and tracked changes
  - `lxml` — XML manipulation required by python-docx for comment injection
  - `litellm` — LLM calls via SAP AI Core Generative AI Hub
- [ ] Run `pip install -r requirements.txt` and confirm no errors

## Document Parsing Tool

- [ ] Create `app/tools/document_parser.py` implementing a tool `parse_document(file_path: str) -> dict`:
  - Accepts a path to a .docx file
  - Extracts all paragraphs with their index, text, and run-level detail
  - Returns a structured dict: `{ "paragraphs": [{ "index": int, "text": str, "runs": [...] }] }`
  - Raises `ValueError` with a clear message if the file is not a valid .docx
  - Log: `M2.achieved: document content extracted successfully` on success
  - Log: `M2.missed: content extraction failed or returned empty` on error

## Document Annotation Tool

- [ ] Create `app/tools/document_annotator.py` implementing a tool `annotate_document(file_path: str, issues: list, output_path: str) -> str`:
  - Accepts the original .docx path, a list of issues (each with `paragraph_index`, `original_text`, `issue_type`, `explanation`, `suggestion`), and an output path
  - For each issue: insert a Word comment at the correct paragraph using python-docx XML comment injection
  - Comment text format: `[{issue_type}] {explanation} → Suggestion: {suggestion}`
  - Preserves the original document content — only adds comments, never deletes or replaces text
  - Returns the output file path on success
  - Log: `M4.achieved: annotations written to document successfully` on success
  - Log: `M4.missed: annotation writing failed for one or more issues` on any error

## Agent Core Logic

- [ ] Implement the agent system prompt in `app/agent.py` `@prompt_section`:
  ```
  You are a professional document review assistant. When given document text, you analyze it for:
  1. Spelling and typographical errors
  2. Grammar and punctuation issues
  3. Inconsistencies in language usage (tense, voice, terminology)
  4. Logical or common-sense inaccuracies
  5. Clarity, readability, and potential ambiguities

  For each issue found, return a JSON array with objects containing:
  - paragraph_index: int (0-based index of the affected paragraph)
  - original_text: str (the problematic phrase or sentence)
  - issue_type: str (one of: spelling, grammar, punctuation, consistency, logic, clarity)
  - explanation: str (clear explanation of the problem)
  - suggestion: str (specific recommended correction or improvement)

  If no issues are found in a paragraph, do not include it. Be thorough but precise.
  Never hallucinate issues that do not exist. Return only valid JSON.
  ```
- [ ] Implement `_run_agent(file_path: str) -> str` as a plain async method (NOT a generator) that:
  1. Validates the file exists and is a .docx — log `M1.achieved` / `M1.missed`
  2. Calls `parse_document()` to extract text — log `M2.achieved` / `M2.missed`
  3. Sends full document text to LLM for analysis — log `M3.achieved` / `M3.missed`
  4. Parses LLM JSON response into issue list
  5. Calls `annotate_document()` to write inline comments — log `M4.achieved` / `M4.missed`
  6. Returns the annotated file path — log `M5.achieved` / `M5.missed`
- [ ] Implement `stream()` as an async generator that calls `_run_agent()` and yields the result — no business logic inside `stream()` itself
- [ ] Wrap each milestone step in `_run_agent()` with OpenTelemetry spans using `@tracer.start_as_current_span` (decorator form on helper methods) or `with tracer.start_as_current_span(...)` inside non-generator functions only

## File Handling

- [ ] The agent accepts the input .docx file path from the user query (the user provides a local path or the file is placed in a known input directory)
- [ ] Output annotated file written to `output/<original-filename>-reviewed.docx`
- [ ] Ensure the `output/` directory is created if it does not exist before writing
- [ ] If the LLM returns a malformed or empty JSON response, the agent returns the original document unchanged and appends a single comment at the first paragraph: `[REVIEW ERROR] The AI review could not be completed. Please try again.`

## Instrumentation

- [ ] Verify `auto_instrument()` is called at the top of `main.py` before any AI framework imports
- [ ] Confirm all five milestone log statements are present in `_run_agent()`:
  - `M1.achieved: document received and validated successfully`
  - `M1.missed: document could not be received or validated`
  - `M2.achieved: document content extracted successfully`
  - `M2.missed: content extraction failed or returned empty`
  - `M3.achieved: content analysis complete, issues identified`
  - `M3.missed: LLM analysis failed or returned unstructured response`
  - `M4.achieved: annotations written to document successfully`
  - `M4.missed: annotation writing failed for one or more issues`
  - `M5.achieved: annotated document returned to user`
  - `M5.missed: document delivery failed`

## Cleanup

- [ ] Delete the template runtime skill: `rm -rf assets/word-document-review-agent/app/skills/template-skill/`
- [ ] Verify `app/agent.py` has exactly 3 decorated functions: run `grep -c "^@agent_model\|^@agent_config\|^@prompt_section" assets/word-document-review-agent/app/agent.py` and confirm output is `3`

## Testing

- [ ] Set up `conftest.py` with only `IBD_TESTING=true` and mock LLM patch returning a sample issues JSON array
- [ ] Write `tests/test_document_parser.py` — unit test for `parse_document()`:
  - Creates a temp .docx with known paragraphs, calls `parse_document()`, asserts correct paragraph count and text
  - Run immediately after writing: `pytest tests/test_document_parser.py`
- [ ] Write `tests/test_document_annotator.py` — unit test for `annotate_document()`:
  - Creates a temp .docx, calls `annotate_document()` with mock issues, verifies output file exists and has XML comment nodes
  - Run immediately after writing: `pytest tests/test_document_annotator.py`
- [ ] Write `tests/test_agent_integration.py` — one end-to-end test:
  - Places a sample .docx in `tests/fixtures/`, invokes the agent's `invoke` function with a file path query
  - Asserts a reviewed .docx is returned and contains at least one Word comment
  - LLM mocked to return a known issue list
  - Run immediately after writing: `pytest tests/test_agent_integration.py`
- [ ] Run full test suite: `pytest` (no args) from `assets/word-document-review-agent/`
- [ ] If coverage < 70%, add targeted tests until threshold met
- [ ] Run `pytest` again (no args) to generate final `test_report.json`
- [ ] Verify `test_report.json` exists: `ls assets/word-document-review-agent/test_report.json`
