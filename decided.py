"""Step 6 | Router: sends a message through the RAG route (mood or genre found) or the prompt-only route (greeting, small talk, off-topic)."""
from mood import detect, detect_smart, _target_moods

# Phrases that ask for more results with the same constraints
MORE_WORDS = ["یکی دیگه", "بیشتر", "دیگه چی", "پیشنهاد دیگه"]
# Cues that a message refines the previous request ("also not action")
REFINE_CUES = [" هم ", "همچنین", "ضمنا", "علاوه"]


def _rag(moods, genres, exclude, more=False):
    """Build a decision for the RAG route."""
    return {"route": "rag", "more": more, "moods": moods, "genres": genres, "exclude": exclude}


def decide(text, session):
    """Return the route and the constraints to search with; refinements are merged with the previous request."""
    has_last = bool(session["last_moods"] or session["last_genres"] or session["last_exclude"])

    if has_last and any(w in text for w in MORE_WORDS):
        words_moods, words_genres = detect(text)
        if not words_moods and not words_genres:
            return _rag(session["last_moods"], session["last_genres"], session["last_exclude"], more=True)

    moods, genres, exclude = detect_smart(text)

    if has_last:
        said_new_mood = bool(detect(text)[0])
        padded = " " + text + " "
        is_refine = exclude or (genres and any(c in padded for c in REFINE_CUES))
        if is_refine and not said_new_mood:
            exclude = list(dict.fromkeys(session["last_exclude"] + exclude))
            genres = [g for g in dict.fromkeys(session["last_genres"] + genres) if g not in exclude]
            moods = _target_moods(session["last_moods"], exclude)
            return _rag(moods, genres, exclude)

    if moods or genres or exclude:
        return _rag(moods, genres, exclude)

    return {"route": "prompt", "more": False, "moods": [], "genres": [], "exclude": []}
