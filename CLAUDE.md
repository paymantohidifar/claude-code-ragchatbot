# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A full-stack RAG (Retrieval-Augmented Generation) chatbot for querying course materials. It uses ChromaDB for vector storage, `sentence-transformers` for local embeddings, and Anthropic's Claude for answer generation via tool-calling.

## Dependency Management

Always use `uv` — never `pip` or `pip install` directly. To add a package:

```bash
uv add <package>
```

## Setup

```bash
# Install dependencies
uv sync

# Create .env from example
cp .env.example .env
# Then add your ANTHROPIC_API_KEY to .env
```

## Running the App

```bash
# Quick start (from repo root)
./run.sh

# Or manually
cd backend && uv run uvicorn app:app --reload --port 8000
```

- Web UI: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

The server auto-loads all `.txt`, `.pdf`, and `.docx` files from `../docs` (relative to `backend/`) on startup.

## Architecture

The app is structured as a FastAPI backend serving a vanilla JS frontend from `frontend/`.

**Request flow for a chat query:**

1. `app.py` receives `POST /api/query` → calls `RAGSystem.query()`
2. `RAGSystem` (orchestrator in `rag_system.py`) builds a prompt and calls `AIGenerator.generate_response()`
3. `AIGenerator` (`ai_generator.py`) sends the query to Claude with the `search_course_content` tool definition
4. If Claude decides to search, it returns `stop_reason="tool_use"` → `AIGenerator._handle_tool_execution()` calls `ToolManager.execute_tool()`
5. `ToolManager` delegates to `CourseSearchTool.execute()` (`search_tools.py`), which calls `VectorStore.search()`
6. `VectorStore` (`vector_store.py`) optionally resolves the course name via semantic search on `course_catalog`, then queries `course_content` with optional filters
7. Results are formatted and returned to Claude for the final answer
8. Sources (course + lesson metadata) are tracked on `CourseSearchTool.last_sources` and returned to the caller

**ChromaDB collections** (persisted at `backend/chroma_db/`):
- `course_catalog` — one doc per course (title, instructor, course link, lessons JSON)
- `course_content` — chunked lesson text with `course_title` and `lesson_number` metadata for filtering

**Document format** (`docs/*.txt`):
```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 0: <title>
Lesson Link: <url>
<lesson content...>

Lesson 1: <title>
...
```
`DocumentProcessor` (`document_processor.py`) parses this format and chunks lesson text using sentence-aware splitting with configurable `CHUNK_SIZE` (800) and `CHUNK_OVERLAP` (100).

**Sessions** are in-memory only (lost on server restart). `SessionManager` stores the last `MAX_HISTORY=2` exchanges per session as formatted strings injected into the system prompt.

## Key Configuration (`backend/config.py`)

| Setting | Default | Purpose |
|---|---|---|
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Model used for generation |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Local sentence-transformer model |
| `CHUNK_SIZE` | 800 | Characters per vector chunk |
| `MAX_RESULTS` | 5 | Max chunks returned per search |
| `MAX_HISTORY` | 2 | Conversation turns remembered |
| `CHROMA_PATH` | `./chroma_db` | ChromaDB persistence path (relative to `backend/`) |

## Adding a New Tool

1. Subclass `Tool` in `search_tools.py` and implement `get_tool_definition()` and `execute()`
2. Register it in `RAGSystem.__init__()` via `self.tool_manager.register_tool(your_tool)`
3. The tool definitions are automatically passed to Claude on every query

## Rebuilding the Vector Store

To clear ChromaDB and re-ingest all docs:
```python
rag_system.add_course_folder("../docs", clear_existing=True)
```
Or delete `backend/chroma_db/` and restart the server.
