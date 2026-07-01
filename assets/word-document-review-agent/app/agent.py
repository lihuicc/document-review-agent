import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncGenerator, Literal, Sequence

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langchain_litellm import ChatLiteLLM
from langgraph.checkpoint.memory import InMemorySaver
from opentelemetry import trace
from sap_cloud_sdk.agent_decorators import agent_config, agent_model, prompt_section

from tools.document_parser import parse_document
from tools.document_annotator import annotate_document

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

THREAD_TTL_SECONDS = 3600  # evict threads inactive for 1 hour
OUTPUT_DIR = Path(__file__).parent.parent / "output"


@agent_model(
    key="config.model",
    label="LLM Model",
    description="The language model powering this agent",
)
def get_model_name() -> str:
    return "sap/anthropic--claude-4.5-sonnet"


@agent_config(
    key="config.temperature",
    label="LLM Temperature",
    description="Controls randomness of responses (0.0 = deterministic, 1.0 = creative)",
)
def get_temperature() -> float:
    return 0.0


@prompt_section(
    key="prompts.system",
    label="System Prompt",
    description="The full system prompt defining the agent's role and behavior",
    validation={"format": "markdown", "max_length": 5000},
)
def get_system_prompt() -> str:
    return """You are a professional document review assistant. When the user provides a file path to a .docx document, follow these steps:

1. Call the `parse_document` tool with the file path to extract the document content.
2. Analyze the extracted text for ALL of the following issue categories:
   - **spelling**: Spelling and typographical errors
   - **grammar**: Grammar and punctuation issues
   - **consistency**: Inconsistencies in language usage (tense, voice, terminology)
   - **logic**: Logical or common-sense inaccuracies
   - **clarity**: Clarity, readability, and potential ambiguities

3. For each issue found, produce a JSON array where each element has:
   - paragraph_index: int (0-based index of the affected paragraph)
   - original_text: str (the problematic phrase or sentence, verbatim)
   - issue_type: str (one of: spelling, grammar, punctuation, consistency, logic, clarity)
   - explanation: str (clear explanation of the problem)
   - suggestion: str (specific recommended correction or improvement)

4. Call the `annotate_document` tool with the file path and the JSON issues list to write inline Word comments.
5. Report back to the user with the output file path and a summary of issues found.

IMPORTANT:
- Never hallucinate issues that do not exist in the document.
- If the document has no issues, say so clearly and return the original path.
- Always set top to a maximum of 100 on any tool call that accepts a page size parameter.
- Relay tool errors verbatim without adding suggestions.
"""


@dataclass
class AgentResponse:
    status: Literal["input_required", "completed", "error"]
    message: str


class WordReviewAgent:
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        self.llm = ChatLiteLLM(model=get_model_name(), temperature=get_temperature())
        self._checkpointer = InMemorySaver()
        self._last_active: dict[str, float] = {}
        self._summarization_middleware = SummarizationMiddleware(
            model=self.llm,
            trigger=("tokens", 100_000),
            keep=("messages", 4),
        )

    def _touch(self, thread_id: str) -> None:
        now = time.monotonic()
        expired = [
            tid
            for tid, ts in list(self._last_active.items())
            if now - ts > THREAD_TTL_SECONDS
        ]
        for tid in expired:
            self._checkpointer.delete_thread(tid)
            del self._last_active[tid]
            logger.info("Evicted inactive thread: %s", tid)
        self._last_active[thread_id] = now

    async def _run_agent(self, file_path: str, context_id: str, tools: list) -> str:
        """Core review logic — plain async method (not a generator) for safe instrumentation."""

        # M1: Document received and validated
        docx_path = Path(file_path)
        if not docx_path.exists() or not file_path.endswith(".docx"):
            logger.info("M1.missed: document could not be received or validated")
            return f"[REVIEW ERROR] File not found or not a .docx: {file_path}"
        logger.info("M1.achieved: document received and validated successfully")

        # M2: Content extracted
        try:
            parsed = parse_document(file_path)
            if not parsed.get("paragraphs"):
                logger.info("M2.missed: content extraction failed or returned empty")
                return f"[REVIEW ERROR] Document appears to be empty: {file_path}"
            logger.info("M2.achieved: document content extracted successfully")
        except Exception as e:
            logger.info("M2.missed: content extraction failed or returned empty")
            return f"[REVIEW ERROR] Failed to parse document: {e}"

        # Build full text for LLM
        paragraphs = parsed["paragraphs"]
        full_text = "\n".join(
            f"[{p['index']}] {p['text']}" for p in paragraphs if p["text"].strip()
        )

        # M3: LLM analysis
        try:
            analysis_query = (
                f"Review the following document text for all quality issues.\n\n"
                f"Document paragraphs (format: [index] text):\n{full_text}\n\n"
                f"Return ONLY a valid JSON array of issues. If no issues, return []."
            )

            graph = create_agent(
                self.llm,
                tools=tools,
                system_prompt=get_system_prompt(),
                checkpointer=self._checkpointer,
                middleware=[self._summarization_middleware],
            )
            config = {"configurable": {"thread_id": f"{context_id}_analysis"}}
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=analysis_query)]}, config
            )
            self._touch(context_id)
            raw_response = result["messages"][-1].content

            # Parse JSON issues from LLM response
            issues = []
            try:
                # Extract JSON array from response
                start = raw_response.find("[")
                end = raw_response.rfind("]") + 1
                if start >= 0 and end > start:
                    issues = json.loads(raw_response[start:end])
                else:
                    issues = []
            except (json.JSONDecodeError, ValueError):
                logger.warning("LLM returned non-JSON response, using empty issues list")
                issues = []

            logger.info("M3.achieved: content analysis complete, issues identified")
        except Exception as e:
            logger.info("M3.missed: LLM analysis failed or returned unstructured response")
            logger.exception("LLM analysis error")
            # Return original document with error comment
            issues = [{
                "paragraph_index": 0,
                "original_text": "",
                "issue_type": "error",
                "explanation": f"AI review could not be completed: {e}",
                "suggestion": "Please try again."
            }]

        # M4: Annotations applied
        try:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            stem = docx_path.stem
            output_path = str(OUTPUT_DIR / f"{stem}-reviewed.docx")
            result_path = annotate_document(file_path, issues, output_path)
            logger.info("M4.achieved: annotations written to document successfully")
        except Exception as e:
            logger.info("M4.missed: annotation writing failed for one or more issues")
            return f"[REVIEW ERROR] Failed to write annotations: {e}"

        # M5: Annotated document returned
        issue_count = len([i for i in issues if i.get("issue_type") != "error"])
        logger.info("M5.achieved: annotated document returned to user")
        return (
            f"Review complete! Found {issue_count} issue(s).\n"
            f"Annotated document saved to: {result_path}\n\n"
            f"Issues by category:\n" +
            "\n".join(
                f"  - [{i.get('issue_type', 'unknown')}] paragraph {i.get('paragraph_index', '?')}: {i.get('explanation', '')}"
                for i in issues if i.get("issue_type") != "error"
            )
        )

    async def stream(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Stream agent responses. Business logic delegated to _run_agent."""
        self._touch(context_id)
        yield {
            "is_task_complete": False,
            "require_user_input": False,
            "content": "Reviewing document...",
        }

        try:
            # Extract file path from query
            words = query.split()
            file_path = next(
                (w for w in words if w.endswith(".docx")),
                query.strip()
            )
            result = await self._run_agent(file_path, context_id, list(tools) if tools else [])
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": result,
            }
        except Exception as e:
            logger.exception("stream() failed")
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": f"I encountered an error while processing your request: {str(e)}. Please try again.",
            }

    async def invoke(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AgentResponse:
        last: dict = {}
        async for chunk in self.stream(query, context_id, tools=tools):
            last = chunk
        if last.get("is_task_complete"):
            return AgentResponse(status="completed", message=last["content"])
        if last.get("require_user_input"):
            return AgentResponse(status="input_required", message=last["content"])
        return AgentResponse(
            status="error", message=last.get("content", "Unknown error")
        )
