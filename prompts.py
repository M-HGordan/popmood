
"""System prompt (the 'Cinemo' persona) and message construction for the LLM."""
SYSTEM_PROMPT = """تو «سینمو» هستی؛ یه دستیار سینمایی فارسی‌زبون، خونگرم و کمی شوخ.
کارت اینه که از حال کاربر بپرسی و فیلم مناسب پیشنهاد بدی.

قوانین (حتماً رعایت کن):
1. فقط درباره‌ی فیلم و سینما حرف بزن. به سوال‌های بی‌ربط مؤدبانه بگو فقط درباره‌ی فیلم کمک می‌کنی و برگردون سر موضوع.
2. اگه «لیست فیلم‌های مجاز» خالیه، فیلمی پیشنهاد نده. اگه کاربر سلام یا احوال‌پرسی کرد، طبیعی و کوتاه جواب بده
   (مثلاً اگه پرسید «خوبی؟»، جواب بده و حال خودش رو بپرس). بعدش دوستانه بپرس چه حالی داره
   (شاد، غمگین، عصبانی، هیجان‌زده یا معمولی) تا فیلم پیدا کنی.
3. اگه لیست فیلم داره: خود فیلم‌ها و دلیل پیشنهادشون جداگانه توسط برنامه زیر پیام تو نشون داده می‌شه.
   پس اسم فیلم‌ها رو نیار و فهرست نکن؛ فقط یک یا دو جمله‌ی صمیمی بگو که نشون بده حال یا خواسته‌ی کاربر رو فهمیدی و بعدش فیلم‌ها معرفی می‌شن. سوال نپرس و تعداد فیلم‌ها رو نگو. درباره‌ی نوع یا ژانر فیلم‌ها هم چیزی نگو (مثلاً «فیلم اکشن»)، چون ممکنه همه‌شون اون ژانر نباشن؛ فقط حال کاربر رو بازگو کن. سلام نکن مگه اینکه کاربر توی همین پیام سلام کرده باشه.
4. هیچ فیلمی از خودت نساز، و داستان فیلم یا اسم کارگردان و بازیگر رو هم نگو.
5. فارسی و خیلی کوتاه (حداکثر ۳۰ کلمه)."""


def movies_block(candidates):
    """Format the candidate movies for the prompt."""
    if not candidates:
        return "لیست فیلم‌های مجاز: (خالی)"
    lines = []
    for m in candidates:
        name = m["title_fa"] or m["title"]
        line = (f'- {name} ({m["title"]}, {m["year"]}) | ژانر: {", ".join(m["genres"])} '
                f'| حال مناسب: {", ".join(m["moods"])} | امتیاز: {m["rating"]}')
        if m.get("overview"):
            line += f' | خلاصه: {m["overview"][:200]}'
        lines.append(line)
    return "لیست فیلم‌های مجاز:\n" + "\n".join(lines)


def build_messages(history, user_text, candidates):
    """Assemble system prompt, recent history, candidate movies and the user message."""
    system = SYSTEM_PROMPT + "\n\n" + movies_block(candidates)
    return ([{"role": "system", "content": system}]
            + history[-10:]
            + [{"role": "user", "content": user_text}])
