# Circle of Lies

Circle of Lies is an original social strategy simulator where one human player competes against five AI opponents in a multi-round trust game.

## Product Concept

- **Genre**: social strategy / social deduction-inspired (original ruleset)
- **Core tension**: shared progression with private incentives
- **Primary mechanics**: trust, suspicion, alliances, social signaling, and elimination votes
- **Educational framing**: practical game theory concepts in motion

## Why LLM-Driven Story Mode

- Richer social conversations and distinct character voices
- Dynamic reactions to player wording and social pressure
- Faster iteration on narrative quality and immersion
- Provider abstraction keeps integrations maintainable

## Tech Stack

- Frontend: Next.js (App Router), TypeScript, Tailwind CSS
- Backend: FastAPI, Python
- Database: SQLite
- Testing: pytest for core engine behavior

## Architecture

See [docs/architecture.md](docs/architecture.md).

High-level modules:

- `backend/app/engine`: game state transitions
- `backend/app/agents`: agent utilities
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
3. AI agents react through LLM-generated social turns
4. Trust/suspicion/alliance state updates
5. Group vote eliminates one participant
6. Round summary is logged and shown

The game ends when the player is eliminated, the round limit is reached, or only two participants remain.

## API Overview

- `POST /api/games`: create game
- `GET /api/games/{game_id}`: current game state
- `POST /api/games/{game_id}/story-turn`: play one social turn from natural-language player input
- `GET /api/games/{game_id}/logs`: structured round logs
- `GET /api/games/{game_id}/analytics`: end-of-game analytics
- `GET /api/games/{game_id}/llm/post-game-analysis`: optional LLM strategic summary
- `POST /api/games/{game_id}/llm/flavor-dialogue`: optional AI character flavor dialogue
- `GET /api/meta/actions`: action catalog

## Local Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
# Optional: copy .env.example to .env and set provider keys if you want LLM enhancements.
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

These remain feature-flagged and can be configured per environment.

## LLM Feature Flags

Backend environment variables:

```bash
LLM_ENABLED=true
LLM_PROVIDER=gemini   # gemini or openai
LLM_STORY_MODE=false  # when true, start game can generate cast + use story-turn input
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.1-flash-lite-preview
GEMINI_FALLBACK_MODELS=gemini-2.5-flash-lite,gemini-2.5-flash
GEMINI_MAX_RETRIES=3
GEMINI_RETRY_BASE_SECONDS=1.0
GEMINI_RETRY_MAX_SECONDS=10.0
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
LLM_TIMEOUT_SECONDS=20
```

If `LLM_ENABLED=false` or the provider key is missing, LLM features return safe fallback responses.
If `LLM_STORY_MODE=true`, LLM can generate character bios/traits and resolve free-text story turns with character reactions.
