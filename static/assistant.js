document.addEventListener("DOMContentLoaded", function () {
    const textElement = document.getElementById("assistant-text");

    if (!textElement) return;

    const text = textElement.innerText;
    textElement.innerText = "";

    let index = 0;

    function typeEffect() {
        if (index < text.length) {
            textElement.innerText += text.charAt(index);
            index++;
            setTimeout(typeEffect, 25);
        }
    }

    typeEffect();
});
