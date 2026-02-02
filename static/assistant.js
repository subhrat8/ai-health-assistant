/* ================= TEXT TO SPEECH ================= */
let synth = window.speechSynthesis;

function speakText(text) {
    if (!text || !synth) return;
    synth.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.rate = 0.95;
    utter.pitch = 1;
    synth.speak(utter);
}

/* ================= READ RESULT ================= */
document.addEventListener("DOMContentLoaded", () => {
    const speakBtn = document.getElementById("speak-btn");
    const text = document.getElementById("assistant-text");

    if (speakBtn && text) {
        speakBtn.onclick = () => speakText(text.innerText);
    }

    // Dark mode persistence
    if (localStorage.getItem("darkMode") === "true") {
        document.body.classList.add("dark");
    }
});

/* ================= DARK MODE ================= */
const darkToggle = document.getElementById("dark-toggle");
if (darkToggle) {
    darkToggle.onclick = () => {
        document.body.classList.toggle("dark");
        localStorage.setItem(
            "darkMode",
            document.body.classList.contains("dark")
        );
    };
}

/* ================= CHAT ================= */
const chatBubble = document.getElementById("chat-bubble");
const chatBox = document.getElementById("chat-box");
const chatBody = document.getElementById("chat-body");
const chatInput = document.getElementById("chat-input");

if (chatBubble) {
    chatBubble.onclick = () => chatBox.classList.toggle("open");
}

function addMessage(text, sender) {
    const div = document.createElement("div");
    div.className = sender === "user" ? "user-msg" : "bot-msg";
    div.innerText = text;
    chatBody.appendChild(div);
    chatBody.scrollTop = chatBody.scrollHeight;

    if (sender === "bot") speakText(text);
}

function sendMessage() {
    const msg = chatInput.value.trim();
    if (!msg) return;

    addMessage(msg, "user");
    chatInput.value = "";

    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg })
    })
    .then(res => res.json())
    .then(data => addMessage(data.reply, "bot"))
    .catch(() => addMessage("Service unavailable.", "bot"));
}

/* ================= VOICE INPUT ================= */
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.onresult = e => {
        chatInput.value = e.results[0][0].transcript;
        sendMessage();
    };
}

function startVoice() {
    if (recognition) recognition.start();
}

/* ================= SORT ================= */
function sortPlaces() {
    const container = document.getElementById("places-container");
    const items = Array.from(container.querySelectorAll(".hospital"));
    const mode = document.getElementById("sortSelect").value;

    items.sort((a, b) => {
        if (mode === "distance") {
            return a.dataset.distance - b.dataset.distance;
        }
        return a.dataset.type.localeCompare(b.dataset.type);
    });

    items.forEach(el => container.appendChild(el));
}
