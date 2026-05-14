const walletForm = document.getElementById("walletTopupForm");

if (walletForm) {
    walletForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const amountInput = walletForm.querySelector("input[name='amount']");
        const amount = amountInput.value;
        const key = walletForm.dataset.key;

        if (!key) {
            alert("Razorpay key is not configured.");
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
                    return;
                }
                window.location.reload();
            },
            theme: { color: "#6c2bd9" }
        };

        const checkout = new Razorpay(options);
        checkout.open();
    });
}
