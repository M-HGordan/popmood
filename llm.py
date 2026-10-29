"""Step 8 | LLM access layer: provider chain (cloud models, local Ollama, local text), model racing, optional streaming and warm-up."""
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from openai import OpenAI
from config import API_KEY, BASE_URL, MODELS, OLLAMA_MODEL, OLLAMA_URL, STREAM, RACE


LAST = {}  # winning model and timings of the latest call, for debugging


_clients = {}  # one cached client per endpoint, avoids repeated TLS handshakes


def _client(api_key, base_url):
    """Return a cached OpenAI-compatible client for the given endpoint."""
    k = (api_key, base_url)
    if k not in _clients:
        _clients[k] = OpenAI(api_key=api_key, base_url=base_url, max_retries=0)
    return _clients[k]


def _call(api_key, base_url, model, messages, timeout=30):
    """One chat-completion call to a single provider."""
    r = _client(api_key, base_url).chat.completions.create(model=model, messages=messages, timeout=timeout)
    return r.choices[0].message.content


def warm_up():
    """Open connections to the cloud models in the background to avoid cold-start latency."""
    cloud = [p for p in _providers() if p[1] == BASE_URL]

    def ping(p):
        """Send a tiny request to one provider."""
        key, url, model, timeout = p
        try:
            _call(key, url, model, [{"role": "user", "content": "hi"}], 20)
            print(f"🔥 {model} آماده شد")
        except Exception as e:
            print(f"⚠️ گرم کردن {model} ناموفق بود: {str(e)[:80]}")

    if cloud:
        with ThreadPoolExecutor(max_workers=len(cloud)) as pool:
            list(pool.map(ping, cloud))


def _providers():
    """Ordered list of (key, base_url, model, timeout) to try."""
    items = []
    if API_KEY and BASE_URL:
        items += [(API_KEY, BASE_URL, m, 30) for m in MODELS]
    else:
        print("⚠️ GAPGPT_API_KEY یا GAPGPT_BASE_URL خالیه؛ فایل .env رو چک کن")
    if OLLAMA_MODEL:
        items.append(("ollama", OLLAMA_URL, OLLAMA_MODEL, 60))
    return items


def _race(providers, messages, max_wait):
    """Call the first two cloud models in parallel and return the fastest successful answer."""
    pool = ThreadPoolExecutor(max_workers=len(providers))
    t0 = time.time()
    futures = {pool.submit(_call, key, url, model, messages, min(timeout, max_wait or timeout)): model
               for key, url, model, timeout in providers}
    pending = set(futures)
    while pending:
        done, pending = wait(pending, return_when=FIRST_COMPLETED)
        for f in done:
            try:
                out = f.result()
            except Exception as e:
                print(f"خطا در مدل {futures[f]}: {e}")
                continue
            LAST.update(model=futures[f], first=round(time.time() - t0, 1))
            print(f"🏁 برنده: {futures[f]} بعد از {time.time() - t0:.1f} ثانیه")
            pool.shutdown(wait=False, cancel_futures=True)
            return out
    pool.shutdown(wait=False)
    return None


def chat(messages, local_text, max_wait=None):
    """Return the reply text, trying providers in order within an optional total time budget; falls back to local_text."""
    start = time.time()
    providers = _providers()
    cloud = [p for p in providers if p[1] == BASE_URL]
    if RACE and len(cloud) >= 2:
        out = _race(cloud[:2], messages, max_wait)
        if out is not None:
            return out
        providers = [p for p in providers if p not in cloud[:2]]
    for key, url, model, timeout in providers:
        left = (max_wait - (time.time() - start)) if max_wait else None
        if left is not None and left <= 0.5:
            break
        t0 = time.time()
        try:
            out = _call(key, url, model, messages, min(timeout, left or timeout))
            LAST.update(model=model, first=round(time.time() - t0, 1))
            print(f"⏱ {model}: {time.time() - t0:.1f} ثانیه")
            return out
        except Exception as e:
            print(f"خطا در مدل {model}، میرم سراغ بعدی: {e}")
    print("⚠️ هیچ LLM‌ای جواب نداد؛ جواب محلی استفاده شد")
    return local_text


def chat_stream(messages, local_text):
    """Yield the reply progressively (word by word) using the same provider chain."""
    if not STREAM:
        yield chat(messages, local_text)
        return
    for key, url, model, timeout in _providers():
        got = False
        t0 = time.time()
        try:
            stream = _client(key, url).chat.completions.create(
                model=model, messages=messages, stream=True, timeout=timeout)
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    if not got:
                        LAST.update(model=model, first=round(time.time() - t0, 1))
                        print(f"⏱ {model}: اولین کلمه بعد از {time.time() - t0:.1f} ثانیه")
                    got = True
                    yield chunk.choices[0].delta.content
            if got:
                return
        except Exception as e:
            if got:
                return
            print(f"خطا در مدل {model}، میرم سراغ بعدی: {e}")
    print("⚠️ هیچ LLM‌ای جواب نداد؛ جواب محلی استفاده شد")
    yield local_text
