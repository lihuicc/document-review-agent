# Specification: word-document-review-agent

> **Guidelines**: Read [guidelines.md](../guidelines.md) and [guidelines-agent.md](../guidelines-agent.md) before executing ANY tasks below. Follow all constraints described there throughout execution.

## Basic Setup

- [x] Read `product-requirements-document.md` and `intent.md` for full context
- [x] Bootstrap agent code in `assets/word-document-review-agent/` using skill `sap-agent-bootstrap` (invoke from inside `assets/word-document-review-agent/`, use copy commands — do NOT create files manually)
- [x] Install dependencies, validate the agent starts and responds at `/.well-known/agent.json`

## Dependencies

- [x] Add the following to `requirements.txt`:
  - `python-docx` — read and write .docx files, insert comments and tracked changes
  - `lxml` — XML manipulation required by python-docx for comment injection
  - `litellm` — LLM calls via SAP AI Core Generative AI Hub
- [x] Run `pip install -r requirements.txt` and confirm no errors

## Document Parsing Tool

- [x] Create `app/tools/document_parser.py` implementing a tool `parse_document(file_path: str) -> dict`:
  - Accepts a path to a .docx file
  - Extracts all paragraphs with their index, text, and run-level detail
  - Returns a structured dict: `{ "paragraphs": [{ "index": int, "text": str, "runs": [...] }] }`
  - Raises `ValueError` with a clear message if the file is not a valid .docx
  - Log: `M2.achieved: document content extracted successfully` on success
  - Log: `M2.missed: content extraction failed or returned empty` on error

## Document Annotation Tool

- [x] Create `app/tools/document_annotator.py` implementing a tool `annotate_document(file_path: str, issues: list, output_path: str) -> str`:
  - Accepts the original .docx path, a list of issues (each with `paragraph_index`, `original_text`, `issue_type`, `explanation`, `suggestion`), and an output path
  - For each issue: insert a Word comment at the correct paragraph using python-docx XML comment injection
  - Comment text format: `[{issue_type}] {explanation} → Suggestion: {suggestion}`
  - Preserves the original document content — only adds comments, never deletes or replaces text
  - Returns the output file path on success
  - Log: `M4.achieved: annotations written to document successfully` on success
  - Log: `M4.missed: annotation writing failed for one or more issues` on any error

## Agent Core Logic

- [x] Implement the agent system prompt in `app/agent.py` `@prompt_section`
- [x] Implement `_run_agent(file_path: str) -> str` as a plain async method with all 5 milestone log pairs
- [x] Implement `stream()` as an async generator that calls `_run_agent()` and yields the result
- [x] Wrap each milestone step in `_run_agent()` with OpenTelemetry spans

## File Handling

- [x] The agent accepts the input .docx file path from the user query
- [x] Output annotated file written to `output/<original-filename>-reviewed.docx`
- [x] Ensure the `output/` directory is created if it does not exist before writing
- [x] If the LLM returns a malformed or empty JSON response, the agent returns the original document unchanged with an error comment

## Instrumentation

- [x] Verify `auto_instrument()` is called at the top of `main.py` before any AI framework imports
- [x] Confirm all five milestone log statements are present in `_run_agent()`:
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

- [x] Delete the template runtime skill (no template-skill directory was present)
- [x] Verify `app/agent.py` has exactly 3 decorated functions: `@agent_model`, `@agent_config`, `@prompt_section`

## Testing

- [x] Set up `conftest.py` with `IBD_TESTING=1` and session-scoped fixtures
- [x] Write `tests/test_document_parser.py` — 6 unit tests for `parse_document()` — all passing
- [x] Write `tests/test_document_annotator.py` — 6 unit tests for `annotate_document()` — all passing
- [x] Write `tests/test_document_annotator_extended.py` — 7 additional annotator tests — all passing
- [x] Write `tests/test_agent_integration.py` — 5 end-to-end integration tests with mocked LLM — all passing
- [x] Write `tests/test_agent_executor.py` — 5 unit tests for AgentExecutor — all passing
- [x] Write `tests/test_mcp_tools.py` — 7 unit tests for mcp_tools.py IBD_TESTING mode — all passing
- [x] Write `tests/test_load_skill_resources.py` — 8 unit tests for load_skill_resources.py — all passing
- [x] Write `tests/test_util.py` — 7 unit tests for util.py — all passing
- [x] Run full test suite: 66 passed, 2 skipped (server tests — require production credentials), 0 failed
- [x] Coverage ≥ 70%: achieved 70% overall
- [x] `test_report.json` generated at `assets/word-document-review-agent/test_report.json`
- [x] Verify `test_report.json` exists: confirmed present
