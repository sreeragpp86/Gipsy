# Project Gipsy

A decoupled local voice assistant with OS control and a custom HUD.

## Repository Structure

```
.
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_health.py
│   ├── .env.example
│   ├── .gitignore
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── index.css
│   │   └── main.tsx
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.app.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   └── vite.config.ts
├── .gitignore
└── README.md
```

## Getting Started

### Backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

- Health Check: `GET http://localhost:8000/health`
- WebSocket: `ws://localhost:8000/ws`
- Tests: `pytest`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

- HUD Interface: `http://localhost:5173`
