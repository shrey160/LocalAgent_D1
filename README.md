# Dharampal

A modular desktop AI agent for Windows, backed by a local LLM served by
[LM Studio](https://lmstudio.ai) and orchestrated with
[LangGraph](https://langchain-ai.github.io/langgraph/). A single command —
`dharampal start` — brings up the model, connects the agent, and pops open a
native chat window; `dharampal stop` tears everything down.

Phase 1 (current) ships a plain chat agent: no tools, no plugins, just a
conversation with the local model. Later phases will add tool calling
(starting with a Space News scraper) on top of the same scaffolding.

---

## Architecture at a glance

| Layer | Tech | Role |
|---|---|---|
| LLM backend | LM Studio + `google/gemma-4-e4b` | OpenAI-compatible API at `http://localhost:1234/v1` |
| Agent | LangGraph + LangChain (`ChatOpenAI`) | Holds conversation state, will bind tools later |
| UI | `customtkinter` | Native desktop chat window with message history, input, status bar |
| CLI | Python + `dharampal.bat` | `start` / `stop` lifecycle across the whole stack |

The UI runs in its own detached process so closing the launching terminal
doesn't kill the chat window. `dharampal stop` coordinates everything via a
state file in `%TEMP%`.

---

## Project structure

```
C:\Shrey_Projs\dharampal_1\
├── dharampal.bat               # Windows launcher on PATH — dispatches to the CLI
├── setup.py                    # Package metadata + dependencies
├── implementation_plan.md      # Original plan (Phase 1..N)
├── README.md                   # This file
├── venv\                       # Python virtual environment
└── dharampal\                  # The actual Python package
    ├── __init__.py
    ├── cli.py                  # start / stop command implementation
    ├── agent\
    │   ├── __init__.py
    │   └── graph.py            # LangGraph chat graph + get_response()
    └── ui\
        ├── __init__.py
        └── chat_window.py      # customtkinter chat UI
```

### What each file does

**`dharampal.bat`** — One-line dispatcher. Cd's into its own directory,
activates `venv\Scripts\activate.bat`, and invokes
`python -m dharampal.cli start|stop`. Because it uses `%~dp0`, it works from
any cwd as long as the folder containing it is on PATH.

**`setup.py`** — Declares the package name, dependencies
(`langchain`, `langchain-openai`, `langgraph`, `customtkinter`, `requests`),
and a `dharampal` console-script entry point. `pip install -e .` reads this.

**`dharampal/cli.py`** — The lifecycle controller.

- `start()` — Starts LM Studio server (`lms server start`), kicks off
  `lms load google/gemma-4-e4b --identifier friday-main --context-length 90000 --gpu off`
  in the background, then spawns the UI in a **detached** process using
  `pythonw.exe` (no console window) with `DETACHED_PROCESS |
  CREATE_NEW_PROCESS_GROUP`. Persists the UI PID and model identifier to
  `%TEMP%\dharampal.state` so a later `stop` call can find them.
- `stop()` — Reads the state file, `taskkill /F /T /PID <ui_pid>` to close
  the window, `lms unload friday-main`, `lms server stop`, then deletes the
  state file. Works from any fresh terminal; doesn't need to be the same
  cmd window that ran `start`.
- Model + identifier constants (`MODEL_ID`, `IDENTIFIER`, `CONTEXT_LENGTH`,
  `GPU_MODE`) live at the top of the file — change them there.
- UI process stdout/stderr is captured to `%TEMP%\dharampal_ui.log` so
  import errors or tracebacks from the silent `pythonw` process aren't lost.

**`dharampal/agent/graph.py`** — The LangGraph definition.

- Defines a minimal `State` with `messages` using `add_messages` reducer.
- `get_model()` returns a `ChatOpenAI` client pointed at LM Studio's local
  OpenAI-compatible endpoint (`http://localhost:1234/v1`), `model="friday-main"`,
  `api_key="not-needed"` (LM Studio ignores it).
- `chatbot(state)` node prepends a system message the first turn and calls
  the model. Currently a single node; the tool-calling version in Phase 2
  will add a conditional edge into a `ToolNode` here.
- Compiles the graph with `MemorySaver()` so conversation history persists
  across turns under `thread_id="1"`.
- `get_response(user_input)` is the one-call helper the UI uses.

**`dharampal/ui/chat_window.py`** — The customtkinter GUI.

- Three-row layout: scrolling chat history (read-only `CTkTextbox`), input
  row (`CTkEntry` + Send button), status bar (`CTkLabel`).
- Input is **disabled at startup** until the model is reachable, so users
  don't get confusing "connection refused" errors while LM Studio is still
  loading the model.
- `_wait_for_model()` polls `GET http://localhost:1234/v1/models` every 2s
  (up to 10 minutes) until `friday-main` appears in the response.
- Once ready, enables input, asks the agent for a one-line greeting, and
  prints it. From there, Enter-to-send and clicking Send both fire
  `get_response()` off on a background thread so the UI never freezes.
- All `chat_history`/`status_label` writes go through `self.after(0, ...)`
  so background threads never touch Tk widgets directly.

---

## Prerequisites

1. **Python 3.10+** on Windows with `py` / `python` on PATH.
2. **LM Studio** installed, with the `lms` CLI available in your terminal.
   Test with `lms --version`. If the command isn't found, open LM Studio →
   Developer → install the CLI, or follow
   [LM Studio's docs](https://lmstudio.ai/docs/cli).
3. The model `google/gemma-4-e4b` downloaded in LM Studio (any compatible
   Gemma build works — see *Changing the model* below if the exact string
   isn't available).

---

## First-time setup

From the project root in a fresh `cmd`:

```
cd C:\Shrey_Projs\dharampal_1
python -m venv venv
venv\Scripts\activate
pip install -e .
```

`pip install -e .` reads `setup.py` and installs `langchain`,
`langchain-openai`, `langgraph`, `customtkinter`, `requests`, plus all
their transitive deps (`typing_extensions`, `pydantic`, etc.), in editable
mode so any code changes are picked up without reinstalling.

### Make `dharampal` runnable from any folder

Add `C:\Shrey_Projs\dharampal_1` to your **user PATH** so Windows can find
`dharampal.bat` from anywhere.

GUI route: Win → "environment variables" → *Edit the system environment
variables* → *Environment Variables…* → under *User variables*, edit
`Path`, add `C:\Shrey_Projs\dharampal_1`, OK everything. Open a fresh cmd.

PowerShell one-liner (same effect):

```powershell
[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path","User") + ";C:\Shrey_Projs\dharampal_1", "User")
```

> Do **not** use `setx PATH "%PATH%;..."` — it merges User + System PATH
> and truncates at 1024 chars, which can corrupt PATH.

Verify from a new cmd window:

```
where dharampal
```

Should print `C:\Shrey_Projs\dharampal_1\dharampal.bat`.

---

## Usage

### Start

```
dharampal start
```

Expected console output:

```
=== Dharampal: start ===
Starting LM Studio server...
Loading model google/gemma-4-e4b as 'friday-main' (may take a while on first run)...
Chat window launched (PID 12345).
UI log: C:\Users\Shrey\AppData\Local\Temp\dharampal_ui.log  (check this file if no window appears)
The window will show 'waiting for model' until LM Studio finishes loading.
Run 'dharampal stop' when you're done.
```

A chat window opens. The Send button and input box are disabled at first
and the status bar shows *"LM Studio reachable, waiting for 'friday-main'
to load… (attempt N)"*. Once the model finishes loading the input enables
itself and Dharampal greets you.

### Stop

```
dharampal stop
```

Works from any fresh terminal — it reads `%TEMP%\dharampal.state` to find
the UI PID:

```
=== Dharampal: stop ===
Closed chat window (PID 12345).
Unloading model 'friday-main'...
Stopping LM Studio server...
Dharampal stopped.
```

You can also just close the chat window's X button — the LM Studio server
and model will keep running in the background until you run
`dharampal stop` (that's intentional: stopping the server is a slow
operation so we let the user decide when to do it).

---

## Configuration

All tunable constants live at the top of `dharampal/cli.py`:

```python
MODEL_ID = "google/gemma-4-e4b"
IDENTIFIER = "friday-main"
CONTEXT_LENGTH = "90000"
GPU_MODE = "off"
```

If you change `IDENTIFIER`, also update `MODEL_IDENTIFIER` in
`dharampal/ui/chat_window.py` so the readiness poll looks for the right
entry.

### Changing the model

`google/gemma-4-e4b` is the string from the original plan. If LM Studio
can't find it (Gemma 4 wasn't a real release at the time of writing), pick
any installed OpenAI-compatible model and update `MODEL_ID` — common
substitutes:

- `google/gemma-3-4b-it`
- `google/gemma-2-2b-it`
- whatever shows up in `lms ls`

### State files

| File | Purpose |
|---|---|
| `%TEMP%\dharampal.state` | UI PID + model identifier; written by `start`, read by `stop`. |
| `%TEMP%\dharampal_ui.log` | stdout/stderr of the detached UI process. Check this first if the window never appears. |

---

## Troubleshooting

**`'dharampal' is not recognized as an internal or external command`**
PATH doesn't include the project folder. See *Make dharampal runnable from
any folder* above. Remember to open a fresh cmd — already-open windows
keep the old PATH.

**`ModuleNotFoundError: No module named 'typing_extensions'` (or customtkinter, or requests)**
Venv isn't fully set up. From the project root:

```
venv\Scripts\activate
pip install -e .
```

**`dharampal start` prints "Chat window launched" but nothing appears**
The detached UI process crashed silently. Open
`%TEMP%\dharampal_ui.log` — the traceback is there. For an even faster
diagnosis, run the UI in the foreground with a visible console:

```
venv\Scripts\activate
python -m dharampal.ui.chat_window
```

**Status bar stuck on "LM Studio not reachable yet, retrying…"**
Either LM Studio server didn't start (is `lms` on PATH?) or your model is
still downloading/loading. `lms ps` from another cmd shows what's loaded.
First load of a multi-GB model can take minutes.

**Chat window opens but greeting fails with a model error**
The model loaded under a different identifier than `friday-main`. Check
`lms ps` — if you see a different name, either restart via
`dharampal stop && dharampal start`, or update `IDENTIFIER` /
`MODEL_IDENTIFIER` to match.

**`dharampal stop` doesn't close the window**
The state file is stale (e.g. Windows was rebooted). Close the window
manually with its X, then run `lms ps` and `lms unload <name>` by hand.
Delete `%TEMP%\dharampal.state` to reset.

---

## Development

The package is installed in editable mode (`pip install -e .`), so edits
to `dharampal/**.py` take effect the next time you run `dharampal start`.
No reinstall needed.

Run the agent logic without the GUI (useful for debugging the graph):

```python
venv\Scripts\activate
python -c "from dharampal.agent.graph import get_response; print(get_response('hi'))"
```

Run the GUI directly with a visible console (for tracebacks):

```
python -m dharampal.ui.chat_window
```

---

## Roadmap

Tracked in `implementation_plan.md`. Next phases:

1. **Phase 2 — Tools & Space News scraper.**
   - `dharampal/tools/space_news.py`: `requests` + `BeautifulSoup` scraper
     targeting `https://spacenews.com/section/news-archive/`, filtered to
     today + yesterday by parsed publish dates, wrapped as a LangChain
     `@tool`.
   - `graph.py`: bind tools to the model, add a `ToolNode` and a
     conditional edge from the chatbot to the tool executor and back.
2. **Phase 3 — Plugin/tool registry.** Discover tool modules under
   `dharampal/tools/` at startup so adding a new capability is a matter of
   dropping in a file.
3. **Phase 4 — UX polish.** Streaming token-by-token output in the chat
   window, model picker in the UI, conversation history persistence
   across `stop`/`start`.

---

## License

Personal project; no license specified yet.
