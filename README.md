# Project Gipsy

A fully local, privacy-first voice assistant and floating cyberpunk HUD for macOS. Built for Apple Silicon, inspired by F.R.I.D.A.Y. and E.D.I.T.H.

No cloud APIs. No telemetry call-homes. No monthly subscriptions. Everything runs directly on your machine.

---

## Why I Built This

Most AI voice assistants either feel sluggish because they wait for the entire LLM response before speaking a single word, or they run as clunky terminal scripts with zero visual feedback. 

I wanted something different:
- A responsive, conversational assistant that runs comfortably on a 16GB MacBook Pro without turning the fans into jet engines or eating up 10 GB of swap.
- An interface that feels alive—a sleek floating HUD with real-time waveform reactions, macOS system telemetry, and a compact "Dynamic Notch" mode that gets out of your way until you need it.
- Real OS-level control (launching apps, setting volume, checking battery, running scripts) with an actual security model so an LLM hallucination or prompt injection can't quietly wipe your drive.

---

## What It Looks Like

Gipsy lives as a native macOS desktop companion using Tauri v2 and native AppKit vibrancy (`NSVisualEffectMaterial::HudWindow`):

- **Dynamic Notch Pill (`280 × 56`)**: Sits cleanly near the top of your display or under the MacBook notch. Displays live assistant state dots, mic toggle, and real-time audio amplitude bars. Fully draggable anywhere on your screen.
- **Cyberpunk Expanded HUD (`780 × 660`)**: Expands automatically on speech or via hotkey. Features a multi-layered harmonic canvas visualizer, live telemetry (CPU, RAM, Battery, WebSocket latency, event counters), live conversation transcripts, an execution drawer for tool call inspection, and a docked text input bar.
- **Global Hotkey (`⌥ + Space`)**: Summon or hide Gipsy from any workspace or full-screen app instantly.
- **Menu Bar Tray**: Resides in your macOS menu bar with quick status and toggle controls.

---

## Architecture & How It Works

Rather than waiting for Ollama to finish generating an entire paragraph, Gipsy streams tokens and synthesizes audio sentence-by-sentence. While sentence $N$ is playing through Kokoro TTS, sentence $N+1$ is already being tokenized by the LLM.

```text
               Microphone Input
                      │
                      ▼
            Silero VAD (Voice Activity Detection)
                      │
              [Speech Detected]
                      │
                      ▼
     openWakeWord ("Hey Gipsy") / Manual Trigger
                      │
                      ▼
       Faster-Whisper (Local STT, Quantized)
                      │
                      ▼
      Ollama (qwen3.5:9b / qwen2.5:7b)
             │                 │
             │ (Function Call) │ (Streaming Text)
             ▼                 ▼
     macOS Tool Registry   Kokoro ONNX (Local TTS)
   (Apps, Volume, SysInfo)     │
             │                 ▼
             │          PortAudio Non-blocking Playback
             ▼                 │
     FastAPI WebSocket Bridge (127.0.0.1:8000)
             │
             ▼
     Tauri v2 Desktop HUD (React + Tailwind + AppKit Vibrancy)
```

---

## Security & Safety First

Giving an LLM access to native OS tool execution can be dangerous. Gipsy implements a defense-in-depth model:

1. **CSWSH Protection**: The WebSocket endpoint (`/ws`) requires an ephemeral cryptographic token generated locally at startup, preventing unauthorized websites from hijacking the voice daemon via cross-site WebSocket attacks.
2. **Interactive Admin Password Gate**: Routine operations (launching Safari, setting volume, checking battery) run with zero friction. However, high-risk or destructive commands (like `sudo`, package removal, disk operations, or raw shell execution) trigger a secure modal challenge requiring manual password entry.
3. **SSRF & Command Hardening**: Tool arguments undergo strict path sanitization, preventing outbound requests to sensitive internal IP ranges or command injection payloads.
4. **Audio Watchdog & Buffer Caps**: Prevents runaway audio capture streams from consuming memory, strictly capping buffers and resetting state to `IDLE` cleanly.
5. **Memory Budget**: Engineered to run within a lean **< 1.45 GB RAM** footprint for the entire audio and daemon pipeline on Apple Silicon.

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **Desktop Shell** | Tauri v2, Rust, macOS AppKit Vibrancy (`HudWindow`), Global Shortcuts, System Tray |
| **Frontend HUD** | React 19, TypeScript, Vite, Tailwind CSS v4, Lucide Icons, HTML5 Canvas Visualizer |
| **Backend Daemon** | Python 3.11+, FastAPI, Uvicorn, WebSockets, `psutil` |
| **Speech-to-Text** | Faster-Whisper (quantized int8/float16), Silero VAD, openWakeWord |
| **LLM & Reasoning** | Ollama (`qwen3.5:9b`, `qwen2.5:7b`, or `qwen3.5:4b`) with native JSON function calling |
| **Text-to-Speech** | Kokoro-ONNX (v1.0 high-quality female voice), Piper TTS fallback |

---

## Prerequisites

- **Hardware**: Mac with Apple Silicon (M1/M2/M3/M4), 16GB unified memory recommended.
- **Operating System**: macOS 13+ (Ventura, Sonoma, Sequoia).
- **Dependencies**:
  - Python 3.11+
  - Node.js 18+ & npm
  - Rust & Cargo (for Tauri desktop app compilation: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`)
  - [Ollama](https://ollama.com/) installed and running.

---

## Getting Started

### 1. Pull the Model

Start Ollama and pull the recommended model:

```bash
ollama pull qwen3.5:9b
```

*(Tip: If you want an even lighter footprint while running heavy IDEs, you can pull `qwen3.5:4b` or `qwen2.5:7b`.)*

### 2. Set Up the Python Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Verify your backend test suite:

```bash
pytest tests/
```

### 3. Run the Desktop Application

The native Tauri shell automatically supervises the Python backend daemon for you. From the project root:

```bash
cd frontend
npm install
npm run tauri dev
```

The HUD will compile, open in the compact Notch Pill mode on your desktop, and connect directly to the supervised backend daemon over local WebSocket.

---

## Usage & Controls

### Interacting

- **Voice**: Say `"Hey Gipsy"` (or click the microphone toggle) and speak your query.
- **Text**: Click the expand icon (or hit `⌥ + Space`), type into the docked command bar at the bottom, and hit Enter.

### Example Commands

- *"Open Calculator and Safari"*
- *"Set system volume to 40 percent"*
- *"What is my battery level and CPU load?"*
- *"Take a quick note: remember to push commit tonight"*
- *"Search Google for latest Apple Silicon benchmarks"*
- *"Open Spotify"*

### Desktop Hotkeys & Gestures

- `⌥ + Space`: Toggle HUD visibility anywhere on macOS.
- **Drag Pill / Header**: Click and hold anywhere on the notch pill or the expanded HUD header to reposition the window across your screens.
- **Pin Toggle**: Click the pin icon in the HUD header to keep the window permanently expanded without auto-collapsing to the pill when idle.

---

## Project Structure

```text
Gipsy/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI server & WebSocket endpoint
│   │   ├── llm.py               # Ollama streaming pipeline & tool orchestration
│   │   ├── security.py          # Ephemeral token auth, challenge gates, SSRF checks
│   │   ├── telemetry.py         # Real-time macOS CPU, RAM, battery metrics
│   │   ├── websocket_manager.py # Broadcast manager & client synchronization
│   │   └── voice/
│   │       ├── audio_loop.py    # Non-blocking audio capture & VAD pipeline
│   │       ├── vad.py           # Silero VAD state machine
│   │       ├── wake_word.py     # openWakeWord listener
│   │       ├── stt.py           # Faster-Whisper local transcriber
│   │       └── tts.py           # Kokoro ONNX streaming speech synthesizer
│   ├── tools/
│   │   ├── registry.py          # Tool schema registry & execution engine
│   │   └── os_tools.py          # AppleScript, volume, app launcher, telemetry tools
│   └── tests/                   # Automated pytest suite (security, tools, voice)
│
├── frontend/
│   ├── src-tauri/               # Native Rust desktop shell
│   │   ├── src/
│   │   │   ├── lib.rs           # Window vibrancy, drag handlers, global shortcut, tray
│   │   │   └── backend.rs       # Python backend process supervisor
│   │   ├── capabilities/        # Tauri v2 security & window capabilities
│   │   └── tauri.conf.json      # Window sizes, transparency, and permissions
│   └── src/                     # React HUD application
│       ├── components/
│       │   ├── PillView.tsx     # Notch pill UI with state indicator & waveform
│       │   ├── Visualizer.tsx   # Live HTML5 multi-frequency harmonic canvas
│       │   ├── TelemetryStrip.tsx # CPU, RAM, Battery, Link latency & Event counters
│       │   ├── TranscriptArea.tsx # User query & assistant response streaming
│       │   ├── CommandBar.tsx   # Docked text input with keyboard submission
│       │   ├── ExecutionDrawer.tsx # Live tool execution logs drawer
│       │   └── AdminAuthModal.tsx # Interactive password gate for sensitive tools
│       ├── hooks/               # WebSocket & Tauri window lifecycle hooks
│       └── App.tsx              # Root HUD container & layout
└── README.md
```

---

## Troubleshooting

- **Audio Playback / Mic Issues**: If macOS prompts for Microphone permissions, grant access in *System Settings → Privacy & Security → Microphone*.
- **Ollama Connection**: Ensure Ollama is running (`ollama list`). If your port is customized, set `OLLAMA_HOST` in your environment.
- **Port Conflicts**: Gipsy defaults to `127.0.0.1:8000`. You can change the port in `backend/app/main.py` and `frontend/src-tauri/tauri.conf.json`.

---

## License

MIT © [Sreerag](https://github.com/sreeragpp86)
