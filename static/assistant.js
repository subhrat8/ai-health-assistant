document.addEventListener("DOMContentLoaded", function () {

const bubble = document.getElementById("chat-bubble")
const box = document.getElementById("chat-box")
const input = document.getElementById("chat-input")
const chatBody = document.getElementById("chat-body")

/* If chat elements do not exist, stop */
if (!bubble || !box || !input || !chatBody) return


/* ---------------- CHAT TOGGLE ---------------- */

bubble.addEventListener("click", function(){

if(box.style.display === "flex"){
box.style.display = "none"
}
else{
box.style.display = "flex"
}

})


/* ---------------- SEND MESSAGE ---------------- */

window.sendMessage = function(){

const message = input.value.trim()

if(!message) return

addUserMessage(message)

input.value = ""

fetch("/chat", {

method:"POST",

headers:{
"Content-Type":"application/json"
},

body:JSON.stringify({

message:message,

healthData:window.healthData || null,
hospitals:window.hospitals || null

})

})

.then(res => res.json())

.then(data => {

addBotMessage(data.reply)

})

.catch(err => {

addBotMessage("Sorry, I couldn't reach the assistant.")

})

}


/* ---------------- USER MESSAGE ---------------- */

function addUserMessage(msg){

const div = document.createElement("div")

div.className = "user-msg"

div.innerText = msg

chatBody.appendChild(div)

chatBody.scrollTop = chatBody.scrollHeight

}


/* ---------------- BOT MESSAGE ---------------- */

function addBotMessage(msg){

const div = document.createElement("div")

div.className = "bot-msg"

div.innerText = msg

chatBody.appendChild(div)

chatBody.scrollTop = chatBody.scrollHeight

}


/* ---------------- ENTER KEY SEND ---------------- */

input.addEventListener("keypress", function(e){

if(e.key === "Enter"){
sendMessage()
}

})

})
