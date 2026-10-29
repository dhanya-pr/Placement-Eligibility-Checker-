"""Placement Eligibility Checker.

Only job-post text is sent to the LLM. Student records remain in Python.
Run: python main.py
Optional LLM configuration: set OPENAI_API_KEY and (optionally) OPENAI_MODEL.
"""
import csv
import json
import os
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
PROMPT_PATH = ROOT / "system_prompt.txt"
ALLOWED_BRANCHES = {"CSE", "IT", "AIDS", "ECE", "EEE", "MECH", "CIVIL"}
CRITERIA_FIELDS = ("branches", "min_cgpa", "max_backlogs", "batch", "summary")


def load_jobs(path):
    """Load job posts from CSV, returning a list of dictionaries."""
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_students(path):
    """Load student records and convert numeric fields to numeric types."""
    students = []
    with open(path, newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            try:
                row["cgpa"] = float(row["cgpa"])
                row["backlogs"] = int(row["backlogs"])
                row["batch"] = int(row["batch"])
                students.append(row)
            except (ValueError, TypeError) as exc:
                print(f"Skipping invalid student row {row.get('roll', '?')}: {exc}")
    return students


def extract_json(text):
    """Parse a JSON object, allowing a surrounding Markdown code fence."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("No JSON object found")
    return json.loads(cleaned[start:end + 1])


def is_valid(criteria):
    """Validate the LLM response structure and allowed field types."""
    if not isinstance(criteria, dict):
        return False
    if set(criteria.keys()) != set(CRITERIA_FIELDS):
        return False
    branches = criteria["branches"]
    if not isinstance(branches, list) or not all(
        isinstance(branch, str) and (branch in ALLOWED_BRANCHES or branch == "ALL")
        for branch in branches
    ):
        return False
    if len(set(branches)) != len(branches):
        return False
    cgpa = criteria["min_cgpa"]
    if cgpa is not None and (isinstance(cgpa, bool) or not isinstance(cgpa, (int, float)) or not 0 <= cgpa <= 10):
        return False
    backlogs = criteria["max_backlogs"]
    if backlogs is not None and (isinstance(backlogs, bool) or not isinstance(backlogs, int) or backlogs < 0):
        return False
    batch = criteria["batch"]
    if batch is not None and (isinstance(batch, bool) or not isinstance(batch, int) or batch < 2000 or batch > 2100):
        return False
    if not isinstance(criteria["summary"], str) or len(criteria["summary"].split()) > 12:
        return False
    return True


def call_llm(post, system_prompt):
    """Send only the job post and system prompt to an OpenAI-compatible chat API."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Extract criteria from this job post only:\n" + post},
        ],
    }
    request = Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=45) as response:
        result = json.loads(response.read().decode("utf-8"))
    return result["choices"][0]["message"]["content"]


def fallback_criteria(post):
    """Conservative local fallback when the API is unavailable or fails validation.

    It deliberately leaves uncertain criteria empty instead of guessing.
    """
    upper = post.upper()
    branch_patterns = {
        "CSE": r"\bCSE\b|COMPUTER SCIENCE",
        "IT": r"\bIT\b|INFORMATION TECHNOLOGY",
        "AIDS": r"\bAI\s*&?\s*DS\b|\bAI&DS\b|\bAIDS\b|ARTIFICIAL INTELLIGENCE",
        "ECE": r"\bECE\b|ELECTRONICS AND COMMUNICATION",
        "EEE": r"\bEEE\b|ELECTRICAL AND ELECTRONICS",
        "MECH": r"\bMECH(?:ANICAL)?\b",
        "CIVIL": r"\bCIVIL\b",
    }
    branches = [name for name, pattern in branch_patterns.items() if re.search(pattern, upper)]
    if re.search(r"\bANY BRANCH\b|\bALL BRANCHES\b", upper):
        branches = ["ALL"]

    cgpa_match = re.search(r"(?:(?:CGPA|GPA)\s*(?:OF\s*)?(?:AT LEAST|MINIMUM|MIN\.?)?\s*([0-9]+(?:\.[0-9]+)?)|([0-9]+(?:\.[0-9]+)?)\s*(?:CGPA|GPA))", upper)
    min_cgpa = float(next(group for group in cgpa_match.groups() if group)) if cgpa_match else None
    if min_cgpa is not None and not 0 <= min_cgpa <= 10:
        min_cgpa = None

    if re.search(r"\bNO (?:ACTIVE )?BACKLOGS?\b|\bZERO BACKLOGS?\b", upper):
        max_backlogs = 0
    else:
        backlog_match = re.search(r"(?:MAX(?:IMUM)?\s*)?(\d+)\s+(?:ACTIVE\s+)?BACKLOGS?", upper)
        max_backlogs = int(backlog_match.group(1)) if backlog_match else None

    batch_match = re.search(r"\b(20\d{2})\s+BATCH\b|\bBATCH\s+(20\d{2})\b", upper)
    batch = int(next(group for group in batch_match.groups() if group)) if batch_match else None

    # Percentage is not converted to CGPA. Fallback summary stays within 12 words.
    summary_parts = []
    summary_parts.append(", ".join(branches) if branches else "branches unclear")
    if min_cgpa is not None:
        summary_parts.append(f"CGPA {min_cgpa:g}+")
    if max_backlogs is not None:
        summary_parts.append(f"max backlogs {max_backlogs}")
    if batch is not None:
        summary_parts.append(str(batch))
    summary = " ".join(summary_parts).split()
    return {
        "branches": branches,
        "min_cgpa": min_cgpa,
        "max_backlogs": max_backlogs,
        "batch": batch,
        "summary": " ".join(summary[:12]),
    }


def read_criteria(post, system_prompt):
    """Try the LLM response twice; validate, fact-check, then use safe fallback."""
    for attempt in range(2):
        try:
            raw = call_llm(post, system_prompt)
            criteria = extract_json(raw)
            if is_valid(criteria):
                checked = check_facts(criteria, post)
                if is_valid(checked):
                    return checked, "llm"
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError, RuntimeError, json.JSONDecodeError) as exc:
            print(f"LLM attempt {attempt + 1} failed: {exc}")
        except Exception as exc:
            print(f"Unexpected LLM error on attempt {attempt + 1}: {exc}")
        time.sleep(0.2)
    criteria = fallback_criteria(post)
    return check_facts(criteria, post), "fallback"


def check_facts(criteria, post):
    """Remove branches/numbers not explicitly supported by the original post."""
    upper = post.upper()
    branch_names = {
        "CSE": [r"\bCSE\b", r"COMPUTER SCIENCE"],
        "IT": [r"\bIT\b", r"INFORMATION TECHNOLOGY"],
        "AIDS": [r"\bAI\s*&?\s*DS\b", r"\bAIDS\b", r"ARTIFICIAL INTELLIGENCE"],
        "ECE": [r"\bECE\b", r"ELECTRONICS AND COMMUNICATION"],
        "EEE": [r"\bEEE\b", r"ELECTRICAL AND ELECTRONICS"],
        "MECH": [r"\bMECH(?:ANICAL)?\b"],
        "CIVIL": [r"\bCIVIL\b"],
    }
    valid_branches = []
    for branch in criteria["branches"]:
        if branch == "ALL":
            if re.search(r"\bANY BRANCH\b|\bALL BRANCHES\b", upper):
                valid_branches.append(branch)
        elif any(re.search(pattern, upper) for pattern in branch_names[branch]):
            valid_branches.append(branch)

    # Do not infer CGPA from percentages or from a number unrelated to CGPA.
    cgpa_match = re.search(r"(?:(?:CGPA|GPA)\s*(?:OF\s*)?(?:AT LEAST|MINIMUM|MIN\.?)?\s*([0-9]+(?:\.[0-9]+)?)|([0-9]+(?:\.[0-9]+)?)\s*(?:CGPA|GPA))", upper)
    min_cgpa = criteria["min_cgpa"]
    if cgpa_match:
        written_cgpa = float(next(group for group in cgpa_match.groups() if group))
        if min_cgpa is None or abs(float(min_cgpa) - written_cgpa) > 0.0001:
            min_cgpa = None
    else:
        min_cgpa = None

    if re.search(r"\bNO (?:ACTIVE )?BACKLOGS?\b|\bZERO BACKLOGS?\b", upper):
        max_backlogs = 0 if criteria["max_backlogs"] == 0 else None
    else:
        backlog_match = re.search(r"(?:MAX(?:IMUM)?\s*)?(\d+)\s+(?:ACTIVE\s+)?BACKLOGS?", upper)
        max_backlogs = criteria["max_backlogs"]
        if backlog_match:
            if max_backlogs != int(backlog_match.group(1)):
                max_backlogs = None
        else:
            max_backlogs = None

    batch_match = re.search(r"\b(20\d{2})\s+BATCH\b|\bBATCH\s+(20\d{2})\b", upper)
    batch = criteria["batch"]
    if batch_match:
        written_batch = int(next(group for group in batch_match.groups() if group))
        if batch != written_batch:
            batch = None
    else:
        batch = None

    # Preserve only supported values; build a concise summary from confirmed facts.
    parts = []
    if valid_branches:
        parts.append(", ".join(valid_branches))
    if min_cgpa is not None:
        parts.append(f"CGPA {min_cgpa:g}+")
    if max_backlogs is not None:
        parts.append(f"max backlogs {max_backlogs}")
    if batch is not None:
        parts.append(str(batch))
    summary = " ".join(" ".join(parts).split()[:12])
    return {
        "branches": valid_branches,
        "min_cgpa": min_cgpa,
        "max_backlogs": max_backlogs,
        "batch": batch,
        "summary": summary,
    }


def job_status(criteria):
    """A post needs officer review when branches or CGPA are missing."""
    if not criteria["branches"] or criteria["min_cgpa"] is None:
        return "needs_review"
    return "matched"


def is_eligible(student, criteria):
    """Apply the specified branch, CGPA, backlog and batch rules."""
    if not criteria["branches"] or criteria["min_cgpa"] is None:
        return False
    branch_ok = "ALL" in criteria["branches"] or student["branch"] in criteria["branches"]
    cgpa_ok = student["cgpa"] >= float(criteria["min_cgpa"])
    backlog_ok = criteria["max_backlogs"] is None or student["backlogs"] <= criteria["max_backlogs"]
    batch_ok = criteria["batch"] is None or student["batch"] == criteria["batch"]
    return branch_ok and cgpa_ok and backlog_ok and batch_ok


def write_reports(jobs, students, results, output_dir):
    """Write all four required reports."""
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_rows, eligible_rows, review_rows = [], [], []
    eligible_rolls = set()

    for job, criteria, status, source, reason in results:
        matches = [student for student in students if status == "matched" and is_eligible(student, criteria)]
        for student in matches:
            eligible_rolls.add(student["roll"])
            eligible_rows.append({
                "job_id": job["id"], "company": job["company"], "roll": student["roll"],
                "name": student["name"], "branch": student["branch"], "cgpa": student["cgpa"],
                "backlogs": student["backlogs"], "batch": student["batch"],
            })
        summary_rows.append({
            "job_id": job["id"], "company": job["company"], "criteria": criteria["summary"],
            "branches": "|".join(criteria["branches"]), "min_cgpa": criteria["min_cgpa"],
            "max_backlogs": criteria["max_backlogs"], "batch": criteria["batch"],
            "status": status, "eligible_count": len(matches), "criteria_source": source,
        })
        if status == "needs_review":
            review_rows.append({
                "job_id": job["id"], "company": job["company"], "post": job["post"],
                "reason": reason or "Missing or unverified branch/CGPA criteria",
            })

    def write_csv(filename, rows):
        if not rows:
            # Keep a useful header for empty reports.
            headers = {
                "job_summary.csv": ["job_id", "company", "criteria", "branches", "min_cgpa", "max_backlogs", "batch", "status", "eligible_count", "criteria_source"],
                "eligible.csv": ["job_id", "company", "roll", "name", "branch", "cgpa", "backlogs", "batch"],
                "review.csv": ["job_id", "company", "post", "reason"],
            }[filename]
        else:
            headers = list(rows[0].keys())
        with open(output_dir / filename, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

    write_csv("job_summary.csv", summary_rows)
    write_csv("eligible.csv", eligible_rows)
    write_csv("review.csv", review_rows)

    no_job_students = [s for s in students if s["roll"] not in eligible_rolls]
    with open(output_dir / "summary.txt", "w", encoding="utf-8") as handle:
        handle.write("PLACEMENT ELIGIBILITY CHECKER — SUMMARY\n")
        handle.write("DRAFT ONLY: placement officer must verify every list before sharing.\n\n")
        for row in summary_rows:
            handle.write(f'{row["job_id"]} | {row["company"]}: {row["eligible_count"]} eligible | {row["status"]}\n')
        handle.write("\nStudents eligible for no matched job yet:\n")
        for student in no_job_students:
            handle.write(f'{student["roll"]} — {student["name"]}\n')
        if not no_job_students:
            handle.write("None\n")


def main():
    jobs = load_jobs(DATA_DIR / "jobs.csv")
    students = load_students(DATA_DIR / "students.csv")
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    results = []
    print(f"Loaded {len(jobs)} jobs and {len(students)} made-up student records.")
    if not os.getenv("OPENAI_API_KEY"):
        print("No OPENAI_API_KEY found: using conservative local fallback for this run.")
    for job in jobs:
        criteria, source = read_criteria(job["post"], system_prompt)
        status = job_status(criteria)
        reason = ""
        if status == "needs_review":
            missing = []
            if not criteria["branches"]:
                missing.append("no verified branch criterion")
            if criteria["min_cgpa"] is None:
                missing.append("no verified CGPA cut-off")
            reason = " and ".join(missing)
        results.append((job, criteria, status, source, reason))
        print(f'{job["id"]}: {status}; criteria source={source}; {criteria["summary"]}')
    write_reports(jobs, students, results, OUTPUT_DIR)
    print(f"\nReports written to: {OUTPUT_DIR}")
    print("Reminder: these are draft lists. A placement officer must check them before sharing.")


if __name__ == "__main__":
    main()
