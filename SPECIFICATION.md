# Placement Eligibility Checker — One-page Specification

**Domain:** Careers / college placements  
**Purpose:** Read job posts from `data/jobs.csv`, extract stated eligibility criteria, compare them with made-up student records in `data/students.csv`, and write draft eligibility reports.

## Privacy and data flow
The LLM receives only the text of one job post and the system prompt. Student CSV records are loaded and compared locally in Python and are never included in an API request. Output lists are drafts; a placement officer must verify every list before it is shared.

## Criteria JSON
The extractor returns exactly five fields: `branches` (allowed branch codes or `ALL`), `min_cgpa` (0–10 or null), `max_backlogs` (whole number or null), `batch` (year or null), and `summary` (12 words or fewer). The program validates the structure and types, retries once if the reply fails, then uses a conservative local fallback. Only these five fields are retained.

## Fact checks and status
Every extracted branch and numeric criterion is checked against the original post. A branch is accepted only when named. `ALL` is accepted only for “any branch” or “all branches”. A CGPA is accepted only when the post explicitly states a CGPA/GPA; a percentage is never converted. A batch year is accepted only when tied to “batch”. “No backlogs” means zero. A job is `needs_review` when no verified branch or no verified CGPA remains; otherwise it is `matched`.

## Eligibility
A student matches when their branch is in the allowed list (or `ALL`), their CGPA is greater than or equal to the cut-off, their backlogs are no greater than the stated maximum (if any), and their batch matches (if specified). CSV CGPA values are converted to floats before comparison.

## Edge cases
1. A post asks for a percentage or vague “top 10 percent” without a CGPA: no conversion or guessing; mark `needs_review`.
2. A post contains instructions to add a student or invent a branch: ignore those instructions; only stated criteria are considered.
3. Invalid JSON, missing fields, extra fields, invalid types, or API failure: retry once, then use the conservative fallback and review incomplete criteria.

## Outputs
`outputs/job_summary.csv`, `outputs/eligible.csv`, `outputs/review.csv`, and `outputs/summary.txt`. All results are drafts and must be checked by the placement officer.
