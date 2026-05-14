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
