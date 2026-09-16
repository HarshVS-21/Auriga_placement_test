I am currently taking a live AI-assisted System Design / Software Development assessment for a company placement drive.

You are my real-time senior software engineer and coding assistant.

The assessment allows me to use AI tools and Internet resources. I will give you the problem statement after this message.

Your job is to help me solve the problem efficiently and correctly within the given time.

IMPORTANT RULES:

Do NOT over-explain unless I ask for an explanation. Keep responses concise and actionable.
First understand the problem carefully. Identify:
Functional requirements
Non-functional requirements
Important constraints
Expected inputs/outputs
Edge cases
Before proposing a complex solution, choose the simplest architecture that correctly satisfies the requirements. Do not introduce unnecessary microservices, Kafka, Kubernetes, Redis, etc. unless there is a genuine reason.
For system design questions, structure the solution as:
Requirements
High-level architecture
Components
Data flow
APIs
Database/schema
Authentication/authorization if relevant
Error handling
Scalability
Security
Trade-offs
If implementation is required, give me a practical implementation plan first, then help me implement it step by step.
Assume the implementation will be done in GitHub Codespaces unless I tell you otherwise.
Prefer technologies that are simple, reliable, and appropriate for a fresher-level placement assessment. Do not over-engineer.
When generating code:
Make it runnable
Keep it clean and understandable
Include necessary imports and dependencies
Maintain a sensible project structure
Handle errors properly
Do not leave placeholders or pseudo-code when actual implementation is required
After implementation, help me test the solution. Think about:
Normal cases
Edge cases
Invalid input
Authentication/security issues
Failure scenarios
If I show you an error, diagnose the actual cause first. Give me the exact change/command needed rather than rewriting the entire project unnecessarily.
If I show you my proposed design or code, CRITICALLY review it. Do not agree with me just to be polite. Point out incorrect assumptions, bugs, security problems, unnecessary complexity, and missing requirements.
If there are multiple valid approaches, briefly compare them and recommend the simplest appropriate approach based on the requirements. Explain the trade-off in 1–3 sentences.
If something in the problem statement is ambiguous, identify the ambiguity and make a reasonable assumption rather than stopping unnecessarily. Clearly state the assumption.
Do not invent requirements that aren't present in the problem. Separate stated requirements from your assumptions.
During the assessment, prioritize:
CORRECTNESS > COMPLETENESS > SIMPLICITY > PERFORMANCE OPTIMIZATION.
If I ask for something that can be answered with a few lines, answer in a few lines. I am under time pressure.
If I say "QUICK", give me only the essential answer/action with no explanation.
If I say "EXPLAIN", then explain the reasoning clearly so I can understand and defend the solution if the evaluator asks me about it.
Remember that I may need to explain my solution to an interviewer afterward. Never give me an architecture or code that I cannot reasonably understand.

Wait for my problem statement now. Do not start solving anything until I provide it.

Understood. Send the problem statement.

i have to do it in github codespace

Yes. We'll assume GitHub Codespaces as the development environment.

Once you send the problem statement, I'll help you:

Identify requirements and constraints.
Choose the simplest suitable architecture/stack.
Set up the Codespace project.
Implement it step-by-step with runnable code.
Test normal + edge cases.
Fix errors quickly if they appear.
Prepare concise points you can use to explain your solution to the evaluator.

Send the full problem statement when you're ready.

ROUND 2  ·  BUILD ROUND
Chipping in for the farewell gift
The team is buying a farewell gift for their manager — budget ₹6,000. Everyone agreed to chip in equally, but in practice it’s chaos: some have paid their full share, a few paid only part, one generous soul paid extra to cover a friend, and two people haven’t paid at all. The organiser is constantly asked ‘how much do I still owe?’ and ‘have we collected enough yet?’ At the end the organiser just wants the simplest list of who should pay whom so everyone lands on their fair share.
Build something so the organiser can track the pool and settle up fairly.
(The questions the organiser keeps fielding are your clues — and build for any pool and organiser, not just this one. The easier you make it to see shares, balances and what’s left to collect, the better. Start with equal shares and simple balances, then settlements.)

What you need to build

The problem naturally breaks into four core features:

Stated requirements

Create a pool with an arbitrary budget and organizer.
Add participants.
Automatically calculate equal share per participant.
Record how much each participant has paid.
Show each person's balance:
owes if paid less than share
credit if paid more than share
settled if exactly at share
Show total collected and amount remaining to collect.
Generate the simplest who-pays-whom settlement list.
Make it easy for the organiser to understand the current state.

Reasonable assumption

One active pool at a time is sufficient for this assessment.
No login/authentication is required because the prompt doesn't ask for it.
Money is stored in paise/integer arithmetic to avoid floating-point problems.
Recommended stack
Browser
   ↓
Flask REST API
   ↓
SQLite

No React, Redis, Docker, Kafka, microservices, etc. They're unnecessary for this problem.

1. Create the Codespace project

In your Codespace terminal:

mkdir farewell-gift
cd farewell-gift

python -m venv venv
source venv/bin/activate

pip install flask

Create this structure:

farewell-gift/
├── app.py
├── requirements.txt
├── gift.db
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── app.js

requirements.txt:

Flask==3.1.2
2. Backend — app.py
from flask import Flask, jsonify, request, render_template
import sqlite3
from pathlib import Path

app = Flask(__name__)

DB_PATH = Path("gift.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS pool (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            organizer TEXT NOT NULL,
            budget INTEGER NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            paid INTEGER NOT NULL DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


def calculate_summary():
    conn = get_db()

    pool = conn.execute(
        "SELECT * FROM pool WHERE id = 1"
    ).fetchone()

    participants = conn.execute(
        "SELECT id, name, paid FROM participants ORDER BY id"
    ).fetchall()

    conn.close()

    if not pool:
        return None

    budget = pool["budget"]
    count = len(participants)

    share = budget / count if count else 0

    result = []

    for p in participants:
        paid = p["paid"]
        balance = round(share - paid, 2)

        if balance > 0.001:
            status = "owes"
        elif balance < -0.001:
            status = "credit"
        else:
            status = "settled"

        result.append({
            "id": p["id"],
            "name": p["name"],
            "paid": paid / 100,
            "share": round(share / 100, 2),
            "balance": round(balance / 100, 2),
            "status": status
        })

    total_paid = sum(p["paid"] for p in participants)

    remaining = max(budget - total_paid, 0)
    surplus = max(total_paid - budget, 0)

    settlements = generate_settlements(participants, budget)

    return {
        "organizer": pool["organizer"],
        "budget": budget / 100,
        "participant_count": count,
        "share": round(share / 100, 2) if count else 0,
        "total_paid": total_paid / 100,
        "remaining": remaining / 100,
        "surplus": surplus / 100,
        "participants": result,
        "settlements": settlements
    }


def generate_settlements(participants, budget):
    """
    Greedy settlement:
    creditors = people who paid more than their fair share
    debtors = people who paid less than their fair share

    Returns a small practical set of transfers.
    """

    count = len(participants)

    if count == 0:
        return []

    share = budget / count

    creditors = []
    debtors = []

    for p in participants:
        net = p["paid"] - share

        if net > 0.005:
            creditors.append({
                "name": p["name"],
                "amount": net
            })
        elif net < -0.005:
            debtors.append({
                "name": p["name"],
                "amount": -net
            })

    settlements = []

    i = 0
    j = 0

    while i < len(debtors) and j < len(creditors):
        amount = min(debtors[i]["amount"], creditors[j]["amount"])

        settlements.append({
            "from": debtors[i]["name"],
            "to": creditors[j]["name"],
            "amount": round(amount / 100, 2)
        })

        debtors[i]["amount"] -= amount
        creditors[j]["amount"] -= amount

        if debtors[i]["amount"] <= 0.005:
            i += 1

        if creditors[j]["amount"] <= 0.005:
            j += 1

    return settlements


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/pool", methods=["GET"])
def get_pool():
    summary = calculate_summary()

    if not summary:
        return jsonify({"error": "No pool exists"}), 404

    return jsonify(summary)


@app.route("/api/pool", methods=["POST"])
def create_pool():
    data = request.get_json()

    organizer = str(data.get("organizer", "")).strip()
    budget = data.get("budget")

    if not organizer:
        return jsonify({"error": "Organizer is required"}), 400

    if budget is None:
        return jsonify({"error": "Budget is required"}), 400

    try:
        budget_paise = int(round(float(budget) * 100))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid budget"}), 400

    if budget_paise <= 0:
        return jsonify({"error": "Budget must be greater than 0"}), 400

    conn = get_db()

    conn.execute("DELETE FROM participants")

    conn.execute("""
        INSERT INTO pool (id, organizer, budget)
        VALUES (1, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            organizer = excluded.organizer,
            budget = excluded.budget
    """, (organizer, budget_paise))

    conn.commit()
    conn.close()

    return jsonify(calculate_summary()), 201


@app.route("/api/participants", methods=["POST"])
def add_participant():
    data = request.get_json()
    name = str(data.get("name", "")).strip()

    if not name:
        return jsonify({"error": "Name is required"}), 400

    conn = get_db()

    try:
        conn.execute(
            "INSERT INTO participants (name) VALUES (?)",
            (name,)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Participant already exists"}), 409

    conn.close()

    return jsonify(calculate_summary()), 201


@app.route("/api/participants/<int:participant_id>/payment", methods=["POST"])
def add_payment(participant_id):
    data = request.get_json()
    amount = data.get("amount")

    try:
        amount_paise = int(round(float(amount) * 100))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid payment amount"}), 400

    if amount_paise <= 0:
        return jsonify({"error": "Payment must be greater than 0"}), 400

    conn = get_db()

    participant = conn.execute(
        "SELECT id FROM participants WHERE id = ?",
        (participant_id,)
    ).fetchone()

    if not participant:
        conn.close()
        return jsonify({"error": "Participant not found"}), 404

    conn.execute(
        "UPDATE participants SET paid = paid + ? WHERE id = ?",
        (amount_paise, participant_id)
    )

    conn.commit()
    conn.close()

    return jsonify(calculate_summary())


@app.route("/api/reset", methods=["POST"])
def reset():
    conn = get_db()

    conn.execute("DELETE FROM participants")
    conn.execute("DELETE FROM pool")

    conn.commit()
    conn.close()

    return jsonify({"message": "Reset successful"})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
3. Frontend — templates/index.html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Farewell Gift Splitter</title>
    <link rel="stylesheet" href="/static/style.css">
</head>

<body>

<div class="container">

    <h1>Farewell Gift Splitter</h1>
    <p class="subtitle">Track contributions and settle everyone fairly.</p>

    <section class="card">
        <h2>Pool Setup</h2>

        <div class="form-row">
            <input id="organizer" placeholder="Organizer name">
            <input id="budget" type="number" min="1" placeholder="Budget ₹">
            <button onclick="createPool()">Create / Update Pool</button>
        </div>
    </section>

    <section class="card">
        <h2>Add Participant</h2>

        <div class="form-row">
            <input id="participantName" placeholder="Participant name">
            <button onclick="addParticipant()">Add</button>
        </div>
    </section>

    <section id="summarySection" class="hidden">

        <div class="stats">

            <div class="stat">
                <span>Budget</span>
                <strong id="budgetValue">₹0</strong>
            </div>

            <div class="stat">
                <span>Share / Person</span>
                <strong id="shareValue">₹0</strong>
            </div>

            <div class="stat">
                <span>Collected</span>
                <strong id="collectedValue">₹0</strong>
            </div>

            <div class="stat">
                <span>Remaining</span>
                <strong id="remainingValue">₹0</strong>
            </div>

        </div>

        <section class="card">
            <h2>Participants</h2>

            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Share</th>
                        <th>Paid</th>
                        <th>Balance</th>
                        <th>Payment</th>
                    </tr>
                </thead>

                <tbody id="participantsTable"></tbody>
            </table>
        </section>

        <section class="card">
            <h2>Settlement</h2>

            <div id="settlements"></div>
        </section>

        <button class="danger" onclick="resetPool()">Reset Pool</button>

    </section>

</div>

<script src="/static/app.js"></script>

</body>
</html>
4. CSS — static/style.css
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f5f7fb;
    color: #222;
}

.container {
    max-width: 1100px;
    margin: 40px auto;
    padding: 20px;
}

h1 {
    margin-bottom: 5px;
}

.subtitle {
    color: #666;
    margin-bottom: 30px;
}

.card {
    background: white;
    padding: 20px;
    margin-bottom: 20px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.form-row {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}

input {
    padding: 11px;
    border: 1px solid #ccc;
    border-radius: 7px;
    flex: 1;
}

button {
    padding: 11px 18px;
    border: none;
    border-radius: 7px;
    cursor: pointer;
    background: #2563eb;
    color: white;
}

button:hover {
    opacity: 0.9;
}

.stats {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 15px;
    margin-bottom: 20px;
}

.stat {
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.stat span {
    display: block;
    color: #666;
    margin-bottom: 8px;
}

.stat strong {
    font-size: 24px;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th,
td {
    padding: 12px;
    border-bottom: 1px solid #eee;
    text-align: left;
}

.payment-input {
    width: 110px;
}

.settlement {
    padding: 12px;
    background: #f8fafc;
    margin-bottom: 8px;
    border-radius: 8px;
}

.hidden {
    display: none;
}

.danger {
    background: #dc2626;
}

@media (max-width: 800px) {
    .stats {
        grid-template-columns: repeat(2, 1fr);
    }

    table {
        font-size: 14px;
    }
}
5. JavaScript — static/app.js
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
6. Run it

Inside Codespaces:

python app.py

You should see:

* Running on http://127.0.0.1:5000

Open port 5000 in Codespaces.

7. Test with the assessment scenario

Use:

Budget = ₹6000

Participants:
A
B
C
D
E
F

Each person's fair share:

₹6000 / 6 = ₹1000

Try payments like:

A → ₹1000
B → ₹1000
C → ₹500
D → ₹1500
E → ₹0
F → ₹2000

The application should identify:

C owes ₹500
E owes ₹1000

A settled
B settled
D credit ₹500
F credit ₹1000

And produce settlements such as:

C pays ₹500 to D
E pays ₹1000 to F

That's exactly the core problem the prompt is asking you to solve.

One important design decision

Don't calculate settlements based simply on the remaining pool amount. Calculate them from each person's net position relative to their fair share:

net = paid - fair_share

That is what correctly handles the "generous soul paid extra to cover a friend" case.

What I'd show the evaluator

Keep the demo focused:

Create pool
      ↓
Add people
      ↓
Automatically calculate equal share
      ↓
Record payments
      ↓
Show collected / remaining
      ↓
Show each person's balance
      ↓
Generate settlement transfers

That is enough. Do not waste assessment time adding authentication, Docker, JWT, React, database migrations, cloud deployment, or microservices unless the evaluator explicitly asks for them.