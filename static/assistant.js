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
