# Project Gipsy

A fully local voice assistant built for macOS, inspired by F.R.I.D.A.Y. and E.D.I.T.H. 

Gipsy listens for a wake word, transcribes speech locally, runs an LLM with native OS tool calling, and responds through a low-latency female voice—paired with a minimalist web HUD that reacts to every state in real time. No cloud APIs, no subscriptions, and everything stays on your machine.

<!-- Replace with a screenshot or short GIF of your HUD -->
<!-- ![Project Gipsy HUD](./docs/preview.png) -->

## Why I Built This

Most local voice assistants either feel sluggish because they wait for the entire LLM response before speaking, or they're just terminal scripts with no visual feedback. I wanted something that runs comfortably on a 16GB M2 MacBook Pro, responds fast enough for real conversation, and can actually control my machine.

## How It Works

Instead of waiting for a full response, Gipsy streams text from Ollama and synthesizes audio sentence by sentence while the next sentence is still generating:

```text
Mic / Wake Word ("Hey Gipsy")
  │
  ▼
Silero VAD + Faster-Whisper (Speech-to-Text)
  │
  ▼
Ollama (qwen3.5:9b) ──► macOS Tool Registry (Apps, Volume, Telemetry)
  │
  ▼
Kokoro ONNX / Piper TTS (Sentence-level streaming)
  │
  ▼
FastAPI WebSocket ◄──► React HUD (Visualizer, Transcript, Logs)

Features
100% Local Pipeline: Wake word (openWakeWord), VAD (silero-vad), STT (faster-whisper), LLM (Ollama), and TTS (kokoro-onnx / piper-tts) all run offline.
macOS System Control: Native function calling to launch apps, adjust system volume, and pull live CPU, RAM, and battery telemetry.
Reactive Web HUD: Built with React, Vite, and Tailwind CSS v4. Includes an HTML5 Canvas waveform visualizer driven by live WebSocket states (IDLE, LISTENING, PROCESSING, EXECUTING_TOOL, SPEAKING), a live transcript view, and a text command bar for quiet environments.
Tuned for 16GB Apple Silicon: Runs qwen3.5:9b with thinking mode disabled (think=False) and a capped 8192 context window to keep latency low and avoid memory swap.
Tech Stack
Backend: Python 3.11+, FastAPI, Uvicorn, WebSockets, psutil
AI / Audio: Ollama (qwen3.5:9b), faster-whisper, silero-vad, openWakeWord, kokoro-onnx
Frontend: React, Vite, Tailwind CSS v4, Lucide Icons
Prerequisites
macOS (tested on Apple Silicon M2, 16GB RAM)
Python 3.11+
Node.js 18+
Ollama installed and running
Getting Started
1. Pull the LLM
Make sure Ollama is running, then pull the default model:
ollama pull qwen3.5:9b

(If you want lower RAM usage while multitasking with heavy dev tools, swap the model in backend/core/brain.py to qwen3.5:4b.)
2. Start the Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

3. Start the Frontend HUD
cd frontend
npm install
npm run dev

Open http://localhost:5173 in your browser. The HUD will connect to ws://localhost:8000/ws automatically.
Project Structure
project-gipsy/
├── backend/
│   ├── core/          # Ollama brain, STT, TTS, and wake-word pipeline
│   ├── tools/         # macOS OS automation tool registry
│   └── main.py        # FastAPI server and WebSocket bridge
├── frontend/
│   ├── src/
│   │   ├── components/# Visualizer, telemetry strip, command bar, logs
│   │   └── hooks/     # WebSocket state management
│   └── vite.config.js
└── README.md

Roadmap
[ ] Custom fine-tuned voice checkpoint
[ ] Screen context awareness using qwen3.5:9b vision
[ ] Packaging the HUD as a lightweight floating desktop app (Tauri)
[ ] More OS tools (window management, Spotify controls, Git workflow shortcuts)
License
MIT
