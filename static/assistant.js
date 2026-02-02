// ================= FLOATING CHAT =================
const chatBubble = document.getElementById("chat-bubble");
const chatBox = document.getElementById("chat-box");
const chatBody = document.getElementById("chat-body");
const chatInput = document.getElementById("chat-input");

// Toggle chat window
chatBubble.addEventListener("click", () => {
    chatBox.classList.toggle("open");
});

// ================= SEND MESSAGE =================
function sendMessage() {
    const msg = chatInput.value.trim();
    if (!msg) return;

    appendUser(msg);
    chatInput.value = "";

    showTyping();

    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg })
    })
    .then(res => res.json())
    .then(data => {
        removeTyping();
        typeBot(data.reply || "Sorry, I couldn’t understand that.");
    })
    .catch(() => {
        removeTyping();
        typeBot("⚠️ Assistant is temporarily unavailable.");
    });
}

// ================= UI HELPERS =================
function appendUser(text) {
    const div = document.createElement("div");
    div.className = "user-msg";
    div.innerText = text;
    chatBody.appendChild(div);
    chatBody.scrollTop = chatBody.scrollHeight;
}

function typeBot(text) {
    const div = document.createElement("div");
    div.className = "bot-msg";
    chatBody.appendChild(div);

    let i = 0;
    const typing = setInterval(() => {
        div.innerText += text.charAt(i);
        i++;
        chatBody.scrollTop = chatBody.scrollHeight;
        if (i >= text.length) clearInterval(typing);
    }, 20);
}

function showTyping() {
    const div = document.createElement("div");
    div.className = "bot-msg";
    div.id = "typing";
    div.innerText = "Typing...";
    chatBody.appendChild(div);
    chatBody.scrollTop = chatBody.scrollHeight;
}

function removeTyping() {
    const typing = document.getElementById("typing");
    if (typing) typing.remove();
}

// ================= DARK MODE =================
const darkBtn = document.getElementById("dark-toggle");

if (darkBtn) {
    darkBtn.addEventListener("click", () => {
        document.body.classList.toggle("dark");
        localStorage.setItem(
            "darkMode",
            document.body.classList.contains("dark")
        );
    });

    // Restore preference
    if (localStorage.getItem("darkMode") === "true") {
        document.body.classList.add("dark");
    }
}

// ================= VOICE SPEAK =================
const speakBtn = document.getElementById("speak-btn");

if (speakBtn) {
    speakBtn.addEventListener("click", () => {
        const text = document.getElementById("assistant-text")?.innerText;
        if (!text) return;

        const utter = new SpeechSynthesisUtterance(text);
        utter.rate = 0.95;
        utter.pitch = 1;
        speechSynthesis.speak(utter);
    });
}
