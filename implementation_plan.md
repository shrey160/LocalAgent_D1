# Dharampal AI Agent - Implementation Plan

## Overview

Dharampal is a modular desktop AI agent for Windows that combines a local LLM (via LM Studio) with web scraping capabilities and a RAG-based memory system. The agent features a native chat interface, multiple news sources, and intelligent tool routing.

## System Architecture

### High-Level Architecture

```
User Input (Chat UI / CLI)
    |
    v
+---------------------+
|   LangGraph Agent   |  <-- Conversation state management
|   (dharampal/agent) |
+---------------------+
    |
    +---> Tool Router (LLM decides which tool to use)
    |         |
    |         +---> Space News Tool (cached in ChromaDB)
    |         +---> Trading News Tool (live, no cache)
    |         +---> Historical Search (ChromaDB RAG)
    |         +---> List Sources (info tool)
    |         +---> Web Scraper (fallback for historical)
    |
    +---> LLM Backend (LM Studio)
    |         |
    |         +---> google/gemma-4-e4b via OpenAI-compatible API
    |
    +---> Response Generation
    |
    v
User Output (Chat UI)
```

### Component Architecture

#### 1. CLI Controller (`dharampal/cli.py`)
- **Purpose**: Lifecycle management (start/stop)
- **Commands**:
  - `dharampal start`: Launch LM Studio server, load model, spawn UI
  - `dharampal stop`: Terminate UI, unload model, stop server
- **Process Management**:
  - UI runs in detached process (pythonw.exe)
  - State file (`%TEMP%\dharampal.state`) tracks PIDs
  - Log file (`%TEMP%\dharampal_ui.log`) captures UI output

#### 2. Chat Interface (`dharampal/ui/chat_window.py`)
- **Framework**: customtkinter
- **Features**:
  - Three-row layout: chat history, input field, status bar
  - Input disabled until model is reachable
  - Auto-polls LM Studio every 2s (up to 10 min)
  - Background threading for non-blocking responses
  - Thread-safe UI updates via `after(0, ...)`

#### 3. Agent Graph (`dharampal/agent/graph.py`)
- **Framework**: LangGraph
- **State**: `messages` list with `add_messages` reducer
- **Nodes**:
  - `chatbot`: LLM invocation with tool binding
  - `tools`: Tool execution node
- **Edges**:
  - `START -> chatbot`
  - `chatbot -> tools` (conditional, if tool calls detected)
  - `tools -> chatbot`
  - `chatbot -> END` (if no tool calls)
- **Memory**: `MemorySaver` checkpoint for conversation persistence

#### 4. Tool System (`dharampal/tools/`)

**Registry Pattern** (`dharampal/tools/__init__.py`):
- All tools auto-discovered via `ALL_TOOLS` list
- Adding a new tool = import + append to list

**Available Tools**:

| Tool | File | Source | Cached? | Use Case |
|------|------|--------|---------|----------|
| `space_news_tool` | `space_news.py` | SpaceNews archive | Yes (ChromaDB) | "Daily news" - fetches yesterday + day before yesterday |
| `trading_news_tool` | `trading_news.py` | TradingEconomics | No (live only) | "Trading news" - live financial headlines |
| `search_historical_news` | `news_search.py` | ChromaDB | N/A | "News for April 21st" - searches local RAG |
| `scrape_historical_news` | `news_scraper.py` | SpaceNews | Yes (stores after scrape) | Fallback when user wants to check online |
| `list_sources_tool` | `list_sources.py` | Info | N/A | "Show sources" - lists sources and cache status |

**Tool Implementation Details**:
- All tools use `@tool` decorator from LangChain
- SpaceNews scraper uses `curl` via subprocess (avoids Python request blocking)
- TradingEconomics scraper uses `requests` (no caching)
- Date parsing via `dateparser` library (handles "April 21st", "yesterday", etc.)

#### 5. Storage Layer (`dharampal/storage/`)

**ChromaDB Store** (`chroma_store.py`):
- **Location**: `data/chroma_db/` (persistent, gitignored)
- **Collection**: `space_news`
- **Schema**:
  - `id`: Article URL (natural unique key)
  - `document`: Combined title + date + excerpt (for embedding)
  - `metadata`: title, date, url, excerpt
  - `embedding`: Vector from Ollama `nomic-embed-text`
- **Search Modes**:
  - `search_by_date()`: Exact date match via metadata filter
  - `search_by_query()`: Semantic similarity search

**Embedding Client** (`dharampal/embeddings.py`):
- **Provider**: Ollama (local)
- **Model**: `nomic-embed-text:latest`
- **Endpoint**: `http://localhost:11434/api/embeddings`
- **Features**: In-memory caching, batch support

### Data Flow Diagrams

#### Daily News Flow
```
User: "Get daily news"
    |
    v
chatbot node (LLM detects intent)
    |
    v
space_news_tool.invoke()
    |
    +---> curl fetch SpaceNews archive
    +---> parse HTML for yesterday + day before
    +---> store articles in ChromaDB
    +---> format and return
    |
    v
chatbot node (formats response)
    |
    v
User sees formatted article list
```

#### Historical News Flow
```
User: "News for April 21st"
    |
    v
chatbot node (LLM detects historical intent)
    |
    v
search_historical_news.invoke("April 21st")
    |
    +---> dateparser extracts date
    +---> ChromaDB.search_by_date()
    |
    +---> [Found] Return articles + "Want more from web?"
    +---> [Not Found] "No cached articles. Check SpaceNews?"
    |
    v
User: "yes"
    |
    v
scrape_historical_news.invoke("April 21st")
    |
    +---> curl fetch SpaceNews archive
    +---> parse for specific date
    +---> store in ChromaDB
    +---> return results
    |
    v
chatbot node (formats response)
    |
    v
User sees web results (now cached for future)
```

#### Trading News Flow
```
User: "Get trading news"
    |
    v
chatbot node (LLM detects trading intent)
    |
    v
trading_news_tool.invoke()
    |
    +---> requests fetch TradingEconomics
    +---> parse headline section
    +---> format and return (NO storage)
    |
    v
chatbot node (formats response)
    |
    v
User sees live trading headlines
```

### Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| LLM Backend | LM Studio | Latest | Local model serving (OpenAI-compatible API) |
| Model | google/gemma-4-e4b | - | Primary LLM (via LM Studio) |
| Embeddings | Ollama + nomic-embed-text | Latest | Vector embeddings for RAG |
| Agent Framework | LangGraph + LangChain | Latest | Conversation state + tool routing |
| LLM Client | langchain-openai | Latest | OpenAI-compatible client for LM Studio |
| UI | customtkinter | Latest | Native desktop chat window |
| Vector DB | ChromaDB | Latest | Persistent article storage |
| Scraping | BeautifulSoup4 + curl | Latest | HTML parsing (curl avoids rate limits) |
| Date Parsing | dateparser | Latest | Natural language date extraction |
| Build | setuptools | Latest | Package installation |

### File Structure

```
dharampal_1/
├── dharampal.bat              # Windows launcher (PATH entry point)
├── setup.py                   # Package setup + dependencies
├── implementation_plan.md     # This document
├── README.md                  # User-facing documentation
├── .gitignore                 # Excludes: venv/, data/, notebook/
├── notebook/                  # Jupyter notebooks for testing (gitignored)
│   └── test_tools.ipynb       # Tool testing & debugging
├── data/                      # ChromaDB storage (gitignored)
│   └── chroma_db/             # Persistent vector database
├── venv/                      # Python virtual environment (gitignored)
└── dharampal/                 # Main Python package
    ├── __init__.py
    ├── cli.py                 # CLI controller (start/stop)
    ├── embeddings.py          # Ollama embedding client
    ├── agent/
    │   ├── __init__.py
    │   └── graph.py           # LangGraph definition + tool binding
    ├── ui/
    │   ├── __init__.py
    │   └── chat_window.py     # customtkinter chat interface
    ├── storage/
    │   ├── __init__.py
    │   └── chroma_store.py    # ChromaDB wrapper
    └── tools/
        ├── __init__.py        # Tool registry (ALL_TOOLS)
        ├── space_news.py      # SpaceNews scraper (cached)
        ├── trading_news.py    # TradingEconomics scraper (live)
        ├── news_search.py     # Historical RAG search
        ├── news_scraper.py    # Historical web scraper
        └── list_sources.py    # Sources info tool
```

### Implementation Phases

#### Phase 1 - Core Agent (COMPLETED)
- [x] Project structure with `setup.py`
- [x] LangGraph agent with `ChatOpenAI` + LM Studio
- [x] customtkinter chat UI with model polling
- [x] CLI controller (`start`/`stop`) with detached process
- [x] Basic conversation flow

#### Phase 2 - Tools & RAG (COMPLETED)
- [x] SpaceNews scraper with curl (yesterday + day before)
- [x] TradingEconomics scraper (live, no cache)
- [x] ChromaDB integration for article storage
- [x] Ollama embeddings (`nomic-embed-text`)
- [x] Historical search tool (RAG-based)
- [x] Historical scraper tool (fallback)
- [x] Sources listing tool
- [x] Tool registry pattern
- [x] Anti-hallucination system prompt rules

#### Phase 3 - Future Enhancements (PLANNED)
- [ ] Plugin/tool auto-discovery from `dharampal/tools/`
- [ ] Streaming token-by-token output in UI
- [ ] Model picker dropdown in chat window
- [ ] Conversation export/import
- [ ] Additional news sources (tech, science, general)
- [ ] Article summarization with LLM
- [ ] Scheduled background scraping (cron-like)

### Design Decisions

1. **curl over requests for SpaceNews**: SpaceNews aggressively rate-limits Python requests (HTTP 429) but allows curl. Using subprocess curl bypasses this detection.

2. **ChromaDB for caching**: Articles from SpaceNews are persisted locally so historical queries don't require repeated scraping. Trading news is ephemeral and not cached.

3. **Two-day window for daily news**: Fetches yesterday + day before yesterday to ensure coverage even if one day has no articles.

4. **URL as document ID**: Natural deduplication in ChromaDB prevents storing the same article twice.

5. **Metadata filtering for date search**: Exact date match via `where={"date": "..."}` is faster than semantic search for date queries.

6. **Tool-calling over intent detection**: The LLM decides when to invoke tools based on user intent, rather than hardcoded keyword matching. More flexible and natural.

7. **No storage for trading news**: Trading data is time-sensitive and changes rapidly. Caching would provide stale information.

### Testing Strategy

- **Unit tests**: `notebook/test_tools.ipynb` for individual tool testing
- **Integration tests**: Agent graph end-to-end via CLI
- **Manual testing**: UI interaction, model loading, start/stop cycles

### Notes for Reviewers

- The system is designed for Windows but could be adapted for Linux/Mac by modifying `cli.py` process management
- ChromaDB uses cosine similarity for embeddings
- All tool errors are caught and returned as user-friendly messages (no crashes)
- The agent explicitly instructed not to hallucinate articles (system prompt rules)
