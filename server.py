"""Step 10 | Local Flask server: serves the web UI and exposes the chat and contract endpoints."""
import json
import threading
import webbrowser
from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context
import chatbot
import llm

app = Flask(__name__, static_folder="web", static_url_path="")
sessions = {}


def _session(sid):
    """Get or create the session of a browser id."""
    if sid not in sessions:
        sessions[sid] = chatbot.new_session()
    return sessions[sid]


@app.get("/")
def home():
    """Serve the single-page UI."""
    return send_from_directory("web", "index.html")


@app.post("/api/chat")
def api_chat():
    """Chat endpoint: full response (cards, text, contract) in one JSON."""
    data = request.get_json(force=True)
    text = (data.get("message") or "").strip()
    if not text:
        return jsonify({"error": "پیام خالیه"}), 400
    result = chatbot.respond(text, _session(data.get("session", "default")))
    result["contract"] = chatbot.contract_output(result)
    return jsonify(result)


@app.post("/api/chat_stream")
def api_chat_stream():
    """Chat endpoint streaming NDJSON events so the UI can show text word by word."""
    data = request.get_json(force=True)
    text = (data.get("message") or "").strip()
    if not text:
        return jsonify({"error": "پیام خالیه"}), 400
    session = _session(data.get("session", "default"))

    def lines():
        for event in chatbot.respond_stream(text, session):
            yield json.dumps(event, ensure_ascii=False) + "\n"

    return Response(stream_with_context(lines()), mimetype="application/x-ndjson")


@app.post("/api/recommend")
def api_recommend():
    """Pure shared-contract output for other challenge sections."""
    data = request.get_json(force=True)
    result = chatbot.respond(data.get("message", ""), chatbot.new_session())
    return jsonify(chatbot.contract_output(result))


@app.post("/api/reset")
def api_reset():
    """Forget the session of a browser id."""
    sessions.pop(request.get_json(force=True).get("session", "default"), None)
    return jsonify({"ok": True})


if __name__ == "__main__":
    threading.Thread(target=llm.warm_up, daemon=True).start()
    threading.Timer(1.2, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(port=5000)
