# Farewell Gift Contribution Tracker

A simple web application for managing contributions toward a shared farewell gift.

## Problem

A group of people contribute toward a common gift. Everyone has an equal fair share, but actual payments may differ:

- Some people may pay their full share.
- Some may pay only part of their share.
- Someone may pay extra for another person.
- Some people may not have paid yet.

The application helps the organiser track contributions and calculate who still owes money and how the final amount can be settled.

## Features

- Create a contribution pool with an organiser and budget.
- Add participants.
- Automatically calculate the equal share per participant.
- Record payments, including multiple payments from the same participant.
- Display:
  - Total budget
  - Equal share per person
  - Total amount collected
  - Remaining amount
- Show each participant's financial status:
  - Settled
  - Owes money
  - Has credit
- Generate a simplified settlement list showing who should pay whom.
- Input validation and duplicate participant protection.
- Responsive dashboard UI.

## Technology Stack

- Python
- Flask
- SQLite
- HTML
- CSS
- JavaScript

## Project Structure

```text
farewell-gift/
├── app.py
├── requirements.txt
├── README.md
├── ai logs.md
├── reasoning.md
├── .gitignore
├── templates/
│   └── index.html
└── static/
    ├── app.js
    └── style.css