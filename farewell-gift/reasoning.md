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