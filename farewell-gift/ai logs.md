now how to implement this
new logical error
fix this
it's treating Ruhal Sharma and Rahul Sharma diffrently
now it's treating Ruhal Sharma and Rahlu Sharmma diffrerntly
same issue again.
give me full app.py
i changed my name 7 times and it performed well, but still a small error

Replace your entire app.py with this version. It includes the joined-name fix (Harsh Vardhan = harshvardhan) along with the previous spelling, typo, duplicate, amount-cleaning, import-report, balance, and settlement logic.

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

After replacing it, reset the test database one last time because the current database already contains the duplicate Harsh records:

Ctrl + C
rm gift.db
python app.py

Then create the pool and import your full messy CSV again.

For your specific case:

Harsh Vardhan
harshvardhan

will now normalize to the same compact name:

harshvardhan

and merge into one participant.

now give me the full reasoning.md file in a single markdown codeblock
# Project Reasoning

## 1. Problem Understanding

The goal is to build a simple application that helps an organiser manage contributions for a shared farewell gift.

The system should make it easy to answer the questions the organiser is likely to receive:

1. What is each person's fair share?
2. How much has each participant paid?
3. How much has been collected?
4. How much is still left to collect?
5. Who still owes money?
6. Who has paid extra?
7. At the end, who should pay whom so everyone reaches their fair share?
8. How should messy historical contribution data be cleaned and incorporated?

The solution was therefore designed around:

- Equal-share calculation
- Contribution tracking
- Balance calculation
- CSV import and data cleaning
- Duplicate detection
- Name matching and merging
- Settlement generation
- Import reporting

The implementation is intended to work for any organiser and any pool amount rather than being hard-coded for the example in the problem statement.

## 2. Architecture Decision

The application uses a simple three-layer architecture:

```text
Frontend
   ↓
Flask API
   ↓
SQLite Database

A single Flask application is sufficient because the problem is small in scope and does not require distributed processing.

Technologies such as microservices, Kafka, Redis, Kubernetes, or other infrastructure were intentionally avoided because they would add complexity without addressing a stated requirement.

The design prioritizes correctness, clarity, and ease of demonstration.

3. Technology Choices
Flask

Flask was selected because it is lightweight, easy to configure in GitHub Codespaces, and suitable for building the required API quickly.

SQLite

SQLite was selected because the application requires a small relational data store and does not need a separate database server.

It also makes the project easy to run in a Codespace without additional infrastructure.

HTML, CSS and JavaScript

A frontend framework was not necessary.

Vanilla JavaScript provides enough functionality for:

Calling backend APIs
Adding participants
Recording payments
Importing CSV files
Updating balances
Displaying settlement information
Displaying the import report

This keeps the project lightweight and easy to understand.

4. Data Model

The application uses two main tables.

Pool

Stores:

Organiser name
Total budget

The current implementation supports one active pool at a time because that is sufficient for the assessment.

Participants

Stores:

Participant ID
Participant name
Total amount paid

The total paid amount is increased whenever a new valid contribution is recorded.

5. Equal Share Calculation

The fair share is calculated dynamically:

Fair Share = Total Budget / Number of Participants

For example:

Budget = ₹6000
Participants = 6

Fair Share = ₹6000 / 6
           = ₹1000

The calculation is not hard-coded, so the same system works for different budgets and group sizes.

6. Balance Calculation

A participant's net financial position is calculated relative to the fair share.

Balance = Fair Share - Amount Paid

This gives three states:

Positive balance → Participant still owes money
Zero balance     → Participant is settled
Negative balance → Participant has paid extra

For example, if the fair share is ₹1000:

Paid ₹500  → Owes ₹500
Paid ₹1000 → Settled
Paid ₹1500 → Credit ₹500

This handles the case where one participant pays extra to cover another participant.

7. Currency Representation

Money is stored internally as integer paise instead of floating-point values.

For example:

₹100.50 = 10050 paise

This avoids common floating-point precision problems in currency calculations.

Values are converted back to rupees only when returned by the API or displayed in the UI.

8. Manual Payment Handling

Participants can make payments through the dashboard.

The system allows multiple payments from the same participant.

For example:

First payment  = ₹500
Second payment = ₹300

Total paid = ₹800

The participant's balance is always calculated using the updated total.

This keeps manual payments and imported historical contributions within the same balance system.

9. Settlement Logic

After calculating each participant's net position, participants are divided into two groups:

Debtors

Participants who have paid less than their fair share.

Creditors

Participants who have paid more than their fair share.

The settlement algorithm matches debtors with creditors.

For each match:

Settlement Amount =
Minimum(Debtor Outstanding, Creditor Credit)

Once one side reaches zero, the algorithm continues with the next participant.

For example:

A owes ₹500
B owes ₹1000

C has ₹500 credit
D has ₹1000 credit

A possible settlement is:

A pays ₹500 to C
B pays ₹1000 to D

This produces a compact and practical settlement list.

10. CSV Import Requirement

The extended problem introduces a messy historical contribution file.

The CSV may contain:

Duplicate rows
Different capitalisation
Extra spaces
Different punctuation
Misspelled names
Joined or separated names
Different currency formats
Invalid rows

The import process was therefore designed as a separate data-cleaning pipeline.

The flow is:

CSV File
   ↓
Validate CSV Structure
   ↓
Clean Names and Amounts
   ↓
Reject Invalid Rows
   ↓
Detect Duplicate Contributions
   ↓
Match Existing Participants
   ↓
Merge Name Variations
   ↓
Update Contribution Totals
   ↓
Generate Import Report
   ↓
Recalculate Balances
   ↓
Recalculate Settlements
11. CSV Structure Validation

The importer does not depend on exact column capitalization.

It accepts common variations of the name field such as:

name
participant
person
member
contributor

Similarly, amount fields can include:

amount
paid
payment
contribution
value

This makes the importer more tolerant of messy input files.

12. Name Normalization

Names are normalized before comparison.

The normalization process:

Removes leading and trailing whitespace.
Converts text to lowercase.
Replaces punctuation with spaces.
Collapses repeated spaces.

Examples:

" Rahul Sharma "
"rahul sharma"
"RAHUL-SHARMA"

become comparable normalized names.

The displayed canonical participant name is preserved rather than replacing it with the normalized lowercase version.

13. Joined Name Handling

The importer also compares compact forms of names.

For example:

Harsh Vardhan
harshvardhan

are converted to the same compact comparison form:

harshvardhan

This allows missing spaces between name components to be handled.

14. Fuzzy Name Matching

Exact normalized matching is attempted first.

If that does not find a match, the system uses fuzzy string comparison.

The matching logic considers:

Character order similarity
Character composition similarity
Individual name-token similarity
Minor spelling mistakes
Character rearrangements
Joined versus separated names

Examples that can be recognized as the same person include:

Rahul Sharma
rahul sharma

Ruhal Sharma
Rahul Sharmma

Rahlu Sharmma

Harsh Vardhan
harshvardhan

A similarity threshold is used to prevent unrelated names from being merged too aggressively.

The approach deliberately favors avoiding incorrect merges over forcing every name to match.

15. Why Conservative Matching Is Important

A false merge changes financial balances and can produce an incorrect settlement.

For example, automatically treating two genuinely different people as the same person would combine their contributions and distort the entire pool.

Therefore, fuzzy matching is only accepted when the names are sufficiently similar.

If the system cannot confidently identify two names as the same participant, they remain separate.

16. Matching Within the Same Import

Name matching is performed not only against participants that already exist in the database but also against participants discovered earlier in the same CSV import.

This matters when a person does not exist in the database before importing the file.

For example:

Ruhal Sharma, ₹1000
Rahlu Sharmma, ₹500
Rahul Sharma, ₹500

The importer can use the first discovered canonical participant and merge later variations into that same participant.

The final result becomes:

Ruhal Sharma → ₹2000

instead of creating three separate participants.

17. Amount Normalization

The importer supports multiple representations of currency values.

Examples include:

1000
1,000
₹1000
₹1,000
Rs. 1000
INR 1000
1000/-
1000.50

Currency labels, symbols, spaces, and formatting characters are removed before parsing.

Valid values are converted into integer paise.

18. Invalid Amount Handling

Amounts are rejected when they are:

Empty
Non-numeric
Zero
Negative

Examples:

abc
-500
0

are rejected.

Rejected rows are not added to participant balances.

19. Duplicate Detection

Duplicate contribution rows are detected within the uploaded CSV.

The duplicate key is based on the normalized participant name and parsed amount.

For example:

Rahul Sharma, 500
rahul sharma, ₹500

represent the same contribution row and are treated as duplicates.

The contribution is counted only once.

However, different legitimate payments by the same participant are preserved.

For example:

Rahul Sharma, 500
Rahul Sharma, 1000

represent two different contributions and therefore produce:

Rahul Sharma → ₹1500
20. Import Report

The application does not silently clean the imported data.

After an import, the organiser can see:

Total rows processed
Successfully imported rows
Duplicate rows removed
Merged rows
Rejected rows

The report also contains details about:

Which name was merged
Which canonical participant it was merged into
Which duplicate row was removed
Which row was rejected
Why the row was rejected

This directly addresses the requirement to report what was imported, de-duplicated, merged, and rejected.

21. Relationship Between Import and Balances

Imported contributions are added directly to the same paid total used by manual payments.

Therefore, there is only one balance calculation.

For example:

Imported payment = ₹500
Manual payment   = ₹300

Total paid = ₹800

The participant's fair share and balance are then calculated normally.

This avoids having separate accounting logic for imported and manually entered data.

22. Database Integrity

The participant name is stored with a unique database constraint.

This prevents exact duplicate participant records from being inserted through the normal participant creation flow.

The import process performs its own matching before inserting participants because spelling and formatting differences may not be caught by a simple database uniqueness constraint.

23. API Design

The backend exposes the following endpoints:

Create or update pool
POST /api/pool
Get pool summary
GET /api/pool
Add participant
POST /api/participants
Add payment
POST /api/participants/{id}/payment
Import CSV
POST /api/import
Reset pool
POST /api/reset

The API remains intentionally small and focused on the actual requirements.

24. Validation and Error Handling

The application validates input before modifying the database.

Examples include:

Missing organiser
Missing budget
Invalid budget
Zero or negative budget
Empty participant name
Duplicate participant
Invalid payment
Zero or negative payment
Unknown participant
Missing CSV
Non-CSV upload
Missing CSV name column
Missing CSV amount column
Invalid contribution rows

The backend returns error messages and appropriate HTTP status codes for invalid requests.

25. Security Considerations

Authentication and authorization were not implemented because they were not part of the stated requirements.

Basic security practices were still included:

SQL statements use parameterized values.
User-provided names are escaped before being rendered in the frontend.
Invalid input is rejected at the API layer.
No passwords, API keys, or other secrets are required.
26. UI Design

The UI was designed around the organiser's most common questions.

The dashboard highlights:

Total budget
Share per person
Total collected
Remaining amount

The participant table shows:

Participant name
Fair share
Total paid
Current balance
Payment input

The settlement section provides a direct answer to the final question of who should pay whom.

The import section provides a separate report so the organiser can understand how messy historical data was processed.

The interface uses a dashboard-style layout to make important financial information visible at a glance.

27. Edge Cases Considered

The implementation considers:

No participants
One participant
Partial payments
Multiple payments from one participant
No payment
Overpayment
Exact duplicate contribution rows
Different capitalisation
Extra spaces
Punctuation differences
Joined and separated names
Minor spelling mistakes
Different currency formats
Invalid amounts
Missing names
Missing CSV columns
Remaining amount below the target budget
Fully collected pool
Pool surplus
28. Testing Approach

The application was tested in stages.

Basic Pool Testing
Create a pool
Add participants
Verify equal share
Add payments
Verify balances
Verify remaining amount
Settlement Testing

Different combinations of:

Underpayments
Full payments
Overpayments

were tested to verify the generated settlement list.

CSV Testing

Messy CSV data was tested using:

Duplicate rows
Different capitalization
Extra spaces
Punctuation differences
Minor spelling variations
Joined names
Currency symbols
Comma-separated amounts
Invalid values
Negative amounts
Missing names
Multiple legitimate contributions

The resulting cleaned data was then checked against the balance and settlement calculations.

29. Simplicity vs Scalability

The project intentionally uses the simplest architecture that satisfies the requirements.

For this assessment, one Flask application with SQLite is sufficient.

If the application were later expanded into a larger production system, it could use:

PostgreSQL
Authentication and authorization
Multiple pools
Payment transaction history
Concurrency controls
Cloud deployment
Monitoring and logging
More advanced data import workflows

These features were not implemented because they are outside the current problem requirements.

30. Final Design Principle

The solution follows this priority:

Correctness > Completeness > Simplicity > Optimization

The final implementation focuses on correctly solving the organiser's problem while keeping the system understandable, testable, and easy to run in GitHub Codespaces.

The messy-data extension was treated as a core part of the system rather than an afterthought, because incorrect cleaning would directly lead to incorrect balances and settlements.

i need all 30 points in a single codeblock so i can just copy paste it. make it concise
# Project Reasoning

## 1. Problem Understanding

The application helps an organiser manage a shared farewell gift contribution pool.

It answers:

1. What is each person's fair share?
2. How much has each person paid?
3. How much has been collected?
4. How much remains?
5. Who owes money?
6. Who has paid extra?
7. Who should pay whom?
8. How should messy historical contribution data be cleaned?

The solution therefore focuses on share calculation, payment tracking, CSV cleaning, balance calculation, and settlement generation.

## 2. Architecture Decision

The application uses:

```text
Frontend
   ↓
Flask API
   ↓
SQLite

A single Flask application is sufficient for the problem. Microservices, Kafka, Redis, and Kubernetes were avoided because they add unnecessary complexity.

3. Technology Choices
Flask

Lightweight and suitable for a small REST API.

SQLite

Simple relational storage with no separate database server.

HTML/CSS/JavaScript

Sufficient for the dashboard, API calls, payments, and CSV import without adding frontend framework complexity.

4. Data Model

Two main tables are used:

Pool

Stores organiser and total budget.

Participants

Stores participant ID, name, and total amount paid.

One active pool is supported because that satisfies the assessment requirements.

5. Equal Share Calculation
Fair Share = Total Budget / Number of Participants

Example:

₹6000 / 6 = ₹1000 per person

The calculation is dynamic for any budget and group size.

6. Balance Calculation
Balance = Fair Share - Amount Paid

Therefore:

Positive → Owes money
Zero     → Settled
Negative → Paid extra
7. Currency Representation

Money is stored internally as integer paise.

Example:

₹100.50 = 10050 paise

This avoids floating-point precision problems.

8. Manual Payments

Multiple payments from the same participant are supported.

Example:

₹500 + ₹300 = ₹800 total paid

The balance is recalculated after every payment.

9. Settlement Logic

Participants are divided into:

Debtors: paid less than their fair share.
Creditors: paid more than their fair share.

The system repeatedly matches them using:

Settlement = Minimum(Debtor Outstanding, Creditor Credit)

This produces a compact settlement list.

10. CSV Import

Historical contributions are imported through CSV.

The importer handles:

Duplicate rows
Name variations
Messy amount formats
Invalid rows
Merging
Import reporting
11. CSV Structure Validation

The importer accepts common name columns such as:

name, participant, person, member, contributor

and amount columns such as:

amount, paid, payment, contribution, value

This makes the import tolerant of column naming differences.

12. Name Normalization

Names are normalized by:

Removing leading/trailing spaces
Converting to lowercase
Replacing punctuation
Collapsing repeated spaces

Example:

" Rahul Sharma "
"RAHUL-SHARMA"

become comparable.

13. Joined Name Handling

Compact comparison removes spaces so that:

Harsh Vardhan
harshvardhan

can be recognized as the same participant.

14. Fuzzy Name Matching

If exact matching fails, fuzzy matching is used to handle minor spelling mistakes and character rearrangements.

Examples include:

Rahul Sharma
Ruhal Sharma
Rahlu Sharmma

A similarity threshold prevents unrelated names from being merged.

15. Conservative Matching

Incorrect merges would produce incorrect financial balances.

Therefore, the system only merges names when similarity is sufficiently high. Uncertain names remain separate instead of being guessed.

16. Matching During the Same Import

The importer also compares new rows against participants already discovered earlier in the same CSV.

For example:

Ruhal Sharma, 1000
Rahlu Sharmma, 500
Rahul Sharma, 500

can become one participant with ₹2000.

17. Amount Normalization

The importer supports formats such as:

1000
1,000
₹1000
₹1,000
Rs. 1000
INR 1000
1000/-
1000.50

Values are cleaned and converted into paise.

18. Invalid Amount Handling

The following are rejected:

abc
0
-500
empty values

Rejected rows are not added to balances.

19. Duplicate Detection

Duplicate contribution rows are detected using normalized name and parsed amount.

Example:

Rahul Sharma,500
rahul sharma,₹500

is treated as one contribution.

Different valid contributions remain separate:

Rahul Sharma,500
Rahul Sharma,1000

becomes ₹1500.

20. Import Report

After import, the application reports:

Total rows
Imported rows
Duplicates removed
Merged rows
Rejected rows

Details about merged, duplicate, and rejected rows are also shown.

21. Import and Balances

Imported contributions are added to the same payment totals used by manual payments.

Example:

Imported = ₹500
Manual   = ₹300
Total    = ₹800

The same balance and settlement calculations then apply.

22. Database Integrity

The participant name has a unique database constraint.

The importer performs additional normalization and fuzzy matching because database uniqueness alone cannot detect spelling or formatting variations.

23. API Design
POST /api/pool
GET  /api/pool
POST /api/participants
POST /api/participants/{id}/payment
POST /api/import
POST /api/reset

The API is intentionally small and focused on the required functionality.

24. Validation and Error Handling

The system validates:

Organiser
Budget
Participant name
Payment amount
Duplicate participants
Participant existence
CSV file type
CSV columns
Imported contribution rows

Invalid requests return clear errors.

25. Security Considerations

Authentication was not implemented because it was not required.

Basic security practices include:

Parameterized SQL queries
Escaping user-provided names in the frontend
API-level validation
No passwords or API keys in the project
26. UI Design

The dashboard focuses on the organiser's most important information:

Budget
Share per person
Collected amount
Remaining amount

The participant table shows payment and balance information.

The settlement section shows who should pay whom.

The import section shows the cleaning report.

27. Edge Cases

The system considers:

No participants
One participant
Partial payments
Multiple payments
No payment
Overpayment
Duplicate rows
Name variations
Joined names
Spelling mistakes
Currency variations
Invalid values
Missing names
Invalid CSV structure
Fully collected pools
Remaining balances
Pool surplus
28. Testing

The application was tested with:

Normal payments
Partial payments
Overpayments
Multiple payments
Duplicate CSV rows
Capitalization differences
Extra spaces
Punctuation differences
Spelling variations
Joined names
Currency formats
Invalid amounts
Missing names
Settlement generation
29. Simplicity vs Scalability

The current Flask + SQLite architecture is sufficient for the assessment.

A larger production system could later add:

PostgreSQL
Authentication
Multiple pools
Transaction history
Concurrency control
Cloud deployment
Monitoring

These were not added because they are outside the stated requirements.

30. Final Design Principle

The implementation follows:

Correctness > Completeness > Simplicity > Optimization

The goal was to build the simplest understandable system that correctly handles the pool, balances, settlements, and messy historical contribution data without unnecessary infrastructure.