document.addEventListener("DOMContentLoaded", function () {

    const textElement = document.getElementById("assistant-text");
    if (!textElement) return;

    const fullText = textElement.innerText.trim();
    textElement.innerText = "";

    let index = 0;

    function typeEffect() {
        if (index < fullText.length) {
            textElement.innerText += fullText.charAt(index);
            index++;
            setTimeout(typeEffect, 18);
        }
    }

    typeEffect();
});
