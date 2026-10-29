# Placement Eligibility Checker

A console-based Python project for drafting placement eligibility lists from job posts. It follows the CIT AI-Native Engineering Programme project specification.

> **Important:** This creates draft reports only. A placement officer must verify every list before it is shared. The sample student names and records are fictional.

## What it does
- Reads at least 8 job posts from `data/jobs.csv`.
- Reads 20+ fictional student records from `data/students.csv`.
- Sends only each job post—not student records—to an OpenAI-compatible LLM API.
- Extracts five JSON fields and validates them.
- Retries a failed/invalid response once, then uses a conservative local fallback.
- Fact-checks branches, CGPA, backlog limits, and batch against the post.
- Matches students in Python and writes four reports.

## Project structure
```text
placement_eligibility_checker/
├── main.py
├── system_prompt.txt
├── SPECIFICATION.md
├── JUDGMENT_FRAMEWORK.md
├── COST_AND_LATENCY.md
├── AI_DECISION_JOURNAL.md
├── REFLECTION.md
├── requirements.txt
├── .gitignore
├── .env.example
├── data/
│   ├── jobs.csv
│   └── students.csv
├── tests/
│   ├── eval_harness.py
│   └── red_team_tests.md
└── outputs/
    ├── job_summary.csv
    ├── eligible.csv
    ├── review.csv
    └── summary.txt
```

## Requirements
- Python 3.10 or newer.
- The core program uses the Python standard library.
- To use the live LLM mode, an API key for the configured OpenAI-compatible endpoint is required. Do not upload a real key.

## Run locally
1. Download or clone this repository.
2. Open a terminal in the project folder.
3. Run `python main.py`.
4. Without an API key, the program uses its conservative local fallback.
5. For live LLM mode, set `OPENAI_API_KEY` as an environment variable before running. Optionally set `OPENAI_MODEL`. Never hard-code the key.

Windows PowerShell example (replace the placeholder only in your local terminal):
```powershell
$env:OPENAI_API_KEY="your-key-here"
$env:OPENAI_MODEL="gpt-4o-mini"
python main.py
```
Do not save the real key in a file that will be uploaded. `.env` is ignored by Git.

## Output files
- `outputs/job_summary.csv`: criteria, status, and eligible count per job.
- `outputs/eligible.csv`: one row per eligible student per job.
- `outputs/review.csv`: posts that require human review, with a reason.
- `outputs/summary.txt`: per-job counts and students not eligible for any matched job.

## Run the evaluation harness
```bash
python tests/eval_harness.py
```
The harness uses five controlled posts, fixed expected criteria, and fictional student records. It tests the fact-checking and eligibility rules without needing an API key. See `tests/red_team_tests.md` for the three required adversarial inputs and expected behaviour.

## Privacy and safety
- Only job-post text is sent to the LLM.
- Student records stay in local Python processing.
- Percentage requirements are never converted to CGPA.
- Unknown/vague criteria should be reviewed by a human.
- Never upload secrets, API keys, real student data, or `.env` files.
- Always verify every draft list before sharing it.

## Coursework documents
See `SPECIFICATION.md`, `system_prompt.txt`, `tests/`, `JUDGMENT_FRAMEWORK.md`, `COST_AND_LATENCY.md`, `AI_DECISION_JOURNAL.md`, and `REFLECTION.md`.

## Suggested meaningful commit history
Create these as separate commits in GitHub if your assignment requires at least three meaningful commits:
1. `Add project specification, sample CSV inputs, and system prompt`
2. `Implement criteria validation, fact checks, matching, and reports`
3. `Add evaluation harness, red-team cases, and project documentation`

These are suggested messages only; create actual commits by uploading/committing the corresponding changes in stages.
