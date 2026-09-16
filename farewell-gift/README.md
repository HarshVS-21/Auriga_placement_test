# Farewell Gift Contribution Tracker

A simple web application for tracking contributions toward a shared farewell gift, calculating fair shares, monitoring the remaining amount, and generating a simple settlement plan.

The application also supports importing messy historical contribution data, cleaning it, merging participant name variations, removing duplicate entries, rejecting invalid rows, and reporting what happened during the import.

---

## Problem

A group of people are contributing toward a farewell gift with a shared budget.

Although everyone agrees to contribute equally, actual payments can differ:

- Some participants pay their full share.
- Some pay only part of their share.
- Someone may pay extra to cover another participant.
- Some participants may not pay anything.
- Historical contribution records may contain duplicate rows, inconsistent names, inconsistent amount formats, and invalid data.

The application helps the organiser answer:

- What is each person's fair share?
- How much has each person paid?
- How much has been collected?
- How much is still left to collect?
- Who still owes money?
- Who has paid extra?
- Who should pay whom to settle everything fairly?
- What happened to the messy imported contribution data?

---

## Features

### Pool Management

- Create a contribution pool.
- Specify the organiser.
- Specify any total budget.
- Automatically calculate the equal share per participant.

### Participant Management

- Add participants.
- Prevent duplicate participant names.
- Display each participant's fair share.
- Display each participant's total paid amount.
- Display each participant's current balance.

### Payment Tracking

- Add payments manually.
- Support multiple payments from the same participant.
- Handle partial payments.
- Handle overpayments.

### Dashboard

The dashboard displays:

- Total budget
- Equal share per person
- Total amount collected
- Remaining amount to collect

### Settlement

The application identifies:

- Participants who still owe money.
- Participants who have paid extra.
- A simple list of who should pay whom.

### Messy CSV Import

The application can import historical contribution data and handle:

- Duplicate rows
- Different capitalization
- Extra spaces
- Punctuation differences
- Minor spelling mistakes
- Joined and separated names
- Inconsistent currency formats
- Invalid amounts
- Missing participant names

The import process reports:

- Total rows
- Successfully imported rows
- Duplicate rows removed
- Merged rows
- Rejected rows

---

## Technology Stack

- Python
- Flask
- SQLite
- HTML
- CSS
- JavaScript

---

## Architecture

The application uses a simple architecture:

```text
Browser
   ↓
Flask Application / REST API
   ↓
SQLite Database