"""Step 2 | Dataset loading: reads the official movies_sample.json and, optionally, the TMDB extract."""
import json
import os
from config import MOVIES_PATH, TMDB_PATH, USE_TMDB


def _load(path):
    """Load a UTF-8 JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


POSTERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "posters")


def attach_posters(movies):
    """Attach web/posters/<id>.<ext> to movies without a poster; the official dataset file is never modified."""
    for m in movies:
        if m.get("poster") or m.get("source") != "sample":
            continue
        for ext in ("jpg", "jpeg", "png", "webp"):
            if os.path.exists(os.path.join(POSTERS_DIR, f"{m['id']}.{ext}")):
                m["poster"] = f"/posters/{m['id']}.{ext}"
                break


def load_movies():
    """Return all movies: the official sample first, then the optional TMDB extract."""
    movies = _load(MOVIES_PATH)
    for m in movies:
        m["source"] = "sample"
    if USE_TMDB and os.path.exists(TMDB_PATH):
        extra = _load(TMDB_PATH)
        for m in extra:
            m["source"] = "tmdb"
        movies += extra
    attach_posters(movies)
    return movies


if __name__ == "__main__":
    movies = load_movies()
    print(len(movies), "فیلم خونده شد")
    print(movies[0])
