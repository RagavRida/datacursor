# DataCursor - AI-Native Data Science IDE

A Jupyter Notebook clone where AI has direct access to the runtime state, enabling context-aware code generation.

![DataCursor](https://img.shields.io/badge/Status-Development-blue)

## Features

- **📝 Cell-Based Editing**: Monaco Editor with Python syntax highlighting
- **🧠 Shadow Context Bridge**: AI sees your variables, DataFrames, and imports
- **⌨️ Keyboard Shortcuts**: `Cmd+K` for AI, `Shift+Enter` to run
- **🔀 Diff View**: See AI suggestions with green/red highlighting
- **🔄 Real-time Execution**: WebSocket-based kernel communication

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React + Vite)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Notebook   │  │    Cell     │  │     AI Chat         │  │
│  │  (Manager)  │  │  (Monaco)   │  │  (Context Display)  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                          │                                   │
│                    WebSocket                                 │
└──────────────────────────┼──────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────┐
│                     Backend (FastAPI)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │    main.py  │  │   kernel_   │  │     ai_bridge.py    │  │
│  │   (Server)  │  │  manager.py │  │   (Gemini LLM)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                          │                                   │
│                   jupyter_client                             │
└──────────────────────────┼──────────────────────────────────┘
                           │
                  ┌────────────────┐
                  │ IPython Kernel │
                  └────────────────┘
```

## Quick Start

### 1. Backend Setup

```bash
cd datacursor/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set API key
export GOOGLE_API_KEY="your-api-key"

# Start server
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd datacursor/frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

### 3. Open in Browser

Navigate to **http://localhost:5173**

## Usage

1. **Run Code**: Press `Shift+Enter` or click the Play button
2. **AI Assist**: Press `Cmd+K` (Mac) or `Ctrl+K` (Windows/Linux)
3. **Accept AI Code**: Click the green "Accept" button on the diff view
4. **Add Cell**: Click "+ Add Cell" or run the last cell

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Shift+Enter` | Run cell and move to next |
| `Cmd/Ctrl+Enter` | Run cell in place |
| `Cmd/Ctrl+K` | Open AI prompt |
| `Escape` | Close AI prompt |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/kernel/start` | POST | Start a new kernel |
| `/kernel/shutdown` | POST | Shutdown kernel |
| `/kernel/execute` | POST | Execute code |
| `/kernel/context/{id}` | GET | Get runtime context |
| `/ai/complete` | POST | Get AI code completion |
| `/ws/{session_id}` | WebSocket | Real-time communication |

## Tech Stack

- **Frontend**: React, Vite, TypeScript, Tailwind CSS, Monaco Editor
- **Backend**: FastAPI, jupyter_client, langchain-google-genai
- **Runtime**: IPython Kernel

## License

MIT

