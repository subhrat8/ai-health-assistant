// ===== DARK MODE =====
const toggle = document.getElementById("dark-toggle");
toggle.onclick = () => {
    document.body.classList.toggle("dark");
    localStorage.setItem("dark", document.body.classList.contains("dark"));
};

if (localStorage.getItem("dark") === "true") {
    document.body.classList.add("dark");
}

// ===== VOICE SPEAK =====
document.getElementById("speak-btn").onclick = () => {
    const text = document.getElementById("assistant-text").innerText;
    const msg = new SpeechSynthesisUtterance(text);
    speechSynthesis.speak(msg);
};

// ===== CHAT TOGGLE =====
const bubble = document.getElementById("chat-bubble");
const box = document.getElementById("chat-box");

bubble.onclick = () => box.classList.toggle("open");

// ===== CHAT SEND =====
function sendMessage() {
    const input = document.getElementById("chat-input");
    const body = document.getElementById("chat-body");

    if (!input.value.trim()) return;

    body.innerHTML += `<div class="user-msg">${input.value}</div>`;

    fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message: input.value})
    })
    .then(res => res.json())
    .then(data => {
        body.innerHTML += `<div class="bot-msg">${data.reply}</div>`;
        body.scrollTop = body.scrollHeight;
    });

    input.value = "";
}
