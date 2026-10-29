// PopMood front end: chat, mood buttons, movie cards, current-mood panel. Talks to server.py via /api/chat_stream.

const EMOJI = { happy: "☀️", sad: "🌧️", angry: "🔥", surprise: "✨", neutral: "🎞️" };
const MOOD_FA = { happy: "شاد", sad: "غمگین", angry: "عصبانی", surprise: "متعجب", neutral: "خنثی" };
const sessionId = "s" + Math.random().toString(36).slice(2);

const box = document.getElementById("messages");
const input = document.getElementById("input");

function addBubble(text, who) {
  const div = document.createElement("div");
  div.className = "bubble " + who;
  div.textContent = text;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

const MOOD_UI = {
  happy: ["😊", "شاد", "حال خوبته! بیا همین حس رو نگه داریم."],
  sad: ["😢", "غمگین", "اشکالی نداره؛ فیلم‌هایی کنارت می‌ذارم که همراهت باشن."],
  angry: ["😠", "عصبانی", "بیا با یه فیلم پرانرژی خالی‌ش کنیم."],
  surprise: ["🤩", "متعجب", "دنبال هیجان و غافلگیری‌ای؛ مغزت رو درگیر می‌کنیم."],
  neutral: ["😐", "خنثی", "یه حال معمولی؛ هر چی بخوای هست."],
};
const historyList = [];
function updateMood(mood) {
  const [e, name, note] = MOOD_UI[mood] || MOOD_UI.neutral;
  document.getElementById("moodEmoji").textContent = e;
  document.getElementById("moodName").textContent = name;
  document.getElementById("moodNote").textContent = note;
  historyList.unshift({ e, name, t: new Date().toLocaleTimeString("fa-IR", { hour: "2-digit", minute: "2-digit" }) });
  document.getElementById("history").innerHTML = historyList.slice(0, 4)
    .map(h => `<li><span>${h.e}</span>${h.name}<small>${h.t}</small></li>`).join("");
}

function showEmpty() {
  document.getElementById("cards").innerHTML =
    '<p class="hint">فیلم دیگه‌ای با این قیدها ندارم؛ یه قید رو شل کن یا حال دیگه‌ای بگو 🙂</p>';
}

function showCards(cards) {
  const wrap = document.getElementById("cards");
  if (!cards.length) return;
  wrap.innerHTML = "";
  cards.forEach((m, i) => {
    const name = m.title_fa || m.title;
    const mood = m.moods[0] || "neutral";
    const badges = m.moods.map(x => `<span class="badge ${x}">${MOOD_FA[x]}</span>`).join("");
    const art = m.poster ? `<img src="${m.poster}" alt="${name}" onerror="this.replaceWith(document.createTextNode('${EMOJI[mood]}'))">` : EMOJI[mood];
    wrap.insertAdjacentHTML("beforeend", `
      <div class="card" style="--i:${i}">
        <div class="poster p-${mood}">${art}</div>
        <div class="cbody">
          <h3>${name}</h3>
          <div class="meta">${m.title} · ${m.year} · <span class="rate">⭐ ${m.rating}</span></div>
          <div class="genres">${m.genres.join(" / ")}</div>
          ${badges}
          <div class="why">${m.why || ""}</div>
        </div>
      </div>`);
  });
}

async function send(text) {
  text = text.trim();
  if (!text) return;
  addBubble(text, "user");
  input.value = "";
  addBubble("...", "bot");
  const bubble = box.lastChild;
  bubble.innerHTML = '<span class="dots"><i></i><i></i><i></i></span>';
  let started = false;

  function handle(ev) {
    if (ev.type === "meta") {
      showCards(ev.cards);
      document.getElementById("contract").textContent = JSON.stringify(ev.contract);
      if (ev.cards.length) { document.body.dataset.mood = ev.contract.mood; updateMood(ev.contract.mood); }
    } else if (ev.type === "delta") {
      if (!started) { bubble.textContent = ""; started = true; }
      bubble.textContent += ev.text;
      box.scrollTop = box.scrollHeight;
    } else if (ev.type === "done") {
      bubble.textContent = ev.reply;
      showCards(ev.cards);
      if (ev.route === "rag" && !ev.cards.length) showEmpty();
      document.getElementById("contract").textContent = JSON.stringify(ev.contract);
      box.scrollTop = box.scrollHeight;
    }
  }

  try {
    const res = await fetch("/api/chat_stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, session: sessionId }),
    });
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      lines.filter(l => l.trim()).forEach(l => handle(JSON.parse(l)));
    }
  } catch (e) {
    bubble.textContent = "اتصال به سرور برقرار نشد 😕";
  }
}

document.getElementById("send").onclick = () => send(input.value);
input.addEventListener("keydown", e => { if (e.key === "Enter") send(input.value); });
document.querySelectorAll("[data-text]").forEach(b => b.onclick = () => send(b.dataset.text));
document.getElementById("reset").onclick = async () => {
  await fetch("/api/reset", { method: "POST", headers: { "Content-Type": "application/json" },
                              body: JSON.stringify({ session: sessionId }) });
  delete document.body.dataset.mood;
  historyList.length = 0;
  document.getElementById("history").innerHTML = '<li class="hint">هنوز چیزی ثبت نشده</li>';
  document.getElementById("moodEmoji").textContent = "🙂"; document.getElementById("moodName").textContent = "هنوز نگفتی";
  document.getElementById("moodNote").textContent = "یکی از دکمه‌ها رو بزن یا برام بنویس.";
  box.innerHTML = '<div class="bubble bot">از نو شروع کردیم! حالت چطوره؟</div>';
  document.getElementById("cards").innerHTML = '<p class="hint">هنوز پیشنهادی نداریم</p>';
  document.getElementById("contract").textContent = "{ }";
};
