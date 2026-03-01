# Director Mode

AI-powered interactive story directing with Google Gemini. Speak or type cinematic directions — pan, cut, introduce characters, shift moods — and watch the narrative unfold in real time.

## Architecture

```
┌─────────────┐     WebSocket/REST     ┌─────────────┐     google-genai     ┌─────────────┐
│   Frontend   │ ◄──────────────────► │   Backend    │ ◄────────────────► │  Gemini API  │
│  React/Vite  │                       │   FastAPI    │                     │  2.5 Flash   │
│              │                       │              │                     │              │
│ Canvas       │                       │ Director     │                     │ Narration    │
│ Voice Input  │                       │ Agent        │                     │ Function     │
│ Timeline     │                       │ Story State  │                     │ Calling      │
└─────────────┘                       └─────────────┘                     └─────────────┘
```

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 22+
- [Google Gemini API key](https://aistudio.google.com/apikey)

### Setup

```bash
# Clone
git clone https://github.com/sphilius/director-mode-gemini.git
cd director-mode-gemini

# Environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

### Run

```bash
# Terminal 1 — Backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Open [http://localhost:5173](http://localhost:5173) and start directing.

## Project Structure

```
director-mode-gemini/
├── backend/
│   ├── main.py                  # FastAPI app, routes, WebSocket
│   ├── agents/
│   │   └── director_agent.py    # Gemini-powered directing agent
│   ├── tools/                   # Extensible tool definitions
│   ├── utils/
│   │   └── story_state.py       # Narrative state management
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── components/
│       │   ├── DirectorCanvas.jsx   # Main narration display
│       │   ├── VoiceControls.jsx    # Text + speech input
│       │   ├── StatusBar.jsx        # Connection & session status
│       │   └── StoryTimeline.jsx    # Scene progression sidebar
│       ├── hooks/
│       │   └── useDirectorSession.js  # WebSocket session hook
│       └── styles/
│           └── global.css
├── infra/
│   └── deploy.sh               # Cloud Run deployment
├── docs/
│   └── architecture.svg
├── Dockerfile
├── .env.example
├── .gitignore
└── README.md
```

## How It Works

1. **You direct** — type or speak commands like *"pan to the harbour at dawn"* or *"introduce a mysterious stranger"*
2. **Gemini interprets** — the Director Agent sends your cue to Gemini with full story context
3. **Narration streams** — vivid scene descriptions stream back token-by-token via WebSocket
4. **State evolves** — Gemini uses function calling to update scenes, characters, and moods automatically
5. **Timeline builds** — every scene is logged with its mood, characters, and director notes

## API

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/api/direct` | POST | Send a directive (non-streaming) |
| `/api/session/{id}` | GET | Get session state |
| `/api/session/{id}/reset` | POST | Reset a session |
| `/ws/direct/{id}` | WS | Streaming directive channel |

## Deployment

### Docker

```bash
docker build -t director-mode .
docker run -p 8000:8000 -e GEMINI_API_KEY=your-key director-mode
```

### Google Cloud Run

```bash
export GEMINI_API_KEY=your-key
./infra/deploy.sh your-project-id us-central1
```

## License

MIT
