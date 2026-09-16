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