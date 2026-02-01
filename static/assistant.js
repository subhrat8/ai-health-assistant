document.addEventListener("DOMContentLoaded", () => {

    // TYPE EFFECT
    const text = document.getElementById("assistant-text");
    if (text) {
        const content = text.innerText;
        text.innerText = "";
        let i = 0;

        function type() {
            if (i < content.length) {
                text.innerText += content.charAt(i++);
                setTimeout(type, 18);
            }
        }
        type();
    }

    // VOICE SPEAK
    document.getElementById("speakBtn").onclick = () => {
        const msg = new SpeechSynthesisUtterance(
            document.getElementById("assistant-text").innerText
        );
        speechSynthesis.speak(msg);
    };

    // DARK MODE
    document.getElementById("darkToggle").onclick = () => {
        document.body.classList.toggle("dark");
    };

    // FLOATING ASSISTANT
    const box = document.getElementById("assistantBox");
    const panel = document.getElementById("assistantPanel");

    box.onclick = () => {
        panel.style.display =
            panel.style.display === "block" ? "none" : "block";
    };
});
