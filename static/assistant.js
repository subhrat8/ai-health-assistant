// ================= TEXT TO SPEECH =================
let synth = window.speechSynthesis;
let currentUtterance = null;

function speakText(text) {
    if (!text || !synth) return;

    // Stop previous speech
    if (synth.speaking) {
        synth.cancel();
    }

    currentUtterance = new SpeechSynthesisUtterance(text);

    // Voice tuning (safe & calm)
    currentUtterance.rate = 0.95;
    currentUtterance.pitch = 1;
    currentUtterance.volume = 1;

    // Prefer English voice
    const voices = synth.getVoices();
    const englishVoice = voices.find(v => v.lang.startsWith("en"));
    if (englishVoice) currentUtterance.voice = englishVoice;

    synth.speak(currentUtterance);
}

// ================= READ RESULT PAGE =================
document.addEventListener("DOMContentLoaded", () => {
    const speakBtn = document.getElementById("speak-btn");
    const assistantText = document.getElementById("assistant-text");

    if (speakBtn && assistantText) {
        speakBtn.addEventListener("click", () => {
            speakText(assistantText.innerText);
        });
    }
});

// ================= DARK MODE =================
const darkToggle = document.getElementById("dark-toggle");
if (darkToggle) {
    darkToggle.onclick = () => {
        document.body.classList.toggle("dark");
        localStorage.setItem(
            "darkMode",
            document.body.classList.contains("dark")
        );
    };

    if (localStorage.getItem("darkMode") === "true") {
        document.body.classList.add("dark");
    }
}

// ================= CHAT UI =================
const chatBubble = document.getElementById("chat-bubble");
const chatBox = document.getElementById("chat-box");
const chatBody = document.getElementById("chat-body");
const chatInput = document.getElementById("chat-input");

if (chatBubble) {
    chatBubble.onclick = () => {
        chatBox.classList.toggle("open");
    };
}

function addMessage(text, sender) {
    const msg = document.createElement("div");
    msg.className = sender === "user" ? "user-msg" : "bot-msg";
    msg.innerText = text;
    chatBody.appendChild(msg);
    chatBody.scrollTop = chatBody.scrollHeight;

    // 🔊 Speak bot replies automatically
    if (sender === "bot") {
        speakText(text);
    }
}

// ================= SEND MESSAGE =================
function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;

    addMessage(text, "user");
    chatInput.value = "";

    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text })
    })
    .then(res => res.json())
    .then(data => {
        addMessage(data.reply || "Sorry, I couldn’t respond.", "bot");
    })
    .catch(() => {
        addMessage("Service unavailable. Please try again.", "bot");
    });
}
