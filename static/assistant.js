// ================= SAFE DOM READY =================
document.addEventListener("DOMContentLoaded", () => {

    // ---------- ELEMENTS ----------
    const chatBubble = document.getElementById("chat-bubble");
    const chatBox = document.getElementById("chat-box");
    const chatBody = document.getElementById("chat-body");
    const chatInput = document.getElementById("chat-input");
    const darkToggle = document.getElementById("dark-toggle");
    const speakBtn = document.getElementById("speak-btn");
    const assistantText = document.getElementById("assistant-text");

    // ---------- SPEECH ----------
    const synth = window.speechSynthesis;

    function speakText(text) {
        if (!text || !synth) return;
        synth.cancel();
        const utter = new SpeechSynthesisUtterance(text);
        utter.rate = 0.95;
        utter.pitch = 1;
        synth.speak(utter);
    }

    // ---------- DARK MODE ----------
    if (darkToggle) {
        if (localStorage.getItem("darkMode") === "true") {
            document.body.classList.add("dark");
        }
        darkToggle.onclick = () => {
            document.body.classList.toggle("dark");
            localStorage.setItem(
                "darkMode",
                document.body.classList.contains("dark")
            );
        };
    }

    // ---------- READ RESULT ----------
    if (speakBtn && assistantText) {
        speakBtn.onclick = () => speakText(assistantText.innerText);
    }

    // ---------- CHAT OPEN ----------
    if (chatBubble && chatBox) {
        chatBubble.onclick = () => {
            chatBox.classList.toggle("open");
            if (chatBody.children.length === 0) {
                addMessage(
                    "Hi 👋 I’m MedAssist.\n\nI can:\n• Explain your results\n• Suggest next steps\n• Share general health info\n\nAsk me anything.",
                    "bot"
                );
            }
        };
    }

    // ---------- ADD MESSAGE ----------
    function addMessage(text, sender) {
        const msg = document.createElement("div");
        msg.className = sender === "user" ? "user-msg" : "bot-msg";
        msg.innerText = text;
        chatBody.appendChild(msg);
        chatBody.scrollTop = chatBody.scrollHeight;

        if (sender === "bot") {
            speakText(text);
        }
    }

    // ---------- SEND MESSAGE ----------
    window.sendMessage = function () {
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
            addMessage(
                data.reply || "I’m here to help. Please try again.",
                "bot"
            );
        })
        .catch(() => {
            addMessage(
                "⚠️ Service temporarily unavailable. Please try again.",
                "bot"
            );
        });
    };

    // ---------- ENTER KEY ----------
    if (chatInput) {
        chatInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") {
                sendMessage();
            }
        });
    }

});
