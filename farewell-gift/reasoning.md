# Project Reasoning

## 1. Problem Understanding

The goal is to build a simple system that helps an organiser manage contributions for a shared farewell gift.

The system should make it easy to:

- Create a contribution pool with a total budget.
- Add participants.
- Calculate the equal share for each participant.
- Record how much each participant has paid.
- See the total amount collected.
- See how much is still left to collect.
- Identify who still owes money.
- Identify who has paid extra.
- Generate a simple settlement list showing who should pay whom.

The implementation was designed around these core requirements rather than adding unnecessary functionality.

## 2. Architecture Decision

The application uses a simple three-layer architecture:

Frontend  
↓  
Flask API  
↓  
SQLite Database

A single Flask application is sufficient for this problem because the expected workload is small and the requirements do not require a distributed architecture.

Technologies such as microservices, Kafka, Redis, Kubernetes, or other infrastructure were not introduced because they would add complexity without providing value for the stated requirements.

## 3. Technology Choices

### Flask

Flask was selected as the backend framework because it is lightweight, simple to configure, and suitable for building a small REST API quickly.

### SQLite

SQLite was selected because the application only needs a small relational data store. It does not require a separate database server and works well in GitHub Codespaces.

### HTML, CSS and JavaScript

A frontend framework was not necessary.

Vanilla JavaScript is enough to:

- Send API requests.
- Add participants.
- Record payments.
- Update balances.
- Display settlement results dynamically.

This keeps the implementation simple and easy to understand.

## 4. Data Model

The application uses two main tables.

### Pool

Stores:

- Organiser name
- Total budget

The current implementation supports one active pool at a time because that is sufficient for the assessment.

### Participants

Stores:

- Participant ID
- Participant name
- Total amount paid

Whenever a participant makes a payment, the total paid amount is increased.

## 5. Equal Share Calculation

The fair share for each participant is calculated as:

Fair Share = Total Budget / Number of Participants

For example:

Budget = ₹6000  
Participants = 6

Fair Share = ₹6000 / 6 = ₹1000

This calculation is dynamic, so the system works with different budgets and different numbers of participants.

## 6. Balance Calculation

Each participant's position is calculated relative to their fair share.

Net Balance = Amount Paid - Fair Share

This produces three states:

- Negative balance: the participant still owes money.
- Zero balance: the participant is settled.
- Positive balance: the participant has paid extra.

For example, if the fair share is ₹1000:

- Paid ₹500 → Owes ₹500
- Paid ₹1000 → Settled
- Paid ₹1500 → Credit ₹500

This model also handles the case where one participant pays extra to cover another participant.

## 7. Settlement Logic

After calculating every participant's balance, the participants are divided into two groups:

### Debtors

Participants who have paid less than their fair share.

### Creditors

Participants who have paid more than their fair share.

The settlement algorithm matches debtors with creditors.

For each match:

Settlement Amount = Minimum(Debtor Outstanding, Creditor Credit)

The smaller balance is completed first, and the remaining balance is then matched with the next participant.

For example:

C owes ₹500  
E owes ₹1000

D has ₹500 credit  
F has ₹1000 credit

The system can produce:

C pays ₹500 to D  
E pays ₹1000 to F

This gives the organiser a direct and practical settlement list.

## 8. Money Representation

Money values are stored internally as integer paise instead of floating-point numbers.

For example:

₹100.50 = 10050 paise

This avoids common floating-point precision problems when performing currency calculations.

## 9. API Design

The backend exposes the following endpoints:

POST /api/pool

Creates or updates the contribution pool.

GET /api/pool

Returns the current pool summary, participants, balances, and settlements.

POST /api/participants

Adds a participant.

POST /api/participants/{id}/payment

Adds a payment to a participant's total.

POST /api/reset

Resets the current pool and participants.

The API design is intentionally small because only the required functionality is implemented.

## 10. Validation and Error Handling

The application validates input before modifying the database.

The following cases are handled:

- Missing organiser name
- Missing or invalid budget
- Zero or negative budget
- Missing participant name
- Duplicate participant
- Invalid payment amount
- Zero or negative payment
- Payment for a participant who does not exist

The API returns appropriate error messages and HTTP status codes for invalid requests.

## 11. Security Considerations

Authentication was not implemented because it was not part of the stated requirements.

However, basic security practices were included:

- SQL queries use parameterized values.
- User-provided participant names are escaped before being rendered in the frontend.
- Invalid input is rejected at the API level.

These measures reduce common risks such as SQL injection and unsafe HTML rendering.

## 12. UI Design

The UI was designed around the questions the organiser is most likely to ask.

The dashboard prominently displays:

- Total budget
- Equal share per person
- Total collected
- Remaining amount

The participant table provides:

- Participant name
- Fair share
- Amount paid
- Current balance
- Payment input

The settlement section provides the final actionable result.

The goal was to allow the organiser to understand the state of the pool quickly without navigating through multiple screens.

## 13. Edge Cases Considered

The implementation considers:

- No participants
- One participant
- Partial payments
- Multiple payments from the same participant
- No payment from a participant
- Overpayment by a participant
- Duplicate participant names
- Invalid payment values
- Remaining amount below the target budget
- Fully collected pool

These cases were tested during development.

## 14. Simplicity vs Scalability

The solution intentionally prioritizes simplicity because this is a placement assessment and the requirements are limited.

The chosen architecture is sufficient for a small number of users and participants.

For a larger production system, the architecture could later be extended with:

- PostgreSQL
- Authentication and authorization
- Multiple contribution pools
- Payment transaction history
- Concurrency control
- Cloud deployment
- Monitoring and logging

These features were not implemented because they are not required by the current problem.

## 15. Final Design Principle

The implementation follows this priority:

Correctness > Completeness > Simplicity > Optimization

The final solution focuses on correctly solving the organiser's actual problem while keeping the system easy to understand, run, test, and maintain.

## 16. Handling the Messy Contribution Import

The problem was extended to include a messy list of historical contributions. The imported data may contain duplicate entries, inconsistent name spellings, inconsistent amount formats, and invalid rows.

The import process was designed as a separate data-cleaning step before updating participant balances.

The flow is:

CSV File  
↓  
Validate CSV structure  
↓  
Clean names and amounts  
↓  
Reject invalid rows  
↓  
Detect duplicate contribution rows  
↓  
Match existing participant names  
↓  
Merge valid contributions  
↓  
Update participant balances  
↓  
Generate import report

## 17. Name Normalization

Names are normalized before comparison.

The normalization process:

- Removes leading and trailing spaces.
- Converts names to lowercase.
- Removes punctuation.
- Converts multiple spaces into a single space.

For example:

" Rahul Sharma "  
"rahul sharma"  
"RAHUL-SHARMA"

are converted into comparable normalized forms.

This allows formatting differences to be handled without changing the participant's displayed name.

## 18. Fuzzy Name Matching

Exact normalized matching is performed first.

If no exact match is found, a conservative fuzzy matching approach is used with `SequenceMatcher`.

For example:

Rahul Sharma  
Rahul Sharmma

can be recognized as likely referring to the same participant.

A similarity threshold is used so that unrelated names are not aggressively merged.

This is intentionally conservative because incorrectly merging two different people would produce incorrect financial balances.

## 19. Amount Normalization

Contribution amounts can appear in different formats.

Examples supported include:

1000  
1,000  
₹1000  
₹1,000  
Rs. 1000  
INR 1000  
1000/-  
1000.50

The application removes currency symbols, labels, commas, spaces, and other formatting characters before converting the value into paise.

Negative, empty, or non-numeric amounts are rejected.

## 20. Duplicate Detection

Duplicate contribution rows are detected using the normalized participant name and parsed contribution amount.

For example:

Rahul Sharma, 500  
rahul sharma, ₹500

represent the same contribution row and are treated as duplicates.

A duplicate is not added to the participant's total a second time.

However, different valid contributions from the same participant are not treated as duplicates.

For example:

Rahul Sharma, 500  
Rahul Sharma, 1000

are treated as two separate contributions and Rahul's total becomes ₹1500.

## 21. Invalid Row Handling

Invalid rows are not silently ignored.

A row is rejected if:

- The participant name is missing.
- The amount is missing.
- The amount cannot be parsed.
- The amount is zero or negative.

Each rejected row is recorded in the import report along with its row number and rejection reason.

This makes the data-cleaning process transparent to the organiser.

## 22. Import Report

After importing the CSV, the application reports:

- Total rows processed
- Successfully imported rows
- Duplicate rows removed
- Rows merged with existing participants
- Rejected rows

The report also provides details about merged names, duplicate rows, and rejected rows.

This satisfies the requirement to report what happened to the messy input instead of silently modifying the data.

## 23. Import and Existing Balances

Imported contributions are added to the same participant payment totals used by the normal application.

Therefore, imported data and manually entered payments use the same balance calculation and settlement logic.

This avoids having two separate balance systems.

For example:

Imported contribution = ₹500  
Manual payment = ₹300

Total paid = ₹800

The participant's balance is then calculated using the same fair-share calculation as every other participant.

## 24. Important Data Integrity Decision

The system prioritizes avoiding incorrect merges over maximizing the number of automatic merges.

If the application cannot confidently determine that two names refer to the same person, it keeps them separate rather than guessing.

This is important because an incorrect merge can change financial balances and produce an incorrect settlement.

## 25. Testing the Messy Import

The import functionality was tested with combinations of:

- Exact duplicate rows
- Names with different capitalization
- Names with extra spaces
- Names with punctuation differences
- Minor spelling variations
- Currency symbols
- Comma-separated amounts
- Invalid amounts
- Negative amounts
- Missing names
- Multiple legitimate contributions from one person

The resulting cleaned data was then used by the existing balance and settlement calculations.