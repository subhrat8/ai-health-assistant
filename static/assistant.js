document.addEventListener("DOMContentLoaded", () => {

    // Typing effect for main AI text
    const textElement = document.getElementById("assistant-text");
    if (textElement) {
        const text = textElement.innerText;
        textElement.innerText = "";
        let i = 0;
        function type() {
            if (i < text.length) {
                textElement.innerText += text.charAt(i);
                i++;
                setTimeout(type, 20);
            }
        }
        type();
    }

    // Chat toggle
    const bubble = document.getElementById("chat-bubble");
    const box = document.getElementById("chat-box");

    bubble.onclick = () => {
        box.classList.toggle("open");
    };
});

function sendMessage() {
    const input = document.getElementById("chat-input");
    const body = document.getElementById("chat-body");
    if (!input.value.trim()) return;

    const userMsg = document.createElement("div");
    userMsg.className = "user-msg";
    userMsg.innerText = input.value;
    body.appendChild(userMsg);

    const botMsg = document.createElement("div");
    botMsg.className = "bot-msg";
    botMsg.innerText = "Thanks! This assistant is currently for guidance only. Medical analysis is shown above.";
    body.appendChild(botMsg);

    body.scrollTop = body.scrollHeight;
    input.value = "";
}
