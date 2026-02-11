// When user clicks chatbox send button, save user input value in variable
const chatButton = document.getElementById("chatbot-button");
chatButton.addEventListener("click", async function () {
  const userInput = document.getElementById("input").value;
  const message_box = document.getElementById("messages");

  // Clear chatbot input and message box
  document.getElementById("input").value = "";
  document.getElementById("messages").textContent = "";

  // Lock chatbot button
  chatButton.disabled = true;
  chatButton.classList.add("loading");

  // Post user input value to /api/llm endpoint in app.py
  const response = await fetch("/api/llm", {
    method: "POST",
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json"
    },
    credentials: "same-origin",
    body: JSON.stringify({ prompt: userInput })
  });

  // Wait and hold data in data variable
  const data = await response.json();
  console.log(data);

  // Create type writer effect, reference: https://www.w3schools.com/howto/howto_js_typewriter.asp
  let i = 0;
  let txt = data.response;
  let speed = 15; // Set speed

  // Recursion: Call function to append one character to chatbox every time the timeout resets 
  function typeWriter() {
    if (i < txt.length) {
      message_box.innerHTML += txt.charAt(i);
      i++;
      setTimeout(typeWriter, speed);
    } else {
      chatButton.disabled = false;
      chatButton.classList.remove("loading");
    }
  }

  typeWriter()
});