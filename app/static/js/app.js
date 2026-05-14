const walletForm = document.getElementById("walletTopupForm");

document.querySelectorAll(".js-loading-form").forEach((form) => {
    form.addEventListener("submit", () => {
        const button = form.querySelector("button[type='submit'], button:not([type])");
        if (!button || button.disabled) {
            return;
        }
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = button.dataset.loadingText || "Please wait...";
        button.disabled = true;
    });
});

if (walletForm) {
    walletForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const amountInput = walletForm.querySelector("input[name='amount']");
        const button = walletForm.querySelector("button[type='submit']");
        const amount = amountInput.value;
        const key = walletForm.dataset.key;

        if (!key) {
            alert("Razorpay key is not configured.");
            if (button) {
                button.disabled = false;
                button.innerHTML = button.dataset.originalText || "Pay with Razorpay";
            }
            return;
        }

        const formData = new FormData();
        formData.append("amount", amount);

        const orderResponse = await fetch("/wallet/create-order", {
            method: "POST",
            body: formData
        });

        const order = await orderResponse.json();
        if (!orderResponse.ok) {
            alert(order.error || "Unable to create Razorpay order.");
            if (button) {
                button.disabled = false;
                button.innerHTML = button.dataset.originalText || "Pay with Razorpay";
            }
            return;
        }

        const options = {
            key,
            amount: order.amount,
            currency: order.currency,
            name: "ZipTask",
            description: "Wallet top-up",
            order_id: order.id,
            handler: async (response) => {
                const verifyResponse = await fetch("/wallet/verify-payment", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        razorpay_order_id: response.razorpay_order_id,
                        razorpay_payment_id: response.razorpay_payment_id,
                        razorpay_signature: response.razorpay_signature,
                        amount
                    })
                });
                const result = await verifyResponse.json();
                if (!verifyResponse.ok) {
                    alert(result.error || "Payment verification failed.");
                    if (button) {
                        button.disabled = false;
                        button.innerHTML = button.dataset.originalText || "Pay with Razorpay";
                    }
                    return;
                }
                window.location.reload();
            },
            modal: {
                ondismiss: () => {
                    if (button) {
                        button.disabled = false;
                        button.innerHTML = button.dataset.originalText || "Pay with Razorpay";
                    }
                }
            },
            theme: { color: "#6c2bd9" }
        };

        const checkout = new Razorpay(options);
        checkout.open();
    });
}

const chatMessages = document.getElementById("chatMessages");
const chatForm = document.getElementById("chatForm");
let lastChatId = 0;

function renderChatMessage(item) {
    const wrapper = document.createElement("div");
    wrapper.className = `message-bubble ${item.mine ? "mine" : ""}`;
    const card = document.createElement("div");
    card.className = "message-card";
    const meta = document.createElement("span");
    meta.className = "message-meta";
    meta.textContent = `${item.sender_name} · ${item.timestamp}`;
    const body = document.createElement("div");
    body.textContent = item.message;
    card.append(meta, body);
    wrapper.appendChild(card);
    return wrapper;
}

async function loadChatMessages() {
    if (!chatMessages) {
        return;
    }
    const taskId = chatMessages.dataset.taskId;
    const response = await fetch(`/chat/tasks/${taskId}/messages?after_id=${lastChatId}`);
    if (!response.ok) {
        return;
    }
    const data = await response.json();
    data.messages.forEach((item) => {
        chatMessages.appendChild(renderChatMessage(item));
        lastChatId = Math.max(lastChatId, item.id);
    });
    if (data.messages.length) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

if (chatMessages && chatForm) {
    loadChatMessages();
    setInterval(loadChatMessages, 3500);
    chatForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const input = chatForm.querySelector("input[name='message']");
        const taskId = chatMessages.dataset.taskId;
        const formData = new FormData();
        formData.append("message", input.value);
        const response = await fetch(`/chat/tasks/${taskId}/messages`, {
            method: "POST",
            body: formData
        });
        if (response.ok) {
            input.value = "";
            await loadChatMessages();
        }
    });
}
