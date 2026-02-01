const bubble = document.getElementById("chat-bubble");
const box = document.getElementById("chat-box");

bubble.addEventListener("click", () => {
    box.classList.toggle("open");
});

function sendMessage() {
    const input = document.getElementById("chat-input");
    const body = document.getElementById("chat-body");

    if (input.value.trim() === "") return;

    const userMsg = document.createElement("div");
    userMsg.className = "user-msg";
    userMsg.innerText = input.value;
    body.appendChild(userMsg);

    const botMsg = document.createElement("div");
    botMsg.className = "bot-msg";
    botMsg.innerText =
        "I can help explain your results or guide you on next steps. For medical emergencies, please visit a hospital immediately.";
    body.appendChild(botMsg);

    input.value = "";
    body.scrollTop = body.scrollHeight;
}
