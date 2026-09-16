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