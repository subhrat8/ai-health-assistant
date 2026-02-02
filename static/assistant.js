// ================= CHAT =================
const bubble = document.getElementById("chat-bubble");
const box = document.getElementById("chat-box");
const body = document.getElementById("chat-body");

bubble.onclick = () => box.classList.toggle("open");

function sendMessage() {
    const input = document.getElementById("chat-input");
    const msg = input.value.trim();
    if (!msg) return;

    body.innerHTML += `<div class="user-msg">${msg}</div>`;
    input.value = "";

    fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message: msg})
    })
    .then(res => res.json())
    .then(data => {
        body.innerHTML += `<div class="bot-msg">${data.reply}</div>`;
        body.scrollTop = body.scrollHeight;
    });
}

// ================= DARK MODE =================
const toggle = document.getElementById("dark-toggle");

if (localStorage.getItem("darkMode") === "on") {
    document.body.classList.add("dark");
}

toggle.onclick = () => {
    document.body.classList.toggle("dark");
    localStorage.setItem(
        "darkMode",
        document.body.classList.contains("dark") ? "on" : "off"
    );
};

// ================= VOICE SPEAK =================
const speakBtn = document.getElementById("speak-btn");

speakBtn.onclick = () => {
    const text = document.getElementById("assistant-text").innerText;
    if (!text) return;

    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = "en-US";
    utter.rate = 0.95;
    window.speechSynthesis.speak(utter);
};
