document.addEventListener("DOMContentLoaded", () => {

    // Typing effect
    const textEl = document.getElementById("assistant-text");
    if (textEl) {
        const text = textEl.innerText;
        textEl.innerText = "";
        let i = 0;
        const type = () => {
            if (i < text.length) {
                textEl.innerText += text.charAt(i++);
                setTimeout(type, 20);
            }
        };
        type();
    }

    // Dark mode
    const darkToggle = document.getElementById("darkToggle");
    if (localStorage.getItem("dark") === "true") {
        document.body.classList.add("dark");
    }

    darkToggle.onclick = () => {
        document.body.classList.toggle("dark");
        localStorage.setItem("dark", document.body.classList.contains("dark"));
    };

    // Voice speak
    document.getElementById("speakBtn").onclick = () => {
        const msg = new SpeechSynthesisUtterance(textEl.innerText);
        speechSynthesis.speak(msg);
    };

    // Floating chat
    const bubble = document.getElementById("chat-bubble");
    const box = document.getElementById("chat-box");
    bubble.onclick = () => box.classList.toggle("open");
});

function sendMessage() {
    const input = document.getElementById("chat-input");
    const body = document.getElementById("chat-body");
    if (!input.value) return;

    body.innerHTML += `<div class="user-msg">${input.value}</div>`;
    body.innerHTML += `<div class="bot-msg">I’m here to help 🙂. This assistant helps with site usage and guidance.</div>`;
    input.value = "";
}
