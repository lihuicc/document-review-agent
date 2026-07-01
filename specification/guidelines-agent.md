# Agent Guidelines

Technical constraints and patterns for building Pro-Code AI Agents. Follow these throughout specification execution.

## Tech Stack

- Python 3.13
- Agent framework defined in the `sap-agent-bootstrap` skill
- Agent2Agent (A2A) protocol
- Local execution only (in-memory storage, no deployment)

## Project Structure

- Asset root: `assets/<asset-name>/`
- Required structure: `asset.yaml`, `app/`
- Full layout from project root: `solution.yaml`, `assets/<asset-name>/asset.yaml`, `assets/<asset-name>/app/`
- `asset.yaml` must use `buildPath: .` and `/.well-known/agent.json` for all health probes
- Follow the `sap-agent-bootstrap` skill for project scaffolding — invoke directly from `assets/<asset-name>/`, use copy commands

## Key Constraints

- When working with LangChain or LangGraph, you MUST NEVER use the `create_react_agent` function (`from langgraph.prebuilt import create_react_agent`) as it has been deprecated in LangChain 1.0. Instead, you should use the `from langchain.agents import create_agent` function.
- **NEVER call SAP APIs directly** (no `requests`, `httpx`, or hand-rolled OData clients). All SAP API consumption MUST go through MCP servers.
- Only use public APIs; mock any private systems with minimal mock data
- AI Core is available at **runtime** via LiteLLM but is **NOT available during tests** — all LLM calls must be mocked
- No Git operations, no authentication, no documentation/READMEs
- Update `requirements.txt` for any new dependencies
- Never modify `sys.path`
- No `.env` files (environment variables supplied at runtime)

## Code Quality

- All Python code must compile with valid imports
- No `src.` import patterns
- All function parameters must be used in function body

## Agent Decorators

- The bootstrap template already includes decorator scaffolding
- **NEVER add new decorated functions to `app/agent.py`** — the three from the bootstrap template (`@agent_model`, `@agent_config` for temperature, `@prompt_section`) are the complete and final set
- Never mark decorator tasks complete until `sap_cloud_sdk.agent_decorators` imports exist in `app/agent.py`

## Agent Instrumentation

- ALL business logic steps MUST be instrumented with proper logging and OpenTelemetry spans
- Log pattern: `[MILESTONE_ID].[achieved|missed]: [description]`
- **NEVER use `with tracer.start_as_current_span(...)` inside an async generator** — extract logic into a plain async helper instead
- Ensure `auto_instrument()` is called at top of `main.py` before any AI framework imports

## MCP Tool Integration

- All SAP API integrations MUST use MCP tool pattern via `get_mcp_tools()`
- **Never hard-code tool names in code** — retrieve dynamically
- System prompt MUST instruct the agent to set `top` to a maximum of 100 on every tool call

## Testing

- Working directory: `assets/<asset-name>/`
- All generated tests go in `assets/<asset-name>/tests/`
- AI Core / LLM calls MUST be mocked in all tests
- ALWAYS invoke as just `pytest` from asset root — no extra flags
- Coverage must be ≥ 70%
- Final `pytest` run (no args) MUST produce `test_report.json`

## Validation Checklist

```bash
grep -r "M[0-9]\.achieved" assets/<asset-name>/app/
grep -r "sap_cloud_sdk.agent_decorators" assets/<asset-name>/app/
grep -c "^@agent_model\|^@agent_config\|^@prompt_section" assets/<asset-name>/app/agent.py
ls assets/<asset-name>/test_report.json
```
