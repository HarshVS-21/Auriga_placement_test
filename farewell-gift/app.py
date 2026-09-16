from flask import Flask, jsonify, request, render_template
import sqlite3
from pathlib import Path
import csv
import io
import re
from difflib import SequenceMatcher

app = Flask(__name__)

DB_PATH = Path("gift.db")


# =========================================================
# DATABASE
# =========================================================

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


# =========================================================
# SUMMARY
# =========================================================

def calculate_summary():
    conn = get_db()

    pool = conn.execute(
        "SELECT * FROM pool WHERE id = 1"
    ).fetchone()

    participants = conn.execute(
        """
        SELECT id, name, paid
        FROM participants
        ORDER BY id
        """
    ).fetchall()

    conn.close()

    if not pool:
        return None

    budget = pool["budget"]
    count = len(participants)

    # All values are stored in paise.
    share_paise = budget / count if count else 0

    result = []

    for participant in participants:
        paid = participant["paid"]

        # Positive = amount still owed
        # Negative = amount paid extra
        balance = share_paise - paid

        if balance > 0.005:
            status = "owes"

        elif balance < -0.005:
            status = "credit"

        else:
            status = "settled"

        result.append({
            "id": participant["id"],
            "name": participant["name"],
            "paid": round(paid / 100, 2),
            "share": round(share_paise / 100, 2),
            "balance": round(balance / 100, 2),
            "status": status
        })

    total_paid = sum(
        participant["paid"]
        for participant in participants
    )

    remaining = max(budget - total_paid, 0)
    surplus = max(total_paid - budget, 0)

    settlements = generate_settlements(
        participants,
        budget
    )

    return {
        "organizer": pool["organizer"],
        "budget": round(budget / 100, 2),
        "participant_count": count,
        "share": round(share_paise / 100, 2)
            if count else 0,
        "total_paid": round(total_paid / 100, 2),
        "remaining": round(remaining / 100, 2),
        "surplus": round(surplus / 100, 2),
        "participants": result,
        "settlements": settlements
    }


# =========================================================
# SETTLEMENT ALGORITHM
# =========================================================

def generate_settlements(participants, budget):
    count = len(participants)

    if count == 0:
        return []

    share = budget / count

    creditors = []
    debtors = []

    for participant in participants:

        net = participant["paid"] - share

        # Participant paid extra
        if net > 0.005:
            creditors.append({
                "name": participant["name"],
                "amount": net
            })

        # Participant still owes
        elif net < -0.005:
            debtors.append({
                "name": participant["name"],
                "amount": -net
            })

    settlements = []

    debtor_index = 0
    creditor_index = 0

    while (
        debtor_index < len(debtors)
        and creditor_index < len(creditors)
    ):
        amount = min(
            debtors[debtor_index]["amount"],
            creditors[creditor_index]["amount"]
        )

        settlements.append({
            "from": debtors[debtor_index]["name"],
            "to": creditors[creditor_index]["name"],
            "amount": round(amount / 100, 2)
        })

        debtors[debtor_index]["amount"] -= amount
        creditors[creditor_index]["amount"] -= amount

        if debtors[debtor_index]["amount"] <= 0.005:
            debtor_index += 1

        if creditors[creditor_index]["amount"] <= 0.005:
            creditor_index += 1

    return settlements


# =========================================================
# NAME CLEANING
# =========================================================

def normalize_name(name):
    name = str(name or "").strip().lower()

    name = re.sub(
        r"[^a-z0-9\s]",
        " ",
        name
    )

    name = re.sub(
        r"\s+",
        " ",
        name
    ).strip()

    return name

def name_similarity(name1, name2):
    normalized1 = normalize_name(name1)
    normalized2 = normalize_name(name2)

    if not normalized1 or not normalized2:
        return 0

    # Exact normalized match.
    if normalized1 == normalized2:
        return 1.0

    # Full string similarity.
    full_ratio = SequenceMatcher(
        None,
        normalized1,
        normalized2
    ).ratio()

    # Token-based comparison.
    tokens1 = sorted(normalized1.split())
    tokens2 = sorted(normalized2.split())

    token_ratio = SequenceMatcher(
        None,
        " ".join(tokens1),
        " ".join(tokens2)
    ).ratio()

    return max(
        full_ratio,
        token_ratio
    )


def find_matching_participant(conn, cleaned_name):
    participants = conn.execute(
        """
        SELECT id, name
        FROM participants
        """
    ).fetchall()

    normalized_name = normalize_name(cleaned_name)

    # 1. Exact normalized match
    for participant in participants:
        if normalize_name(participant["name"]) == normalized_name:
            return participant

    # 2. Conservative fuzzy matching
    best_match = None
    best_score = 0

    for participant in participants:
        score = name_similarity(
            cleaned_name,
            participant["name"]
        )

        if score > best_score:
            best_score = score
            best_match = participant

    # Only merge when similarity is sufficiently high.
    if best_match and best_score >= 0.88:
        return best_match

    return None

# =========================================================
# AMOUNT CLEANING
# =========================================================

def parse_amount(value):
    """
    Converts messy currency strings into integer paise.

    Supported examples:

    1000
    1,000
    ₹1000
    ₹1,000
    Rs. 1000
    INR 1000
    1000/-
    1000.50

    Invalid and negative values return None.
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    # Remove currency symbols / labels.
    text = re.sub(
        r"(₹|rs\.?|inr)",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Remove trailing /-
    text = re.sub(
        r"/-\s*$",
        "",
        text
    )

    # Remove spaces.
    text = text.replace(" ", "")

    # Remove remaining unwanted characters.
    text = re.sub(
        r"[^0-9.\-]",
        "",
        text
    )

    if not text:
        return None

    # Negative amounts are invalid.
    if text.startswith("-"):
        return None

    try:
        amount = float(text)

    except ValueError:
        return None

    if amount <= 0:
        return None

    return int(round(amount * 100))


# =========================================================
# CSV HELPERS
# =========================================================

def find_column(
    fieldnames,
    possible_names
):
    """
    Finds the actual CSV column name even if
    capitalization or spacing differs.
    """

    normalized_columns = {
        normalize_name(field): field
        for field in fieldnames
        if field is not None
    }

    for possible_name in possible_names:

        normalized_possible = normalize_name(
            possible_name
        )

        if normalized_possible in normalized_columns:
            return normalized_columns[
                normalized_possible
            ]

    return None


# =========================================================
# CSV IMPORT
# =========================================================

def import_contributions(file_bytes):
    """
    Reads and cleans the uploaded CSV.

    Reports:
    - total rows
    - imported rows
    - duplicate rows
    - merged rows
    - rejected rows
    """

    text = file_bytes.decode(
        "utf-8-sig",
        errors="replace"
    )

    reader = csv.DictReader(
        io.StringIO(text)
    )

    if not reader.fieldnames:
        raise ValueError(
            "CSV must contain a header row."
        )

    name_column = find_column(
        reader.fieldnames,
        [
            "name",
            "participant",
            "person",
            "member",
            "contributor"
        ]
    )

    amount_column = find_column(
        reader.fieldnames,
        [
            "amount",
            "paid",
            "payment",
            "contribution",
            "value"
        ]
    )

    if not name_column:
        raise ValueError(
            "CSV must contain a name column."
        )

    if not amount_column:
        raise ValueError(
            "CSV must contain an amount column."
        )

    conn = get_db()

    report = {
        "rows": 0,
        "imported": 0,
        "duplicates": 0,
        "merged": 0,
        "rejected": 0,
        "rejected_rows": [],
        "merged_rows": [],
        "duplicate_rows": []
    }

    # Used to identify exact duplicate rows
    # inside the uploaded CSV.
    seen_rows = set()

    for row_number, row in enumerate(
        reader,
        start=2
    ):

        report["rows"] += 1

        raw_name = row.get(
            name_column,
            ""
        )

        raw_amount = row.get(
            amount_column,
            ""
        )

        cleaned_name = str(
            raw_name or ""
        ).strip()

        amount_paise = parse_amount(
            raw_amount
        )

        # -----------------------------------------
        # Missing / invalid name
        # -----------------------------------------

        if not cleaned_name:

            report["rejected"] += 1

            report["rejected_rows"].append({
                "row": row_number,
                "name": "",
                "amount": str(raw_amount),
                "reason": "Missing participant name"
            })

            continue

        # -----------------------------------------
        # Invalid amount
        # -----------------------------------------

        if amount_paise is None:

            report["rejected"] += 1

            report["rejected_rows"].append({
                "row": row_number,
                "name": cleaned_name,
                "amount": str(raw_amount),
                "reason": f"Invalid amount: {raw_amount}"
            })

            continue

        # -----------------------------------------
        # Exact duplicate contribution row
        # -----------------------------------------

        normalized_name = normalize_name(
            cleaned_name
        )

        duplicate_key = (
            normalized_name,
            amount_paise
        )

        if duplicate_key in seen_rows:

            report["duplicates"] += 1

            report["duplicate_rows"].append({
                "row": row_number,
                "name": cleaned_name,
                "amount": amount_paise / 100
            })

            continue

        seen_rows.add(
            duplicate_key
        )

        # -----------------------------------------
        # Find existing participant
        # -----------------------------------------

        participant = find_matching_participant(
            conn,
            cleaned_name
        )

        if participant:

            # Merge contribution into existing
            # participant.
            conn.execute(
                """
                UPDATE participants
                SET paid = paid + ?
                WHERE id = ?
                """,
                (
                    amount_paise,
                    participant["id"]
                )
            )

            report["merged"] += 1

            report["merged_rows"].append({
                "row": row_number,
                "source_name": cleaned_name,
                "canonical_name": participant["name"],
                "amount": amount_paise / 100
            })

        else:

            # Create a new participant.
            conn.execute(
                """
                INSERT INTO participants
                (name, paid)
                VALUES (?, ?)
                """,
                (
                    cleaned_name,
                    amount_paise
                )
            )

        # Valid, non-duplicate row.
        report["imported"] += 1

    conn.commit()
    conn.close()

    return report


# =========================================================
# ROUTES
# =========================================================

@app.route("/")
def index():
    return render_template(
        "index.html"
    )


# ---------------------------------------------------------
# GET POOL
# ---------------------------------------------------------

@app.route(
    "/api/pool",
    methods=["GET"]
)
def get_pool():

    summary = calculate_summary()

    if not summary:
        return jsonify({
            "error": "No pool exists"
        }), 404

    return jsonify(summary)


# ---------------------------------------------------------
# CREATE / UPDATE POOL
# ---------------------------------------------------------

@app.route(
    "/api/pool",
    methods=["POST"]
)
def create_pool():

    data = request.get_json() or {}

    organizer = str(
        data.get("organizer", "")
    ).strip()

    budget = data.get("budget")

    if not organizer:
        return jsonify({
            "error": "Organizer is required"
        }), 400

    if budget is None:
        return jsonify({
            "error": "Budget is required"
        }), 400

    try:
        budget_paise = int(
            round(
                float(budget) * 100
            )
        )

    except (
        ValueError,
        TypeError
    ):
        return jsonify({
            "error": "Invalid budget"
        }), 400

    if budget_paise <= 0:
        return jsonify({
            "error": "Budget must be greater than 0"
        }), 400

    conn = get_db()

    # Creating a new pool starts a fresh participant list.
    conn.execute(
        "DELETE FROM participants"
    )

    conn.execute(
        """
        INSERT INTO pool
        (id, organizer, budget)
        VALUES (1, ?, ?)

        ON CONFLICT(id)
        DO UPDATE SET
            organizer = excluded.organizer,
            budget = excluded.budget
        """,
        (
            organizer,
            budget_paise
        )
    )

    conn.commit()
    conn.close()

    return jsonify(
        calculate_summary()
    ), 201


# ---------------------------------------------------------
# ADD PARTICIPANT
# ---------------------------------------------------------

@app.route(
    "/api/participants",
    methods=["POST"]
)
def add_participant():

    data = request.get_json() or {}

    name = str(
        data.get("name", "")
    ).strip()

    if not name:
        return jsonify({
            "error": "Name is required"
        }), 400

    conn = get_db()

    # Make sure a pool exists.
    pool = conn.execute(
        "SELECT id FROM pool WHERE id = 1"
    ).fetchone()

    if not pool:
        conn.close()

        return jsonify({
            "error": "Create a pool before adding participants"
        }), 400

    try:

        conn.execute(
            """
            INSERT INTO participants
            (name)
            VALUES (?)
            """,
            (name,)
        )

        conn.commit()

    except sqlite3.IntegrityError:

        conn.close()

        return jsonify({
            "error": "Participant already exists"
        }), 409

    conn.close()

    return jsonify(
        calculate_summary()
    ), 201


# ---------------------------------------------------------
# ADD PAYMENT
# ---------------------------------------------------------

@app.route(
    "/api/participants/<int:participant_id>/payment",
    methods=["POST"]
)
def add_payment(
    participant_id
):

    data = request.get_json() or {}

    amount = data.get("amount")

    try:

        amount_paise = int(
            round(
                float(amount) * 100
            )
        )

    except (
        ValueError,
        TypeError
    ):

        return jsonify({
            "error": "Invalid payment amount"
        }), 400

    if amount_paise <= 0:

        return jsonify({
            "error": "Payment must be greater than 0"
        }), 400

    conn = get_db()

    participant = conn.execute(
        """
        SELECT id
        FROM participants
        WHERE id = ?
        """,
        (participant_id,)
    ).fetchone()

    if not participant:

        conn.close()

        return jsonify({
            "error": "Participant not found"
        }), 404

    conn.execute(
        """
        UPDATE participants
        SET paid = paid + ?
        WHERE id = ?
        """,
        (
            amount_paise,
            participant_id
        )
    )

    conn.commit()
    conn.close()

    return jsonify(
        calculate_summary()
    )


# ---------------------------------------------------------
# IMPORT CSV
# ---------------------------------------------------------

@app.route(
    "/api/import",
    methods=["POST"]
)
def import_csv():

    # A pool must exist before importing.
    pool_summary = calculate_summary()

    if not pool_summary:

        return jsonify({
            "error": "Create a pool before importing contributions."
        }), 400

    if "file" not in request.files:

        return jsonify({
            "error": "No CSV file uploaded."
        }), 400

    file = request.files["file"]

    if not file.filename:

        return jsonify({
            "error": "No file selected."
        }), 400

    if not file.filename.lower().endswith(".csv"):

        return jsonify({
            "error": "Please upload a CSV file."
        }), 400

    try:

        report = import_contributions(
            file.read()
        )

        summary = calculate_summary()

        return jsonify({
            "report": report,
            "summary": summary
        })

    except Exception as exc:

        return jsonify({
            "error": str(exc)
        }), 400


# ---------------------------------------------------------
# RESET
# ---------------------------------------------------------

@app.route(
    "/api/reset",
    methods=["POST"]
)
def reset():

    conn = get_db()

    conn.execute(
        "DELETE FROM participants"
    )

    conn.execute(
        "DELETE FROM pool"
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Reset successful"
    })


# =========================================================
# APPLICATION START
# =========================================================

if __name__ == "__main__":

    init_db()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )