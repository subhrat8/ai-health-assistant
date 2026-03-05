const bubble = document.getElementById("chat-bubble")
const box = document.getElementById("chat-box")
const input = document.getElementById("chat-input")
const chatBody = document.getElementById("chat-body")

bubble.onclick = () => {

    box.style.display =
        box.style.display === "flex" ? "none" : "flex"
}

function sendMessage(){

    const message = input.value.trim()

    if(!message) return

    addUserMessage(message)

    input.value = ""

    fetch("/chat",{
        method:"POST",
        headers:{
            "Content-Type":"application/json"
        },
        body:JSON.stringify({message:message})
    })
    .then(res=>res.json())
    .then(data=>{
        addBotMessage(data.reply)
    })
}

function addUserMessage(msg){

    const div = document.createElement("div")

    div.className = "user-msg"

    div.innerText = msg

    chatBody.appendChild(div)

}

function addBotMessage(msg){

    const div = document.createElement("div")

    div.className = "bot-msg"

    div.innerText = msg

    chatBody.appendChild(div)

    chatBody.scrollTop = chatBody.scrollHeight
}
