// Éléments DOM
const messagesContainer = document.getElementById("messages-container");
const messageForm = document.getElementById("message-form");
const messageInput = document.getElementById("message-input");
const toastContainer = document.getElementById("toast-container");

// État de connexion SSE
let eventSource = null;
let isConnected = false;

// Formater l'heure
function formatTime(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Créer un élément message
function createMessageElement(msg) {
  const isOwnMessage = msg.username === username;
  const chatDiv = document.createElement("div");
  chatDiv.className = `chat ${isOwnMessage ? "chat-end" : "chat-start"}`;

  chatDiv.innerHTML = `
        <div class="chat-image">
          <img src="${msg.avatar}" alt="" class="size-10 rounded-full">
        </div>
        <div class="chat-header">
            ${msg.username}
            ${
              msg.is_bot
                ? '<span class="badge badge-primary badge-sm ml-1">Bot</span>'
                : ""
            }
            <time class="text-xs opacity-50 ml-1">${formatTime(
              msg.timestamp
            )}</time>
        </div>
        <div class="chat-bubble ${msg.is_bot ? "chat-bubble-accent" : ""}">
            ${escapeHtml(msg.message)}
        </div>
    `;

  return chatDiv;
}

// Échapper le HTML
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Ajouter un message au conteneur
function addMessage(msg) {
  const messageElement = createMessageElement(msg);
  messagesContainer.appendChild(messageElement);
  scrollToBottom();
}

// Défiler vers le bas
function scrollToBottom() {
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Afficher un toast
function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `alert alert-${type} shadow-lg`;
  toast.innerHTML = `
        <div>
            <span>${message}</span>
        </div>
    `;

  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, 3000);
}

// Envoyer un message
async function sendMessage(message) {
  try {
    const response = await fetch("/api/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        username: username,
        avatar: avatar,
        message: message,
      }),
    });

    if (!response.ok) {
      throw new Error("Erreur lors de l'envoi du message");
    }

    messageInput.value = "";
  } catch (error) {
    console.error("Erreur:", error);
    showToast("Impossible d'envoyer le message", "error");
  }
}

// Connexion SSE
function connectSSE() {
  if (eventSource) {
    eventSource.close();
  }

  eventSource = new EventSource("/api/stream");

  eventSource.onopen = () => {
    isConnected = true;
    console.log("Connexion SSE établie");
  };

  eventSource.addEventListener("message", (event) => {
    try {
      const msg = JSON.parse(event.data);
      addMessage(msg);

      // Afficher un toast si c'est un nouveau message d'un autre utilisateur
      if (msg.username !== username && !msg.is_bot) {
        showToast(`${msg.username} a envoyé un message`, "info");
      }
    } catch (error) {
      console.error("Erreur de parsing:", error);
    }
  });

  eventSource.onerror = (error) => {
    console.error("Erreur SSE:", error);
    isConnected = false;

    // Reconnecter après 5 secondes
    setTimeout(() => {
      if (!isConnected) {
        connectSSE();
      }
    }, 5000);
  };
}

// Gestionnaire de soumission du formulaire
messageForm.addEventListener("submit", (e) => {
  e.preventDefault();

  const message = messageInput.value.trim();

  if (message) {
    sendMessage(message);
  }
});

// Initialisation
document.addEventListener("DOMContentLoaded", () => {
  scrollToBottom();
  connectSSE();
  messageInput.focus();

  showToast(`Bienvenue ${username} ! 👋`, "success");
});

// Nettoyage à la fermeture
window.addEventListener("beforeunload", () => {
  if (eventSource) {
    eventSource.close();
  }
});
