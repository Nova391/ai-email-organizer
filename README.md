# AI Email Organizer

A local-first FastAPI service that imports Gmail messages, classifies category and priority with trained local Naive Bayes models, creates short local summaries, and stores results in SQLite. Email contents are not sent to an external AI service.

## Setup

1. Create and activate a Python 3.11+ virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. For Gmail sync, create a Google Cloud OAuth **Desktop app**, enable the Gmail API, and save the downloaded client file as `credentials.json` in the project root.
4. Start the API: `uvicorn apps.main:app --reload`
5. Open `http://127.0.0.1:8000` for the dashboard or `/docs` for the API console.

The first Gmail sync opens Google's OAuth flow and saves `token.json`. Both credential files, the database, and labeled datasets are ignored by Git.

## Workflow

- `POST /api/sync` imports Gmail messages (`limit` and `days` are configurable).
- `POST /api/organize` classifies and summarizes unprocessed messages. Send `{"reprocess": true}` to rebuild every stored summary.
- `GET /api/emails` lists messages with pagination and filters for `processed`, `category`, `priority`, and `search`.
- `GET /api/stats` returns aggregate counts.
- `POST /api/predict` classifies arbitrary email text without saving it.

Configuration variables: `EMAIL_ORGANIZER_DB`, `GMAIL_CREDENTIALS_PATH`, `GMAIL_TOKEN_PATH`, and comma-separated `CORS_ORIGINS`.

## Data and model tools

Run `python data/fetch_emails.py`, `python data/labeling_tool.py`, and then `python ml/train.py` to fetch data, label it interactively, and retrain the models.

Run the test suite with `python -m unittest discover -s tests -v`.
