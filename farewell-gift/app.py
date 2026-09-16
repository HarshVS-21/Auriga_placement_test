from flask import Flask, jsonify, request, render_template
import sqlite3
from pathlib import Path
import csv
import io
import re
from difflib import SequenceMatcher
from collections import Counter

app = Flask(__name__)

DB_PATH = Path("gift.db")


# ============================================================
# DATABASE
# ============================================================

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


# ============================================================
# NAME NORMALIZATION
# ============================================================

def normalize_name(name):
    """
    Normalize a name for comparison.

    Examples:
        " Rahul Sharma " -> "rahul sharma"
        "RAHUL-SHARMA"   -> "rahul sharma"
    """

    name = str(name or "").strip().lower()

    # Replace punctuation with spaces.
    name = re.sub(r"[^a-z0-9\s]", " ", name)

    # Collapse repeated whitespace.
    name = re.sub(r"\s+", " ", name).strip()

    return name


def compact_name(name):
    """
    Remove spaces from normalized name.

    Examples:
        "Harsh Vardhan" -> "harshvardhan"
        "harshvardhan"  -> "harshvardhan"
    """

    return normalize_name(name).replace(" ", "")


# ============================================================
# STRING SIMILARITY
# ============================================================

def sequence_similarity(s1, s2):
    """
    Similarity based on character order.
    """

    if not s1 or not s2:
        return 0.0

    if s1 == s2:
        return 1.0

    return SequenceMatcher(
        None,
        s1,
        s2
    ).ratio()


def character_similarity(s1, s2):
    """
    Similarity based on character composition.

    Helps with small rearrangements such as:
        Rahul -> Ruhal
        Rahul -> Rahlu
    """

    if not s1 or not s2:
        return 0.0

    if len(s1) != len(s2):
        return 0.0

    counter1 = Counter(s1)
    counter2 = Counter(s2)

    if counter1 == counter2:
        return 1.0

    common = sum(
        (counter1 & counter2).values()
    )

    return common / max(
        len(s1),
        len(s2)
    )


def token_similarity(token1, token2):
    """
    Compare individual name tokens.
    """

    token1 = token1.lower()
    token2 = token2.lower()

    if token1 == token2:
        return 1.0

    ordered_score = sequence_similarity(
        token1,
        token2
    )

    character_score = character_similarity(
        token1,
        token2
    )

    return max(
        ordered_score,
        character_score
    )


def name_similarity(name1, name2):
    """
    Compare names while handling:

    - capitalization
    - punctuation
    - extra spaces
    - joined names
    - minor spelling mistakes
    - character rearrangements
    """

    n1 = normalize_name(name1)
    n2 = normalize_name(name2)

    if not n1 or not n2:
        return 0.0

    # Exact normalized match.
    if n1 == n2:
        return 1.0

    # Exact match after removing spaces.
    # Example:
    # Harsh Vardhan
    # harshvardhan
    c1 = compact_name(name1)
    c2 = compact_name(name2)

    if c1 == c2:
        return 1.0

    # Compare compact forms.
    compact_score = sequence_similarity(
        c1,
        c2
    )

    # Token-based comparison.
    tokens1 = n1.split()
    tokens2 = n2.split()

    token_score = 0.0

    if len(tokens1) == len(tokens2):

        scores = [
            token_similarity(t1, t2)
            for t1, t2 in zip(tokens1, tokens2)
        ]

        if scores and min(scores) >= 0.70:
            token_score = (
                sum(scores) / len(scores)
            )

    return max(
        compact_score,
        token_score
    )


def find_matching_participant(conn, cleaned_name):
    """
    Find an existing participant.

    Returns:
        (participant, similarity_score)
    """

    participants = conn.execute(
        """
        SELECT id, name
        FROM participants
        ORDER BY id
        """
    ).fetchall()

    normalized_name = normalize_name(
        cleaned_name
    )

    # --------------------------------------------------------
    # 1. Exact normalized match
    # --------------------------------------------------------

    for participant in participants:

        if normalize_name(
            participant["name"]
        ) == normalized_name:

            return participant, 1.0

    # --------------------------------------------------------
    # 2. Exact compact match
    # --------------------------------------------------------

    compact_input = compact_name(
        cleaned_name
    )

    for participant in participants:

        if compact_name(
            participant["name"]
        ) == compact_input:

            return participant, 1.0

    # --------------------------------------------------------
    # 3. Fuzzy match
    # --------------------------------------------------------

    best_match = None
    best_score = 0.0

    for participant in participants:

        score = name_similarity(
            cleaned_name,
            participant["name"]
        )

        if score > best_score:

            best_score = score
            best_match = participant

    # Conservative threshold.
    if best_match and best_score >= 0.78:
        return best_match, best_score

    return None, 0.0


# ============================================================
# MONEY PARSING
# ============================================================

def parse_amount(value):
    """
    Convert messy currency values into integer paise.

    Supported:

        1000
        1,000
        ₹1000
        ₹1,000
        Rs. 1000
        INR 1000
        1000/-
        1000.50
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    # Remove currency labels.
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

    # Keep numbers, decimal point and minus sign.
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

    return int(
        round(amount * 100)
    )


# ============================================================
# CSV HELPERS
# ============================================================

def find_column(fieldnames, possible_names):
    """
    Find a CSV column despite differences in
    capitalization and spacing.
    """

    normalized_columns = {}

    for field in fieldnames:

        if field is not None:

            normalized_columns[
                normalize_name(field)
            ] = field

    for possible_name in possible_names:

        normalized_possible = normalize_name(
            possible_name
        )

        if normalized_possible in normalized_columns:

            return normalized_columns[
                normalized_possible
            ]

    return None


def empty_import_report():
    return {
        "rows": 0,
        "imported": 0,
        "duplicates": 0,
        "merged": 0,
        "rejected": 0,
        "rejected_rows": [],
        "merged_rows": [],
        "duplicate_rows": []
    }


# ============================================================
# CSV IMPORT
# ============================================================

def import_contributions(file_bytes):
    """
    Import and clean contribution data.

    Handles:
        - duplicate rows
        - spelling variations
        - joined names
        - inconsistent amount formats
        - invalid rows
        - merging
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

    report = empty_import_report()

    # Exact duplicate rows inside the uploaded CSV.
    seen_rows = set()

    # Aliases found during this import.
    import_aliases = []

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

        # ----------------------------------------------------
        # Missing name
        # ----------------------------------------------------

        if not cleaned_name:

            report["rejected"] += 1

            report["rejected_rows"].append({
                "row": row_number,
                "name": "",
                "amount": str(raw_amount),
                "reason": "Missing participant name"
            })

            continue

        # ----------------------------------------------------
        # Invalid amount
        # ----------------------------------------------------

        if amount_paise is None:

            report["rejected"] += 1

            report["rejected_rows"].append({
                "row": row_number,
                "name": cleaned_name,
                "amount": str(raw_amount),
                "reason": (
                    f"Invalid amount: {raw_amount}"
                )
            })

            continue

        normalized_name = normalize_name(
            cleaned_name
        )

        # ----------------------------------------------------
        # Exact duplicate contribution
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Match existing database participant
        # ----------------------------------------------------

        participant, match_score = (
            find_matching_participant(
                conn,
                cleaned_name
            )
        )

        # ----------------------------------------------------
        # If not found, match against aliases from
        # earlier rows in this same CSV.
        # ----------------------------------------------------

        if participant is None:

            best_alias = None
            best_alias_score = 0.0

            for alias in import_aliases:

                score = name_similarity(
                    cleaned_name,
                    alias["canonical_name"]
                )

                if score > best_alias_score:

                    best_alias_score = score
                    best_alias = alias

            if (
                best_alias is not None
                and best_alias_score >= 0.78
            ):

                participant = conn.execute(
                    """
                    SELECT id, name
                    FROM participants
                    WHERE id = ?
                    """,
                    (
                        best_alias["participant_id"],
                    )
                ).fetchone()

                match_score = best_alias_score

        # ----------------------------------------------------
        # Matched participant
        # ----------------------------------------------------

        if participant:

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

            # Record merge when imported spelling differs.
            if (
                normalize_name(
                    cleaned_name
                )
                !=
                normalize_name(
                    participant["name"]
                )
            ):

                report["merged"] += 1

                report["merged_rows"].append({
                    "row": row_number,
                    "source_name": cleaned_name,
                    "canonical_name": participant["name"],
                    "amount": amount_paise / 100,
                    "similarity": round(
                        match_score,
                        3
                    )
                })

            # Remember this spelling as an alias.
            import_aliases.append({
                "canonical_name": participant["name"],
                "participant_id": participant["id"]
            })

        # ----------------------------------------------------
        # New participant
        # ----------------------------------------------------

        else:

            cursor = conn.execute(
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

            participant_id = cursor.lastrowid

            import_aliases.append({
                "canonical_name": cleaned_name,
                "participant_id": participant_id
            })

        report["imported"] += 1

    conn.commit()
    conn.close()

    return report


# ============================================================
# SETTLEMENT
# ============================================================

def generate_settlements(
    participants,
    budget
):
    """
    Generate a practical list of who pays whom.
    """

    participant_count = len(
        participants
    )

    if participant_count == 0:
        return []

    share = (
        budget / participant_count
    )

    debtors = []
    creditors = []

    for participant in participants:

        net = (
            participant["paid"]
            - share
        )

        if net < -0.005:

            debtors.append({
                "name": participant["name"],
                "amount": -net
            })

        elif net > 0.005:

            creditors.append({
                "name": participant["name"],
                "amount": net
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
            "amount": round(
                amount / 100,
                2
            )
        })

        debtors[debtor_index]["amount"] -= amount
        creditors[creditor_index]["amount"] -= amount

        if (
            debtors[debtor_index]["amount"]
            <= 0.005
        ):

            debtor_index += 1

        if (
            creditors[creditor_index]["amount"]
            <= 0.005
        ):

            creditor_index += 1

    return settlements


# ============================================================
# POOL SUMMARY
# ============================================================

def calculate_summary():
    conn = get_db()

    pool = conn.execute(
        """
        SELECT *
        FROM pool
        WHERE id = 1
        """
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

    participant_count = len(
        participants
    )

    # Equal fair share.
    share_paise = (
        budget / participant_count
        if participant_count
        else 0
    )

    participant_results = []

    for participant in participants:

        paid = participant["paid"]

        # Positive = still owes.
        # Negative = paid extra.
        balance = (
            share_paise - paid
        )

        if balance > 0.005:

            status = "owes"

        elif balance < -0.005:

            status = "credit"

        else:

            status = "settled"

        participant_results.append({
            "id": participant["id"],
            "name": participant["name"],
            "paid": round(
                paid / 100,
                2
            ),
            "share": round(
                share_paise / 100,
                2
            ),
            "balance": round(
                balance / 100,
                2
            ),
            "status": status
        })

    total_paid = sum(
        participant["paid"]
        for participant in participants
    )

    remaining = max(
        budget - total_paid,
        0
    )

    surplus = max(
        total_paid - budget,
        0
    )

    settlements = generate_settlements(
        participants,
        budget
    )

    return {
        "organizer": pool["organizer"],
        "budget": round(
            budget / 100,
            2
        ),
        "participant_count": participant_count,
        "share": round(
            share_paise / 100,
            2
        ) if participant_count else 0,
        "total_paid": round(
            total_paid / 100,
            2
        ),
        "remaining": round(
            remaining / 100,
            2
        ),
        "surplus": round(
            surplus / 100,
            2
        ),
        "participants": participant_results,
        "settlements": settlements
    }


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def index():
    return render_template(
        "index.html"
    )


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

    return jsonify(
        summary
    )


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

    # A new/updated pool starts with no participants.
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

    pool = conn.execute(
        """
        SELECT id
        FROM pool
        WHERE id = 1
        """
    ).fetchone()

    if not pool:

        conn.close()

        return jsonify({
            "error": (
                "Create a pool before adding participants"
            )
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


@app.route(
    "/api/participants/<int:participant_id>/payment",
    methods=["POST"]
)
def add_payment(participant_id):

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
            "error": (
                "Payment must be greater than 0"
            )
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


@app.route(
    "/api/import",
    methods=["POST"]
)
def import_csv():

    # Pool must exist first.
    if not calculate_summary():

        return jsonify({
            "error": (
                "Create a pool before importing contributions."
            )
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

    if not file.filename.lower().endswith(
        ".csv"
    ):

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


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    init_db()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )