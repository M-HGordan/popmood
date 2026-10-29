"""Step 4 | Mood and genre detection for Persian text: keyword rules first, LLM classification only for ambiguous sentences."""
import re

MOOD_WORDS = {
    "happy":    ["شارژ", "روحیه", "سرحالم", "حالم رو خوب", "بخندونه", "شاد", "خوشحال", "سرحال", "حال خوب", "بخندم", "خنده", "انرژی"],
    "sad":      ["غمگین", "ناراحت", "دلتنگ", "افسرده", "گریه", "دلم گرفته", "حالم گرفته", "غصه", "داغون", "دپرس"],
    "angry":    ["عصبانی", "خشمگین", "حرصی", "کلافه", "عصبی"],
    "surprise": ["هیجان", "غافلگیر", "شگفت", "پیچیده", "پرپیچ", "پیچ و خم", "ذهن", "ذهنم", "کنجکاو"],
    "neutral":  ["معمولی", "عادی", "خسته", "بی حوصله", "بیحوصله"],
}

GENRE_WORDS = {
    "animation": ["انیمیشن", "کارتون"],
    "comedy":    ["کمدی", "خنده دار", "خنده‌دار"],
    "action":    ["اکشن", "درگیری"],
    "sci-fi":    ["علمی تخیلی", "علمی‌تخیلی", "فضایی", "فضا"],
    "drama":     ["درام"],
    "family":    ["خانوادگی", "خانواده"],
    "thriller":  ["تریلر", "ترسناک"],
    "romance":   ["عاشقانه", "رمانتیک"],
    "fantasy":   ["فانتزی"],
    "mystery":   ["معمایی", "جنایی"],
}


def _normalize(text):
    """Unify characters and apply mid-sentence self-corrections."""
    text = re.sub(r"^\s*نه[\s،,]+(?=(الان|حالا|من|راستش))", "", text)
    text = text.replace("\u200c", " ").replace("ي", "ی").replace("ك", "ک").replace("غم گین", "غمگین")
    return _after_correction(text)


CORRECTION = re.compile(r"(نه\s*صبر\s*کن|صبر\s*کن|نه\s*نه|اشتباه\s*گفتم|یعنی\s*نه|ببخشید)[\s،,.!]*")


def _after_correction(text):
    """Keep only what the user said after a self-correction such as 'no, wait, ...'."""
    parts = CORRECTION.split(text)[::2]
    tail = parts[-1].strip() if len(parts) > 1 else ""
    return tail if len(tail.split()) >= 2 else text


def _hits(table, text):
    """Return the table keys found in the text, ordered by first appearance."""
    found = []
    for key, words in table.items():
        pos = [text.find(_normalize(w)) for w in words if _normalize(w) in text]
        if pos:
            found.append((min(pos), key))
    return [k for _, k in sorted(found)]


def detect(text):
    """Return (moods, genres) found by keywords, ordered by position in the sentence."""
    text = _normalize(text)
    return _hits(MOOD_WORDS, text), _hits(GENRE_WORDS, text)


NEG_AFTER = ["نباشه", "نباشد", "نمی خوام", "نمیخوام", "نخوام", "نه "]
NEG_BEFORE = ["بدون", "غیر از", "به جز", "نه "]


def has_negation(text):
    """True if the sentence contains a negation word."""
    text = _normalize(text) + " "
    return any(n in text for n in NEG_AFTER + NEG_BEFORE)


def _negated(text, words, window):
    """True when one of the words is negated within a small window of words."""
    for w in words:
        w = _normalize(w)
        start = 0
        while True:
            i = text.find(w, start)
            if i == -1:
                break
            after = text[i + len(w): i + len(w) + window]
            before = text[max(0, i - 12): i]
            if any(n in after for n in NEG_AFTER) or any(n in before for n in NEG_BEFORE):
                return True
            start = i + 1
    return False


def find_excluded(text, genres, moods=()):
    """Return the genres and moods the user explicitly does not want (e.g. 'not action', 'not sad')."""
    text = _normalize(text) + " "
    excluded = [g for g in genres if _negated(text, GENRE_WORDS[g], 25)]
    excluded += [x for x in moods if _negated(text, MOOD_WORDS[x], 14)]
    return excluded


def _target_moods(moods, excluded):
    """Turn 'I feel X but do not want X movies' into the mood the user wants to reach."""
    moods = [x for x in moods if x not in excluded]
    if not moods and any(x in MOOD_WORDS for x in excluded):
        moods = ["happy"]
    return moods


GREETINGS = ["خوبم", "عالیم", "سلام", "درود", "خوبی", "چطوری", "مرسی", "ممنون", "خداحافظ", "hi", "hello"]

CLASSIFY_PROMPT = """You classify a Persian message for a movie assistant.
Return ONLY a JSON object, nothing else:
{"moods": [...], "genres": [...], "exclude_genres": [...], "exclude_moods": [...]}
moods: the user's CURRENT feeling(s), main one first, at most 2. Allowed: happy, sad, angry, surprise, neutral.
  "make me feel good" is NOT a feeling by itself: if the user states another feeling, use that one.
  If the user only wants to cheer up without naming a feeling, use happy.
  Examples that mean happy: "recharge me", "boost my mood", "give me energy", "cheer me up" (Persian: حالم رو شارژ کن، روحیه بده، سرحالم کنه).
genres: genres the user WANTS. Allowed: animation, comedy, action, sci-fi, drama, family, thriller, romance, fantasy, mystery.
exclude_genres: genres the user does NOT want (same allowed list).
exclude_moods: moods the user does NOT want the movie to have (e.g. "not a sad movie" -> ["sad"]). Allowed: happy, sad, angry, surprise, neutral.
  If the user feels bad but wants a movie that is not sad, put sad in exclude_moods and leave moods empty or ["happy"].
If the message has no mood or genre information (greeting, small talk), return empty lists."""


def is_greeting(text):
    """True if the message is only a greeting."""
    return len(text.split()) <= 3 and any(g in text for g in GREETINGS)


def detect_smart(text):
    """Return (moods, genres, exclude); keywords first, LLM classification (max 6 s) only for ambiguous, negated or multi-mood sentences."""
    import json
    import re
    import llm

    moods, genres = detect(text)
    pair = re.search(r"نه\s+\S+\s+نه\s+\S+", _normalize(text))
    if len(moods) >= 2 and pair:
        rest = _normalize(text).replace(pair.group(0), " ")
        _, genres2, exclude2 = detect_smart(rest)
        return ["neutral"], genres2, exclude2
    negated = has_negation(text)
    if (moods or genres) and not negated and len(moods) < 2:
        return moods, genres, []
    if not moods and not genres and is_greeting(text):
        return [], [], []

    if len(moods) > 1 and "happy" in moods:
        moods = [x for x in moods if x != "happy"]
    excluded = find_excluded(text, genres, moods)
    fallback = (_target_moods(moods, excluded), [g for g in genres if g not in excluded], excluded)

    messages = [{"role": "system", "content": CLASSIFY_PROMPT},
                {"role": "user", "content": _after_correction(text)}]
    answer = llm.chat(messages, None, max_wait=6)
    found = re.search(r"\{.*\}", answer or "", re.S)
    if not found:
        return fallback
    try:
        data = json.loads(found.group(0))
    except ValueError:
        return fallback
    new_moods = [x for x in data.get("moods", []) if x in MOOD_WORDS]
    new_genres = [x for x in data.get("genres", []) if x in GENRE_WORDS]
    new_excl = [x for x in data.get("exclude_genres", []) if x in GENRE_WORDS]
    new_excl += [x for x in data.get("exclude_moods", []) if x in MOOD_WORDS]
    new_genres = [g for g in new_genres if g not in new_excl]
    if not (new_moods or new_genres or new_excl):
        return fallback if (moods or genres) else ([], [], [])
    return _target_moods(new_moods, new_excl), new_genres, new_excl


if __name__ == "__main__":
    for s in ["امروز خیلی غمگینم", "عصبانی‌ام و اکشن می‌خوام", "یه انیمیشن شاد پیشنهاد بده", "سلام"]:
        print(s, "->", detect(s))
