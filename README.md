# Dharampal

A modular desktop AI agent for Windows that brings together a local LLM, intelligent web scraping, and a RAG-based memory system — all in a native chat interface.

**What it does:**
- **Chat** with a local AI model (Google Gemma 4 via LM Studio)
- **Fetch space news** from SpaceNews (cached locally for historical queries)
- **Get trading news** from TradingEconomics (live, no caching)
- **Search historical articles** using a local vector database (ChromaDB + Ollama embeddings)
- **Control everything** from the command line: `dharampal start` and `dharampal stop`

**Key features:**
- 🤖 **Local LLM** — No API keys, no internet required for chat
- 📰 **Smart News** — Fetches yesterday's + day before yesterday's space news automatically
- 🔍 **RAG Search** — Ask for news from any date; searches local cache first, then scrapes if needed
- 💼 **Trading Updates** — Live financial headlines from TradingEconomics
- 🎮 **Tic-Tac-Toe** — Built-in game: you play as X, AI plays as O
- 💾 **Persistent Memory** — Articles stored in ChromaDB with Ollama embeddings
- 🖥️ **Native UI** — Clean customtkinter chat window with floating widget
- ⚡ **Tool Routing** — LLM automatically decides which tool to use based on your question

---

## Table of Contents

1. [Architecture](#architecture)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [Available Commands](#available-commands)
7. [Tool Examples](#tool-examples)
8. [Troubleshooting](#troubleshooting)
9. [Development](#development)
10. [Roadmap](#roadmap)

---

## Architecture

```
User Input (Chat UI)
    |
    v
+---------------------+
|   LangGraph Agent   |
|   (dharampal/agent) |
+---------------------+
    |
    +--> Tool Router (LLM decides)
    |       |
    |       +--> SpaceNews (cached in ChromaDB)
    |       +--> TradingEconomics (live)
    |       +--> Historical Search (ChromaDB RAG)
    |       +--> List Sources (info)
    |
    +--> LLM Backend (LM Studio)
    |
    v
User Output (Chat UI)
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| **CLI Controller** | `dharampal/cli.py` | `start`/`stop` lifecycle management |
| **Chat UI** | `dharampal/ui/chat_window.py` | customtkinter desktop interface |
| **Agent Graph** | `dharampal/agent/graph.py` | LangGraph conversation + tool routing |
| **Tool Registry** | `dharampal/tools/__init__.py` | Auto-discovery of all tools |
| **Space Scraper** | `dharampal/tools/space_news.py` | SpaceNews archive (curl-based) |
| **Trading Scraper** | `dharampal/tools/trading_news.py` | TradingEconomics headlines |
| **RAG Search** | `dharampal/tools/news_search.py` | ChromaDB historical search |
| **Web Scraper** | `dharampal/tools/news_scraper.py` | Fallback for historical dates |
| **Sources Info** | `dharampal/tools/list_sources.py` | Show sources and cache status |
| **Tic-Tac-Toe** | `dharampal/tools/tictactoe.py` | In-chat game (user X, AI O) |
| **Vector Store** | `dharampal/storage/chroma_store.py` | ChromaDB wrapper |
| **Embeddings** | `dharampal/embeddings.py` | Ollama nomic-embed-text client |

---

## Prerequisites

Before installing Dharampal, ensure you have:

1. **Windows 10/11** with Python 3.10+ installed
2. **LM Studio** installed with CLI access (`lms` command)
3. **Ollama** installed for embeddings (`nomic-embed-text` model)
4. **Git** (optional, for cloning)

### Install LM Studio

1. Download from [lmstudio.ai](https://lmstudio.ai)
2. Install and open LM Studio
3. Go to **Developer** → **Install LM Studio CLI** (or follow [CLI docs](https://lmstudio.ai/docs/cli))
4. Verify in a new cmd window:
   ```cmd
   lms --version
   ```

### Install Ollama

1. Download from [ollama.ai](https://ollama.ai)
2. Install and verify:
   ```cmd
   ollama --version
   ```
3. Pull the embedding model:
   ```cmd
   ollama pull nomic-embed-text
   ```

### Download the AI Model

1. Open LM Studio GUI
2. Go to **Search** → Find `google/gemma-4-e4b` (or compatible Gemma model)
3. Download it (several GB, may take time)
4. Alternative models if gemma-4 is unavailable:
   - `google/gemma-3-4b-it`
   - `google/gemma-2-2b-it`
   - Any model from `lms ls` output

---

## Installation

### Step 1: Clone or Download the Project

```cmd
cd C:\Shrey_Projs
git clone <repository-url> dharampal_1
cd dharampal_1
```

Or download and extract the ZIP, then navigate to the folder.

### Step 2: Create Virtual Environment

```cmd
python -m venv venv
```

### Step 3: Activate Virtual Environment

```cmd
venv\Scripts\activate
```

Your prompt should now show `(venv)` at the beginning.

### Step 4: Install Dependencies

```cmd
pip install -e .
```

This installs:
- `langchain` + `langchain-openai` (LLM client)
- `langgraph` (agent framework)
- `customtkinter` (UI)
- `requests` + `beautifulsoup4` (web scraping)
- `chromadb` (vector database)
- `dateparser` (natural language dates)
- All transitive dependencies

The `-e .` flag installs in "editable" mode, so code changes take effect immediately without reinstalling.

### Step 5: Add to PATH (Optional but Recommended)

To run `dharampal` from any folder, add the project directory to your user PATH:

**GUI Method:**
1. Press `Win` → Search "environment variables"
2. Click "Edit the system environment variables"
3. Click "Environment Variables..."
4. Under "User variables", find and select `Path`
5. Click "Edit" → "New"
6. Add: `C:\Shrey_Projs\dharampal_1`
7. Click OK on all dialogs
8. **Open a new cmd window** (old windows keep old PATH)

**PowerShell Method:**
```powershell
[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path","User") + ";C:\Shrey_Projs\dharampal_1", "User")
```

> **Warning:** Do NOT use `setx PATH "%PATH%;..."` — it merges User + System PATH and can truncate at 1024 characters, corrupting your PATH.

### Step 6: Verify Installation

Open a **new** cmd window:

```cmd
where dharampal
```

Should output:
```
C:\Shrey_Projs\dharampal_1\dharampal.bat
```

Test the package import:
```cmd
cd C:\Shrey_Projs\dharampal_1
venv\Scripts\activate
python -c "from dharampal.agent.graph import get_response; print('OK')"
```

Should print `OK` with no errors.

---

## Configuration

All tunable settings are in `dharampal/cli.py`:

```python
MODEL_ID = "google/gemma-4-e4b"      # Model identifier in LM Studio
IDENTIFIER = "friday-main"            # Custom name for loaded model
CONTEXT_LENGTH = "90000"              # Token context window
GPU_MODE = "off"                      # Set to "on" if you have GPU
```

If you change `IDENTIFIER`, also update `MODEL_IDENTIFIER` in `dharampal/ui/chat_window.py`.

### Changing the Model

If `google/gemma-4-e4b` isn't available:

1. Check available models:
   ```cmd
   lms ls
   ```
2. Update `MODEL_ID` in `cli.py` with any installed model
3. Update `MODEL_IDENTIFIER` in `chat_window.py` if you changed `IDENTIFIER`

---

## Usage

### Start the Agent

```cmd
dharampal start
```

Expected output:
```
=== Dharampal: start ===
Starting LM Studio server...
Loading model google/gemma-4-e4b as 'friday-main'...
Chat window launched (PID 12345).
UI log: C:\Users\YourName\AppData\Local\Temp\dharampal_ui.log
The window will show 'waiting for model' until LM Studio finishes loading.
Run 'dharampal stop' when you're done.
```

A chat window opens with a floating widget button. The input is ready immediately — type while the model loads in the background.

### Stop the Agent

```cmd
dharampal stop
```

Or simply close the chat window — LM Studio keeps running in the background until you run `stop`.

---

## Available Commands

### CLI Commands

| Command | Description |
|---------|-------------|
| `dharampal start` | Start LM Studio, load model, launch chat UI |
| `dharampal stop` | Close UI, unload model, stop LM Studio server |
| `dharampal --help` | Show help message |

### Chat Commands (Type in UI)

The agent understands natural language. No special commands needed — just ask:

| What you type | What happens |
|---------------|--------------|
| "Get daily news" | Fetches yesterday + day before yesterday's space news |
| "Trading news" | Live financial headlines from TradingEconomics |
| "News for April 21st" | Searches local cache first, offers to scrape if empty |
| "Show sources" | Lists all sources and cache status |
| "Play tic tac toe" | Starts a game — you are X, AI is O |
| "What satellites launched recently?" | General chat with the LLM |

---

## Tool Examples

### Daily Space News

**You:** Get me the daily news

**Dharampal:**
```
SpaceNews articles from April 22, 2026:

1. NASA sets early September launch date for Roman Space Telescope
   Date: April 22, 2026
   Excerpt: NASA's Nancy Grace Roman Space Telescope is now scheduled for launch...
   URL: https://spacenews.com/...

2. Commerce Department budget proposal would halt work on TraCSS
   Date: April 22, 2026
   URL: https://spacenews.com/...

SpaceNews articles from April 21, 2026:

1. Northrop Grumman takes $71 million charge on Vulcan booster issue
   Date: April 21, 2026
   URL: https://spacenews.com/...

(I've saved 8 article(s) to my local memory.)
```

### Trading News

**You:** Show me trading news

**Dharampal:**
```
Trading Economics Headlines:

1. US Stocks Approach Records
   US equities rose on Wednesday, rebounding from earlier losses...

Source: https://tradingeconomics.com/
(These headlines are live and not cached.)
```

### Historical Search (with RAG fallback)

**You:** Get me news for April 21st

**Dharampal:**
```
Here are the space news articles I have cached for April 21, 2026:

1. Northrop Grumman takes $71 million charge on Vulcan booster issue
   Northrop Grumman has announced a $71 million charge...
   https://spacenews.com/...

2. Trump taps Raytheon executive for top military space acquisition post
   ...

Would you like me to check SpaceNews online for more articles from that date?
```

**You:** yes

**Dharampal:**
```
SpaceNews articles from April 21, 2026:

1. [Additional article not in cache]
   ...

(I've saved 2 new article(s) to my local memory.)
```

### Tic-Tac-Toe

**You:** Let's play tic tac toe

**Dharampal:**
```
Let's play Tic-Tac-Toe!

You are X, I am O. Pick a number (1-9) to place your mark.

 1 | 2 | 3
---+---+---
 4 | 5 | 6
---+---+---
 7 | 8 | 9
```

**You:** 5

**Dharampal:**
```
 1 | 2 | 3
---+---+---
 4 | X | 6
---+---+---
 7 | 8 | 9

I place O on 1. Your turn!
Pick an empty square (1-9).
```

**You:** yes *(after game ends)*

**Dharampal:** *(starts a new game)*

### List Sources

**You:** Show me the sources

**Dharampal:**
```
NEWS SOURCES

Available Sources:
--------------------------------------------------

SpaceNews:
  URL: https://spacenews.com/section/news-archive/
  Description: Space industry news and articles
  Cached locally: [YES]

TradingEconomics:
  URL: https://tradingeconomics.com/
  Description: Financial markets and economic indicators
  Cached locally: [NO] (live only)

Local Cache Status (RAG Database):
--------------------------------------------------
Total cached articles: 8

Cached dates: April 22, 2026, April 21, 2026

Usage Notes:
--------------------------------------------------
- 'Daily news' -> SpaceNews (yesterday + day before)
- 'Trading news' -> TradingEconomics (live, not cached)
- 'News for [date]' -> Searches cache first, then scrapes if needed
```

---

## Troubleshooting

### `'dharampal' is not recognized`

**Cause:** PATH doesn't include the project folder.

**Fix:** Add `C:\Shrey_Projs\dharampal_1` to your user PATH (see Step 5 in Installation). Open a **new** cmd window after changing PATH.

### `ModuleNotFoundError: No module named 'X'`

**Cause:** Virtual environment not activated or dependencies not installed.

**Fix:**
```cmd
cd C:\Shrey_Projs\dharampal_1
venv\Scripts\activate
pip install -e .
```

### `dharampal start` prints "Chat window launched" but no window appears

**Cause:** The detached UI process crashed silently.

**Fix:** Check the log file:
```cmd
type %TEMP%\dharampal_ui.log
```

Or run the UI in the foreground for visible tracebacks:
```cmd
venv\Scripts\activate
python -m dharampal.ui.chat_window
```

### Status bar stuck on "LM Studio not reachable yet"

**Cause:** LM Studio server didn't start or model is still loading.

**Fix:**
1. Check if `lms` is on PATH: `lms --version`
2. Check loaded models: `lms ps`
3. First load of a multi-GB model can take 5-10 minutes
4. Check LM Studio GUI for errors

### Input not responding during game

**Cause:** Rare threading issue where processing indicator gets stuck.

**Fix:** The input field is never disabled — you can always type. If the Send button is grayed out, wait for the "⚡ Processing..." indicator to disappear (max 30 seconds). If still stuck, close and reopen the chat window.

### Chat window opens but greeting fails with model error

**Cause:** Model loaded under a different identifier.

**Fix:**
```cmd
lms ps
```

If you see a different name, update `IDENTIFIER` in `cli.py` and `MODEL_IDENTIFIER` in `chat_window.py` to match.

### `dharampal stop` doesn't close the window

**Cause:** State file is stale (e.g., after Windows reboot).

**Fix:**
1. Close the window manually with X
2. Run: `lms ps` and `lms unload friday-main`
3. Delete the state file: `del %TEMP%\dharampal.state`

### No articles found when scraping

**Cause:** SpaceNews may be temporarily blocking requests.

**Fix:** Wait a few minutes and try again. The tool uses curl which is more reliable than Python requests.

---

## Development

### Project Structure

```
dharampal_1/
├── dharampal/
│   ├── cli.py              # CLI lifecycle controller
│   ├── embeddings.py       # Ollama embedding client
│   ├── agent/
│   │   └── graph.py        # LangGraph + tool binding
│   ├── ui/
│   │   ├── chat_window.py  # customtkinter chat interface
│   │   └── floating_widget.py  # Draggable floating button
│   ├── storage/
│   │   └── chroma_store.py # ChromaDB wrapper
│   └── tools/
│       ├── __init__.py     # Tool registry
│       ├── space_news.py   # SpaceNews scraper
│       ├── trading_news.py # TradingEconomics scraper
│       ├── news_search.py  # RAG search
│       ├── news_scraper.py # Historical scraper
│       ├── list_sources.py # Sources info
│       └── tictactoe.py    # Tic-Tac-Toe game
├── notebook/
│   └── test_tools.ipynb    # Jupyter test notebook
├── data/                   # ChromaDB storage (auto-created)
├── setup.py                # Package configuration
└── dharampal.bat          # Windows launcher
```

### Running Tests

Use the Jupyter notebook for testing individual tools:

```cmd
venv\Scripts\activate
jupyter notebook notebook/test_tools.ipynb
```

### Test Agent Without UI

```cmd
venv\Scripts\activate
python -c "from dharampal.agent.graph import get_response; print(get_response('hello'))"
```

### Test Individual Tool

```cmd
venv\Scripts\activate
python -c "from dharampal.tools.space_news import space_news_tool; print(space_news_tool.invoke({}))"
```

### Adding a New Tool

1. Create a new file in `dharampal/tools/`:
   ```python
   from langchain_core.tools import tool
   
   @tool
   def my_new_tool() -> str:
       """Description for the LLM."""
       return "Result"
   ```

2. Register it in `dharampal/tools/__init__.py`:
   ```python
   from dharampal.tools.my_new_tool import my_new_tool
   ALL_TOOLS = [..., my_new_tool]
   ```

3. The agent automatically discovers it via `ALL_TOOLS`.

---

## Roadmap

### Completed (Phase 1-3)
- ✅ Core chat agent with LangGraph
- ✅ customtkinter UI with model polling
- ✅ CLI start/stop lifecycle
- ✅ SpaceNews scraper with ChromaDB caching
- ✅ TradingEconomics live scraper
- ✅ RAG-based historical search
- ✅ Tool registry system
- ✅ Ollama embeddings
- ✅ Anti-hallucination prompts
- ✅ Tic-Tac-Toe game tool
- ✅ Floating widget (minimize/maximize)
- ✅ Robust input handling (never disabled)

### Planned (Phase 3+)
- 🔄 Auto-discovery of tools from filesystem
- 🔄 Streaming token output in UI
- 🔄 Model picker dropdown
- 🔄 Conversation history persistence
- 🔄 Additional news sources
- 🔄 Background scheduled scraping
- 🔄 Article summarization

---

## License

Personal project — no license specified yet.

## Support

For issues or questions:
- Check [Troubleshooting](#troubleshooting) above
- Review the [Implementation Plan](implementation_plan.md) for architecture details
- Check `%TEMP%\dharampal_ui.log` for UI errors
- Run tools individually in `notebook/test_tools.ipynb`
