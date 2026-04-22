# Graph Report - .  (2026-04-22)

## Corpus Check
- Corpus is ~3,468 words - fits in a single context window. You may not need a graph.

## Summary
- 91 nodes · 139 edges · 6 communities detected
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 13 edges (avg confidence: 0.82)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Project Overview & Implementation|Project Overview & Implementation]]
- [[_COMMUNITY_CLI Controller|CLI Controller]]
- [[_COMMUNITY_Chat UI|Chat UI]]
- [[_COMMUNITY_Documentation & Setup|Documentation & Setup]]
- [[_COMMUNITY_Agent Graph|Agent Graph]]
- [[_COMMUNITY_Architecture & Technologies|Architecture & Technologies]]

## God Nodes (most connected - your core abstractions)
1. `ChatWindow` - 12 edges
2. `Dharampal AI Agent Implementation Plan` - 11 edges
3. `start()` - 10 edges
4. `stop()` - 9 edges
5. `Dharampal Project README` - 8 edges
6. `_run()` - 6 edges
7. `Project Structure` - 6 edges
8. `_find_lms()` - 5 edges
9. `Architecture & Technologies` - 5 edges
10. `Architecture at a Glance` - 5 edges

## Surprising Connections (you probably didn't know these)
- `LLM Backend: LM Studio with google/gemma-4-e4b` --conceptually_related_to--> `Architecture at a Glance`  [INFERRED]
  implementation_plan.md → README.md
- `Agent Framework: LangGraph and LangChain` --conceptually_related_to--> `Architecture at a Glance`  [INFERRED]
  implementation_plan.md → README.md
- `User Interface: customtkinter or tkinter` --conceptually_related_to--> `Architecture at a Glance`  [INFERRED]
  implementation_plan.md → README.md
- `CLI Management: Python setup.py or dharampal.bat` --conceptually_related_to--> `Architecture at a Glance`  [INFERRED]
  implementation_plan.md → README.md
- `Chat Interface` --implements--> `dharampal/ui/chat_window.py customtkinter GUI`  [INFERRED]
  implementation_plan.md → README.md

## Hyperedges (group relationships)
- **Dharampal Architecture Layers** — implementation_plan_llm_backend, implementation_plan_agent_framework, implementation_plan_ui_library, implementation_plan_cli_management [EXTRACTED 1.00]
- **Dharampal Project Files** — readme_dharampal_bat, readme_setup_py, readme_cli_py, readme_agent_graph_py, readme_ui_chat_window_py [EXTRACTED 1.00]
- **Dharampal Roadmap Phases** — readme_phase_2_tools, readme_phase_3_plugin_registry, readme_phase_4_ux_polish [EXTRACTED 1.00]
- **Dharampal Design Rationales** — rationale_ui_detached_process, rationale_input_disabled_startup, rationale_state_file_coordination, rationale_pythonw_detached, rationale_after_0_thread_safety, rationale_memory_saver, rationale_no_setx_path, rationale_keep_server_running, rationale_editable_install [EXTRACTED 1.00]

## Communities

### Community 0 - "Project Overview & Implementation"
Cohesion: 0.1
Nodes (22): Chat Interface, CLI Controller, Core Agent Logic, Dharampal AI Agent Implementation Plan, Goal Description, Project Initialization & Jupyter Notebook, Setup Instructions, setup.py for Package Registration (+14 more)

### Community 1 - "CLI Controller"
Cohesion: 0.26
Nodes (18): _clear_state(), _find_lms(), _kill_ui(), _launch_ui_detached(), _load_model(), _load_state(), main(), Dharampal CLI: `dharampal start` / `dharampal stop`.  `start` boots LM Studio, l (+10 more)

### Community 2 - "Chat UI"
Cohesion: 0.26
Nodes (4): ChatWindow, Dharampal chat window.  A minimal customtkinter chat UI. On startup it polls LM, Poll LM Studio's /v1/models endpoint until our identifier appears., run_app()

### Community 3 - "Documentation & Setup"
Cohesion: 0.15
Nodes (13): Space News Scraper Tool, Tools Implementation, Rationale: Editable install for development, Rationale: Do not use setx PATH, Configuration, Dharampal Project README, First-time Setup, Phase 2 - Tools & Space News Scraper (+5 more)

### Community 4 - "Agent Graph"
Cohesion: 0.48
Nodes (5): chatbot(), get_model(), get_response(), State, TypedDict

### Community 5 - "Architecture & Technologies"
Cohesion: 0.53
Nodes (6): Agent Framework: LangGraph and LangChain, Architecture & Technologies, CLI Management: Python setup.py or dharampal.bat, LLM Backend: LM Studio with google/gemma-4-e4b, User Interface: customtkinter or tkinter, Architecture at a Glance

## Knowledge Gaps
- **23 isolated node(s):** `Locate the `lms` CLI. Returns the resolved path or just 'lms' as a fallback.`, `Run a subprocess, surfacing stderr to the current console.`, `Spawn the UI in its own process so the terminal is free and the     window survi`, `Poll LM Studio's /v1/models endpoint until our identifier appears.`, `Goal Description` (+18 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `start()` connect `CLI Controller` to `Chat UI`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **Why does `Dharampal Project README` connect `Documentation & Setup` to `Project Overview & Implementation`, `Architecture & Technologies`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Why does `Dharampal AI Agent Implementation Plan` connect `Project Overview & Implementation` to `Documentation & Setup`, `Architecture & Technologies`?**
  _High betweenness centrality (0.086) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `start()` (e.g. with `.__init__()` and `.send_message()`) actually correct?**
  _`start()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Locate the `lms` CLI. Returns the resolved path or just 'lms' as a fallback.`, `Run a subprocess, surfacing stderr to the current console.`, `Spawn the UI in its own process so the terminal is free and the     window survi` to the rest of the system?**
  _23 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Project Overview & Implementation` be split into smaller, more focused modules?**
  _Cohesion score 0.1 - nodes in this community are weakly interconnected._