# MindMatch

MindMatch is a no-account quiz app. A creator answers questions, shares a quiz link, and sees how friends scored.

## Included

- SQLite database (`mindmatch.db`, created when the server starts)
- Random public quiz IDs and private creator-results keys
- Quick Start, Mix, and Custom modes
- Friend quiz flow, scoring, answer breakdown, and creator response list
- Server-side validation: correct answers are never sent to a friend before scoring

## Run it locally

Use Python 3.10 or newer:

```powershell
python server.py
```

Open `http://localhost:8000`. Do not open `index.html` directly: the database and links need the server.

## Deploy it

Deploy this folder to a Python host that supports a persistent disk. Use `python server.py` as its start command. The server reads the host's `PORT` variable; set `HOST=0.0.0.0` if the host requires it. Use HTTPS. Back up `mindmatch.db`: it contains quizzes and responses.

For a public service, add rate limiting and move the database to a managed service. Creator results links are secret: do not share them with quiz takers.
