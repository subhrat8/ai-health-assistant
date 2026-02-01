// ===== Floating assistant =====
const bubble = document.getElementById("chat-bubble");
const box = document.getElementById("chat-box");

if (bubble) {
  bubble.onclick = () => box.classList.toggle("open");
}

// ===== Voice speak =====
function speak(text){
    const msg = new SpeechSynthesisUtterance(text);
    msg.rate = 0.95;
    speechSynthesis.speak(msg);
}

// ===== Save history =====
function saveHistory(data){
    let h = JSON.parse(localStorage.getItem("history") || "[]");
    h.unshift(data);
    localStorage.setItem("history", JSON.stringify(h.slice(0,5)));
}

// ===== Type animation =====
const el = document.getElementById("assistant-text");
if(el){
    const txt = el.innerText;
    el.innerText = "";
    let i=0;
    function t(){
        if(i<txt.length){
            el.innerText += txt[i++];
            setTimeout(t,20);
        }
    }
    t();
    speak(txt);
    saveHistory(txt);
}
