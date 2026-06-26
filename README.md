# Project Builder – AI Coding Assistant

**Project Builder – AI Coding Assistant** is an AI-powered coding assistant built with [LangGraph](https://github.com/langchain-ai/langgraph) and [Azure OpenAI](https://learn.microsoft.com/azure/ai-services/openai/).

It works like a small multi-agent development team: you describe the app you want in plain English, and the assistant plans it, breaks it into engineering tasks, and writes the code file by file into a fresh project folder.

---

## How It Works

The app is a three-stage [LangGraph](https://github.com/langchain-ai/langgraph) state machine. Each stage is an agent backed by the same Azure OpenAI model:

```text
   user prompt
        │
        ▼
┌──────────────┐     ┌────────────────┐     ┌──────────────┐
│   Planner    │ ──▶ │   Architect    │ ──▶ │    Coder     │ ──▶ DONE
│  build Plan  │     │ build TaskPlan │     │ write files  │ ◀─┐
└──────────────┘     └────────────────┘     └──────────────┘   │
                                                   └───────────┘
                                              (loops until every
                                               task is implemented)
```

- **Planner Agent** – Converts your request into a structured `Plan` (app name, description, tech stack, features, and the list of files to create).
- **Architect Agent** – Expands the plan into an ordered list of explicit, self-contained engineering tasks (`TaskPlan`), with dependencies sequenced first.
- **Coder Agent** – Works through the tasks one at a time. It is a tool-using ReAct agent that reads existing files and writes new ones using sandboxed file tools, until every task is complete.

All generated code is written to a **new, timestamped folder per run** — see [Output](#-output) below.

---

## Project Structure

```text
.
├── main.py             # CLI entry point: prompts the user and runs the agent graph
├── agent/
│   ├── graph.py        # LangGraph wiring + the planner/architect/coder agent nodes
│   ├── states.py       # Pydantic models (Plan, TaskPlan, CoderState, ...)
│   ├── prompts.py      # Prompt templates for each agent
│   └── tools.py        # Sandboxed file tools (read/write/list) for the coder agent
├── pyproject.toml      # Project metadata and dependencies
├── uv.lock             # Locked, reproducible dependency versions
└── .sample_env         # Template for the required environment variables
```

---

## Getting Started

### Prerequisites

- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** — used to manage the virtual environment and dependencies.
- **Python 3.11+** (uv will install it automatically if needed).
- An **Azure AI Foundry / Azure OpenAI** resource with a **deployed chat model** (e.g. `gpt-4o-mini`). From the portal, copy your:
  - resource **endpoint** (e.g. `https://<your-resource>.services.ai.azure.com`)
  - **API key**
  - **deployment name**

### Installation

1. Create the virtual environment and install dependencies from the lockfile:

   ```bash
   uv venv
   uv sync
   ```

   > `uv sync` installs the exact, tested versions from `uv.lock`. Avoid `uv pip install -r pyproject.toml`, which may resolve to incompatible newer releases.

2. Create a `.env` file (copy `.sample_env`) and fill in your Azure values:

   ```env
   AZURE_OPENAI_ENDPOINT=https://<your-resource>.services.ai.azure.com
   AZURE_OPENAI_API_KEY=<your-api-key>
   AZURE_OPENAI_DEPLOYMENT=<your-deployment-name>
   AZURE_OPENAI_MODEL=<your-model-name>
   AZURE_OPENAI_API_VERSION=2024-10-21
   ```

   | Variable | Description |
   | --- | --- |
   | `AZURE_OPENAI_ENDPOINT` | Base resource URL only — no `/openai/...` path or operation suffix. |
   | `AZURE_OPENAI_API_KEY` | API key for the resource. |
   | `AZURE_OPENAI_DEPLOYMENT` | The **deployment name** as shown in the portal (may differ from the model name). |
   | `AZURE_OPENAI_MODEL` | Underlying model name (used as metadata). |
   | `AZURE_OPENAI_API_VERSION` | API version; `2024-10-21` is a safe GA default. |

### Running

```bash
uv run python main.py
```

You'll be prompted:

```text
Enter your project prompt:
```

Type a description of what you want to build. When the run finishes, the path to the generated project is printed.

Optional — raise the step limit for larger projects:

```bash
uv run python main.py --recursion-limit 200
```

---

## Output

Each run creates a **new folder** so previous projects are never overwritten:

```text
generated_projects/
└── project_YYYYMMDD_HHMMSS/
    ├── index.html
    ├── style.css
    └── script.js
```

The coder agent is sandboxed to this folder and cannot write outside it. The exact path is printed at the end of each run.

---

## Example Prompts

- Create a to-do list application using HTML, CSS, and JavaScript.
- Create a simple calculator web application.
- Create a simple blog API in FastAPI with a SQLite database.

---

## Tech Stack

- **[LangGraph](https://github.com/langchain-ai/langgraph)** — multi-agent orchestration / state machine
- **[LangChain](https://github.com/langchain-ai/langchain)** + **langchain-openai** — LLM integration and structured output
- **[Azure OpenAI](https://learn.microsoft.com/azure/ai-services/openai/)** — the underlying chat model
- **[Pydantic](https://docs.pydantic.dev/)** — structured data models for the agents
- **[uv](https://docs.astral.sh/uv/)** — environment and dependency management

---
