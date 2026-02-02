// ---------- DARK MODE ----------
const darkToggle = document.getElementById("dark-toggle");
if (darkToggle) {
    darkToggle.onclick = () => {
        document.body.classList.toggle("dark");
        localStorage.setItem(
            "theme",
            document.body.classList.contains("dark") ? "dark" : "light"
        );
    };

    if (localStorage.getItem("theme") === "dark") {
        document.body.classList.add("dark");
    }
}

// ---------- VOICE SPEAK ----------
const speakBtn = document.getElementById("speak-btn");
if (speakBtn) {
    speakBtn.onclick = () => {
        const text = document.getElementById("assistant-text")?.innerText;
        if (!text) return;

        const utter = new SpeechSynthesisUtterance(text);
        utter.rate = 0.95;
        utter.pitch = 1;
        speechSynthesis.cancel();
        speechSynthesis.speak(utter);
    };
}

// ---------- CHAT UI ----------
const bubble = document.getElementById("chat-bubble");
const box = document.getElementById("chat-box");

if (bubble && box) {
    bubble.onclick = () => box.classList.toggle("open");
}

// ---------- CHAT SEND ----------
function sendMessage() {
    const input = document.getElementById("chat-input");
    const body = document.getElementById("chat-body");

    if (!input.value.trim()) return;

    const userText = input.value;
    input.value = "";

    body.innerHTML += `<div class="user-msg">${userText}</div>`;
    body.scrollTop = body.scrollHeight;

    fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message: userText})
    })
    .then(res => res.json())
    .then(data => {
        body.innerHTML += `<div class="bot-msg">${data.reply}</div>`;
        body.scrollTop = body.scrollHeight;
    })
    .catch(() => {
        body.innerHTML += `<div class="bot-msg">⚠️ Unable to reply right now.</div>`;
    });
}
