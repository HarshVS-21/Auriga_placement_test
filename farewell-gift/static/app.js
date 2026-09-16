async function api(url, options = {}) {
    const response = await fetch(url, {
        headers: {
            "Content-Type": "application/json"
        },
        ...options
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Something went wrong");
    }

    return data;
}


async function createPool() {
    const organizer = document.getElementById("organizer").value.trim();
    const budget = document.getElementById("budget").value;

    if (!organizer || !budget) {
        alert("Enter organizer and budget.");
        return;
    }

    try {
        await api("/api/pool", {
            method: "POST",
            body: JSON.stringify({
                organizer,
                budget
            })
        });

        loadSummary();
    } catch (error) {
        alert(error.message);
    }
}


async function addParticipant() {
    const input = document.getElementById("participantName");
    const name = input.value.trim();

    if (!name) {
        alert("Enter a participant name.");
        return;
    }

    try {
        await api("/api/participants", {
            method: "POST",
            body: JSON.stringify({ name })
        });

        input.value = "";
        loadSummary();
    } catch (error) {
        alert(error.message);
    }
}


async function addPayment(id) {
    const input = document.getElementById(`payment-${id}`);
    const amount = input.value;

    if (!amount || Number(amount) <= 0) {
        alert("Enter a valid payment amount.");
        return;
    }

    try {
        await api(`/api/participants/${id}/payment`, {
            method: "POST",
            body: JSON.stringify({ amount })
        });

        input.value = "";
        loadSummary();
    } catch (error) {
        alert(error.message);
    }
}


async function loadSummary() {
    try {
        const data = await api("/api/pool");

        document.getElementById("summarySection")
            .classList.remove("hidden");

        document.getElementById("budgetValue").textContent =
            `₹${data.budget.toFixed(2)}`;

        document.getElementById("shareValue").textContent =
            `₹${data.share.toFixed(2)}`;

        document.getElementById("collectedValue").textContent =
            `₹${data.total_paid.toFixed(2)}`;

        document.getElementById("remainingValue").textContent =
            `₹${data.remaining.toFixed(2)}`;

        renderParticipants(data.participants);
        renderSettlements(data.settlements, data.surplus);

    } catch (error) {
        // No pool yet.
    }
}


function renderParticipants(participants) {
    const table = document.getElementById("participantsTable");

    table.innerHTML = "";

    participants.forEach(p => {

        let balanceText;

        if (p.status === "owes") {
            balanceText =
                `Owes ₹${p.balance.toFixed(2)}`;
        } else if (p.status === "credit") {
            balanceText =
                `Credit ₹${Math.abs(p.balance).toFixed(2)}`;
        } else {
            balanceText = "Settled";
        }

        table.innerHTML += `
            <tr>
                <td>${escapeHtml(p.name)}</td>
                <td>₹${p.share.toFixed(2)}</td>
                <td>₹${p.paid.toFixed(2)}</td>
                <td>${balanceText}</td>
                <td>
                    <input
                        id="payment-${p.id}"
                        class="payment-input"
                        type="number"
                        min="0.01"
                        step="0.01"
                        placeholder="₹ amount"
                    >
                    <button onclick="addPayment(${p.id})">
                        Add
                    </button>
                </td>
            </tr>
        `;
    });
}


function renderSettlements(settlements, surplus) {
    const container = document.getElementById("settlements");

    if (settlements.length === 0) {
        if (surplus > 0) {
            container.innerHTML =
                `<p>All participant balances are settled. Pool surplus: ₹${surplus.toFixed(2)}</p>`;
        } else {
            container.innerHTML =
                "<p>No settlements needed yet.</p>";
        }
        return;
    }

    container.innerHTML = settlements.map(s => `
        <div class="settlement">
            <strong>${escapeHtml(s.from)}</strong>
            pays
            <strong>₹${s.amount.toFixed(2)}</strong>
            to
            <strong>${escapeHtml(s.to)}</strong>
        </div>
    `).join("");
}


async function resetPool() {
    if (!confirm("Reset the entire pool?")) {
        return;
    }

    await api("/api/reset", {
        method: "POST"
    });

    location.reload();
}


function escapeHtml(value) {
    return value
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


loadSummary();