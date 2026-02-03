// ================= SPEECH =================
let synth = window.speechSynthesis;

function speak(text) {
    if (!text) return;
    synth.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 0.95;
    u.pitch = 1;
    synth.speak(u);
}

// ================= DARK MODE =================
const darkToggle = document.getElementById("dark-toggle");
if (darkToggle) {
    darkToggle.onclick = () => {
        document.body.classList.toggle("dark");
        localStorage.setItem("dark", document.body.classList.contains("dark"));
    };
    if (localStorage.getItem("dark") === "true") {
        document.body.classList.add("dark");
    }
}

// ================= CHAT =================
const bubble = document.getElementById("chat-bubble");
const box = document.getElementById("chat-box");
const body = document.getElementById("chat-body");
const input = document.getElementById("chat-input");

if (bubble) bubble.onclick = () => box.classList.toggle("open");

function addMsg(text, type) {
    const d = document.createElement("div");
    d.className = type === "user" ? "user-msg" : "bot-msg";
    d.innerText = text;
    body.appendChild(d);
    body.scrollTop = body.scrollHeight;
    if (type === "bot") speak(text);
}

function sendMessage() {
    const t = input.value.trim();
    if (!t) return;
    addMsg(t, "user");
    input.value = "";

    fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message: t})
    })
    .then(r => r.json())
    .then(d => addMsg(d.reply, "bot"))
    .catch(() => addMsg("Service unavailable.", "bot"));
}
