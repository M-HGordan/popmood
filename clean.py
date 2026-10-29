"""Step 3 | Cleaning utilities: deduplication, id-collision handling, text rendering and the one-off TMDB CSV converter."""
import json
import pandas as pd
from config import TMDB_CSV, TMDB_PATH
from read import load_movies

GENRE_FIX = {"science fiction": "sci-fi"}

GENRE_TO_MOODS = {
    "comedy": ["happy"], "family": ["happy", "angry"], "animation": ["happy"],
    "music": ["happy"], "adventure": ["happy"],
    "drama": ["sad", "neutral"], "romance": ["sad"],
    "action": ["angry"], "crime": ["angry"], "war": ["angry"],
    "thriller": ["surprise"], "mystery": ["surprise"],
    "sci-fi": ["surprise"], "fantasy": ["surprise"], "horror": ["surprise"],
    "documentary": ["neutral"], "history": ["neutral"],
}


def prepare_tmdb(csv_path=TMDB_CSV, out_path=TMDB_PATH, top=400):
    """Convert the Kaggle TMDB CSV into the project schema (top movies by votes, moods inferred from genres)."""
    df = pd.read_csv(csv_path)
    df = df[(df["original_language"] == "en") & (df["status"] == "Released")]
    df = df.dropna(subset=["overview", "release_date"])
    df = df.sort_values("vote_count", ascending=False).head(top)

    movies = []
    for _, r in df.iterrows():
        genres = [g["name"].lower() for g in json.loads(r["genres"])]
        genres = [GENRE_FIX.get(g, g) for g in genres]

        moods = []
        for g in genres:
            for m in GENRE_TO_MOODS.get(g, []):
                if m not in moods:
                    moods.append(m)

        movies.append({
            "id": int(r["id"]),
            "title": r["title"],
            "title_fa": "",
            "year": int(str(r["release_date"])[:4]),
            "genres": genres,
            "moods": moods or ["neutral"],
            "rating": round(float(r["vote_average"]), 1),
            "poster": "",
            "overview": r["overview"],
            "keywords": [k["name"] for k in json.loads(r["keywords"])][:8],
        })

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(movies, f, ensure_ascii=False, indent=1)
    print(len(movies), "فیلم ذخیره شد")


def clean_movies(movies):
    """Deduplicate movies by title and renumber colliding ids."""
    cleaned = []
    seen = set()
    used_ids = set()
    for m in movies:
        key = m["title"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        mid = m["id"]
        if mid in used_ids:
            mid += 100000
        used_ids.add(mid)
        cleaned.append({
            "id": mid,
            "title": m["title"].strip(),
            "title_fa": m["title_fa"].strip(),
            "year": m["year"],
            "genres": [g.lower() for g in m["genres"]],
            "moods": [x.lower() for x in m["moods"]],
            "rating": m["rating"],
            "poster": m["poster"] or None,
            "overview": m.get("overview", ""),
            "keywords": m.get("keywords", []),
            "source": m.get("source", "sample"),
        })
    return cleaned


def movie_to_text(m):
    """Render a movie as one searchable line of text."""
    name = m["title_fa"] or m["title"]
    text = (f'{name} ({m["title"]}, {m["year"]}) | '
            f'ژانر: {", ".join(m["genres"])} | '
            f'حال مناسب: {", ".join(m["moods"])} | امتیاز: {m["rating"]}')
    if m["overview"]:
        text += f' | خلاصه: {m["overview"]}'
    return text


if __name__ == "__main__":
    import sys
    if "--tmdb" in sys.argv:
        prepare_tmdb()          # python clean.py --tmdb
    else:
        movies = clean_movies(load_movies())
        print(len(movies), "فیلم تمیز شد")
        print(movie_to_text(movies[0]))
