const form = document.getElementById("chatForm");
const input = document.getElementById("messageInput");
const messages = document.getElementById("messages");
const errorBox = document.getElementById("error");
const sendBtn = document.getElementById("sendBtn");

function bubble(text, cls, meta="") {
  const div = document.createElement("div");
  div.className = `bubble ${cls}`;
  div.textContent = text;
  if (meta) {
    const m = document.createElement("div");
    m.className = "meta";
    m.textContent = meta;
    div.appendChild(m);
  }
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

async function sendMessage(text) {
  errorBox.textContent = "";
  bubble(text, "user");
  sendBtn.disabled = true;
  input.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({message: text})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Request failed.");

    const confidence = `${(data.confidence * 100).toFixed(1)}% confidence`;
    bubble(data.response, "bot", `${data.intent} • ${confidence}`);
  } catch (err) {
    errorBox.textContent = err.message;
    bubble("I could not process that request. Please check the message or model setup.", "bot");
  } finally {
    sendBtn.disabled = false;
    input.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) {
    errorBox.textContent = "Please enter a support question.";
    return;
  }
  input.value = "";
  sendMessage(text);
});

document.querySelectorAll(".chips button").forEach(btn => {
  btn.addEventListener("click", () => {
    input.value = btn.dataset.text;
    input.focus();
  });
});
