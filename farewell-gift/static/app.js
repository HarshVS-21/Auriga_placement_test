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


// ---------------------------
// Pool
// ---------------------------

async function createPool() {
    const organizer = document.getElementById("organizer").value.trim();
    const budget = document.getElementById("budget").value;

    if (!organizer || !budget) {
        alert("Enter organizer and budget.");
        return;
    }

    try {
        const data = await api("/api/pool", {
            method: "POST",
            body: JSON.stringify({
                organizer,
                budget
            })
        });

        renderSummary(data);
    } catch (error) {
        alert(error.message);
    }
}


// ---------------------------
// Participants
// ---------------------------

async function addParticipant() {
    const input = document.getElementById("participantName");
    const name = input.value.trim();

    if (!name) {
        alert("Enter a participant name.");
        return;
    }

    try {
        const data = await api("/api/participants", {
            method: "POST",
            body: JSON.stringify({
                name
            })
        });

        input.value = "";
        renderSummary(data);
    } catch (error) {
        alert(error.message);
    }
}


// ---------------------------
// Payments
// ---------------------------

async function addPayment(id) {
    const input = document.getElementById(`payment-${id}`);
    const amount = input.value;

    if (!amount || Number(amount) <= 0) {
        alert("Enter a valid payment amount.");
        return;
    }

    try {
        const data = await api(
            `/api/participants/${id}/payment`,
            {
                method: "POST",
                body: JSON.stringify({
                    amount
                })
            }
        );

        input.value = "";
        renderSummary(data);
    } catch (error) {
        alert(error.message);
    }
}


// ---------------------------
// CSV Import
// ---------------------------

async function importCsv() {
    const fileInput = document.getElementById("csvFile");
    const reportBox = document.getElementById("importReport");

    if (!fileInput.files.length) {
        alert("Please select a CSV file.");
        return;
    }

    const formData = new FormData();

    formData.append(
        "file",
        fileInput.files[0]
    );

    try {
        const response = await fetch("/api/import", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || "Import failed."
            );
        }

        const report = data.report;

        reportBox.classList.remove("hidden");

        let html = `
            <div class="report-title">
                Import completed successfully
            </div>

            <div class="report-grid">

                <div>
                    <span>Total rows</span>
                    <strong>${report.rows}</strong>
                </div>

                <div>
                    <span>Imported</span>
                    <strong>${report.imported}</strong>
                </div>

                <div>
                    <span>Duplicates removed</span>
                    <strong>${report.duplicates}</strong>
                </div>

                <div>
                    <span>Merged</span>
                    <strong>${report.merged}</strong>
                </div>

                <div>
                    <span>Rejected</span>
                    <strong>${report.rejected}</strong>
                </div>

            </div>
        `;


        // Merged rows
        if (report.merged_rows.length > 0) {
            html += `
                <h3>Merged names</h3>

                <div class="report-list">
                    ${report.merged_rows.map(item => `
                        <div>
                            <strong>
                                ${escapeHtml(item.source_name)}
                            </strong>

                            →
                            
                            ${escapeHtml(item.canonical_name)}

                            <span>
                                ₹${Number(item.amount).toFixed(2)}
                            </span>
                        </div>
                    `).join("")}
                </div>
            `;
        }


        // Duplicate rows
        if (report.duplicate_rows.length > 0) {
            html += `
                <h3>Duplicate rows removed</h3>

                <div class="report-list">
                    ${report.duplicate_rows.map(item => `
                        <div>
                            Row ${item.row}:
                            ${escapeHtml(item.name)}

                            <span>
                                ₹${Number(item.amount).toFixed(2)}
                            </span>
                        </div>
                    `).join("")}
                </div>
            `;
        }


        // Rejected rows
        if (report.rejected_rows.length > 0) {
            html += `
                <h3>Rejected rows</h3>

                <div class="report-list">
                    ${report.rejected_rows.map(item => `
                        <div>
                            Row ${item.row}:

                            ${
                                item.name
                                    ? escapeHtml(item.name)
                                    : "(empty name)"
                            }

                            <span>
                                ${escapeHtml(item.reason)}
                            </span>
                        </div>
                    `).join("")}
                </div>
            `;
        }


        reportBox.innerHTML = html;

        // Update dashboard after import
        renderSummary(data.summary);

        // Clear selected file
        fileInput.value = "";

    } catch (error) {
        alert(error.message);
    }
}


// ---------------------------
// Load Summary
// ---------------------------

async function loadSummary() {
    try {
        const data = await api("/api/pool");

        renderSummary(data);

    } catch (error) {
        // No pool exists yet.
        // Nothing to render.
    }
}


// ---------------------------
// Render Summary
// ---------------------------

function renderSummary(data) {
    const summarySection =
        document.getElementById("summarySection");

    summarySection.classList.remove("hidden");


    document.getElementById("budgetValue").textContent =
        `₹${Number(data.budget).toFixed(2)}`;


    document.getElementById("shareValue").textContent =
        `₹${Number(data.share).toFixed(2)}`;


    document.getElementById("collectedValue").textContent =
        `₹${Number(data.total_paid).toFixed(2)}`;


    document.getElementById("remainingValue").textContent =
        `₹${Number(data.remaining).toFixed(2)}`;


    renderParticipants(data.participants);

    renderSettlements(
        data.settlements,
        data.surplus
    );
}


// ---------------------------
// Render Participants
// ---------------------------

function renderParticipants(participants) {
    const table =
        document.getElementById("participantsTable");

    table.innerHTML = "";


    participants.forEach(participant => {

        let balanceText;


        if (participant.status === "owes") {

            balanceText =
                `<span style="color:#dc2626;font-weight:600;">
                    Owes ₹${Math.abs(
                        Number(participant.balance)
                    ).toFixed(2)}
                 </span>`;

        } else if (participant.status === "credit") {

            balanceText =
                `<span style="color:#16a34a;font-weight:600;">
                    Credit ₹${Math.abs(
                        Number(participant.balance)
                    ).toFixed(2)}
                 </span>`;

        } else {

            balanceText =
                `<span style="color:#16a34a;font-weight:600;">
                    Settled
                 </span>`;
        }


        table.innerHTML += `
            <tr>

                <td>
                    <strong>
                        ${escapeHtml(participant.name)}
                    </strong>
                </td>

                <td>
                    ₹${Number(
                        participant.share
                    ).toFixed(2)}
                </td>

                <td>
                    ₹${Number(
                        participant.paid
                    ).toFixed(2)}
                </td>

                <td>
                    ${balanceText}
                </td>

                <td>

                    <input
                        id="payment-${participant.id}"
                        class="payment-input"
                        type="number"
                        min="0.01"
                        step="0.01"
                        placeholder="₹ amount"
                    >

                    <button
                        onclick="addPayment(${participant.id})"
                    >
                        Add
                    </button>

                </td>

            </tr>
        `;
    });


    if (participants.length === 0) {
        table.innerHTML = `
            <tr>
                <td colspan="5"
                    style="text-align:center;color:#6b7280;">
                    No participants added yet.
                </td>
            </tr>
        `;
    }
}


// ---------------------------
// Render Settlements
// ---------------------------

function renderSettlements(
    settlements,
    surplus
) {
    const container =
        document.getElementById("settlements");


    if (!settlements ||
        settlements.length === 0) {

        if (Number(surplus) > 0) {

            container.innerHTML = `
                <div class="settlement">
                    All participant balances are settled.

                    Pool surplus:
                    <strong>
                        ₹${Number(surplus).toFixed(2)}
                    </strong>
                </div>
            `;

        } else {

            container.innerHTML = `
                <p>
                    No settlements needed yet.
                </p>
            `;
        }

        return;
    }


    container.innerHTML =
        settlements.map(settlement => `
            <div class="settlement">

                <strong>
                    ${escapeHtml(settlement.from)}
                </strong>

                <span>pays</span>

                <strong>
                    ₹${Number(
                        settlement.amount
                    ).toFixed(2)}
                </strong>

                <span>to</span>

                <strong>
                    ${escapeHtml(settlement.to)}
                </strong>

            </div>
        `).join("");
}


// ---------------------------
// Reset
// ---------------------------

async function resetPool() {
    const confirmed = confirm(
        "Reset the entire pool? This will remove all participants and payments."
    );

    if (!confirmed) {
        return;
    }


    try {
        await api("/api/reset", {
            method: "POST"
        });

        location.reload();

    } catch (error) {
        alert(error.message);
    }
}


// ---------------------------
// HTML Escaping
// ---------------------------

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


// ---------------------------
// Initial Load
// ---------------------------

loadSummary();