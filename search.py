
"""Candidate retrieval: filter by constraints, then rank by rating, mood specificity and genre match."""
def find_movies(movies, moods=None, genres=None, k=5, exclude_ids=(), exclude=()):
    """Return up to k movies matching the moods and genres, skipping excluded ids, genres and moods."""
    moods, genres = moods or [], genres or []
    scored = []
    for m in movies:
        if m["id"] in exclude_ids:
            continue
        mood_hits = len(set(moods) & set(m["moods"]))
        genre_hits = len(set(genres) & set(m["genres"]))
        if set(exclude) & (set(m["genres"]) | set(m["moods"])):
            continue
        if moods and mood_hits == 0:
            continue
        score = m["rating"] + 3 * mood_hits / max(len(m["moods"]), 1) + 1.5 * genre_hits
        if m.get("source") == "sample":
            score += 1.5
        scored.append((score, m))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in scored[:k]]


if __name__ == "__main__":
    from clean import clean_movies
    from read import load_movies
    from mood import detect

    movies = clean_movies(load_movies())
    for text in ["غمگینم و انیمیشن می‌خوام", "عصبانی‌ام", "سلام"]:
        moods, genres = detect(text)
        print(text, moods, genres)
        for m in find_movies(movies, moods, genres, k=3):
            print("   ", m["title"], m["rating"], m["moods"])
