# Dharampal AI Agent Implementation Plan

## Goal Description
Build a modular AI agent named "dharampal" for Windows using LangGraph and LM Studio (Google Gemma 4). The agent will have a windowed chat interface, support custom tools (including a Space News scraper), and be controllable via command line (`dharampal start` / `dharampal stop`). 

## Architecture & Technologies
- **LLM Backend**: LM Studio running locally with `google/gemma-4-e4b` (OpenAI-compatible API).
- **Agent Framework**: LangGraph and LangChain to manage state and tool execution in a modular way.
- **User Interface**: `customtkinter` (or standard `tkinter`) to provide a clean, native desktop window with a chat interface. It will open immediately when the agent starts.
- **CLI Management**: A Python `setup.py` exposing a command line tool, or simple Windows Batch files (`dharampal.bat`) to handle the `start` and `stop` commands. `start` will launch the LM studio server (via `lms` command) and the UI. `stop` will terminate the processes.

## Proposed Changes

### 1. Project Initialization & Jupyter Notebook
- Create `c:/Shrey_Projs/dharampal_1/test_agent.ipynb` to test LangGraph tool binding and LLM responses using LM Studio API.
- Create basic project structure (`dharampal/` package).

### 2. Tools Implementation
#### [NEW] `c:/Shrey_Projs/dharampal_1/dharampal/tools/space_news.py`
- A scraper using `requests` and `BeautifulSoup`.
- Targets `https://spacenews.com/section/news-archive/`.
- Extracts articles from today and yesterday by parsing the publishing dates.
- Wrapped as a LangChain `@tool` so it can be easily added to the agent.

### 3. Core Agent Logic
#### [NEW] `c:/Shrey_Projs/dharampal_1/dharampal/agent/graph.py`
- Defines the LangGraph State.
- Integrates `ChatOpenAI` initialized with LM Studio's local URL (`http://localhost:1234/v1`).
- Binds available tools (e.g., `space_news_tool`) dynamically to allow modular tool addition.

### 4. Chat Interface
#### [NEW] `c:/Shrey_Projs/dharampal_1/dharampal/ui/chat_window.py`
- A windowed GUI using a Python UI library.
- Contains a chat history display and a text input field.
- Connects to the LangGraph agent to stream or display responses.
- On launch (loading properly), triggers a system prompt to make the agent greet the user.

### 5. CLI Controller
#### [NEW] `c:/Shrey_Projs/dharampal_1/dharampal/cli.py`
- Handles `start` and `stop` commands.
- `start`: 
  1. Executes `lms load "google/gemma-4-e4b" --identifier friday-main --context-length 90000 --gpu off` in a subprocess.
  2. Launches the UI application.
- `stop`: 
  1. Closes the UI.
  2. Executes `lms unload friday-main` or kills the LM studio process safely.

#### [NEW] `c:/Shrey_Projs/dharampal_1/setup.py`
- Standard Python package setup to register the `dharampal` executable in the user's environment.

## User Review Required
> [!IMPORTANT]
> - Which UI library do you prefer? I suggest `customtkinter` for a modern look, or `tkinter` for zero dependencies, or `PyQt5`. 
> - For the CLI commands to work globally from any cmd window, we will install the package via `pip install -e .` in your Python environment. Is that acceptable?
> - Please let me know your thoughts on the plan.

## Setup Instructions (Once implemented)
1. Ensure your Python environment is active.
2. Run `pip install -e .` in the `c:/Shrey_Projs/dharampal_1` directory.
3. Make sure the LM Studio CLI (`lms`) is installed and available in your System PATH.
4. Type `dharampal start` in cmd to begin.
