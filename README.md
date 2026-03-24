# Circle of Lies

Circle of Lies is an original social strategy simulator where one human player competes against five deterministic AI opponents in a multi-round trust game.

The project is designed for portfolio review and interviews: clear architecture, deterministic game logic, explainable AI behavior, and end-of-game analytics.

## Product Concept

- **Genre**: social strategy / social deduction-inspired (original ruleset)
- **Core tension**: shared progression with private incentives
- **Primary mechanics**: trust, suspicion, alliances, social signaling, and elimination votes
- **Educational framing**: practical game theory concepts in motion

## Why Rule-Based Agents for MVP

- Deterministic and testable outcomes
- Lower operational complexity than LLM-in-the-loop turn logic
- Easier to explain in architecture and system design interviews
- Clear extension points for optional LLM features later

## Tech Stack

- Frontend: Next.js (App Router), TypeScript, Tailwind CSS
- Backend: FastAPI, Python
- Storage: SQLite
- Testing: pytest for core engine behavior

## Architecture

See [docs/architecture.md](docs/architecture.md).

High-level modules:

- `backend/app/engine`: deterministic game state transitions
- `backend/app/agents`: rule-based AI heuristics
- `backend/app/api`: FastAPI route layer
- `backend/app/services`: orchestration and application use-cases
- `backend/app/db`: SQLite schema + repository functions
- `frontend/app`: pages and interaction flow
- `frontend/lib`: API client
- `frontend/types`: typed game contracts

## Core Gameplay Loop

For each round:

1. Event context is presented
2. Player selects an action (optionally with a target)
3. AI agents react with deterministic heuristics
4. Trust/suspicion/alliance state updates
5. Group vote eliminates one participant
6. Round summary is logged and shown

The game ends when the player is eliminated, the round limit is reached, or only two participants remain.

## API Overview

- `POST /api/games`: create game
- `GET /api/games/{game_id}`: current game state
- `POST /api/games/{game_id}/actions`: play one round
- `GET /api/games/{game_id}/logs`: structured round logs
- `GET /api/games/{game_id}/analytics`: end-of-game analytics
- `GET /api/meta/actions`: action catalog

## Local Setup

### Backend

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
$env:NEXT_PUBLIC_API_BASE='http://127.0.0.1:8000'
npm run dev
```

Open `http://127.0.0.1:3000`.

## Run Tests

```bash
cd backend
pytest
```

## Optional LLM Extension Points (Not Core MVP)

- Post-game strategic coaching summary
- Flavor dialogue generation
- Scenario generation and adaptive narrative variants

These should remain feature-flagged and not alter deterministic engine correctness.
