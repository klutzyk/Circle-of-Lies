from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "circle_of_lies.db"
DEFAULT_MAX_ROUNDS = 7
MAX_ROUNDS_RANGE = (6, 8)
