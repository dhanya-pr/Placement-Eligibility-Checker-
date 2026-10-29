"""Offline evaluation harness: five hand-checkable test posts, no API needed."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from main import check_facts, job_status, is_eligible, load_students  # noqa: E402

students = [
    {"roll": "T01", "name": "Test CSE", "branch": "CSE", "cgpa": 8.0, "backlogs": 0, "batch": 2027},
    {"roll": "T02", "name": "Test IT", "branch": "IT", "cgpa": 7.0, "backlogs": 0, "batch": 2027},
    {"roll": "T03", "name": "Test MECH", "branch": "MECH", "cgpa": 7.5, "backlogs": 1, "batch": 2027},
    {"roll": "T04", "name": "Test ECE", "branch": "ECE", "cgpa": 6.9, "backlogs": 1, "batch": 2026},
    {"roll": "T05", "name": "Test CSE old batch", "branch": "CSE", "cgpa": 9.0, "backlogs": 0, "batch": 2026},
]

tests = [
    {
        "name": "E1 named branches, CGPA, no backlog, batch",
        "post": "CSE and IT students of the 2027 batch. Minimum CGPA 7.5. No backlogs.",
        "criteria": {"branches": ["CSE", "IT"], "min_cgpa": 7.5, "max_backlogs": 0, "batch": 2027, "summary": "CSE IT CGPA 7.5+ no backlogs 2027"},
        "expected_status": "matched", "expected_count": 1,
    },
    {
        "name": "E2 any branch and CGPA",
        "post": "Any branch can apply. CGPA 6.5 or above.",
        "criteria": {"branches": ["ALL"], "min_cgpa": 6.5, "max_backlogs": None, "batch": None, "summary": "Any branch CGPA 6.5+"},
        "expected_status": "matched", "expected_count": 5,
    },
    {
        "name": "E3 percentage only",
        "post": "CSE students with at least 70 percent in all semesters.",
        "criteria": {"branches": ["CSE"], "min_cgpa": None, "max_backlogs": None, "batch": None, "summary": "CSE"},
        "expected_status": "needs_review", "expected_count": 0,
    },
    {
        "name": "E4 named branch but no CGPA",
        "post": "ECE students of the 2027 batch. No active backlogs.",
        "criteria": {"branches": ["ECE"], "min_cgpa": None, "max_backlogs": 0, "batch": 2027, "summary": "ECE max backlogs 0 2027"},
        "expected_status": "needs_review", "expected_count": 0,
    },
    {
        "name": "E5 vague top 10 percent",
        "post": "Students from any branch, top 10 percent only.",
        "criteria": {"branches": ["ALL"], "min_cgpa": None, "max_backlogs": None, "batch": None, "summary": "ALL"},
        "expected_status": "needs_review", "expected_count": 0,
    },
]

failures = 0
print("OFFLINE EVALUATION HARNESS")
print("-" * 72)
for case in tests:
    checked = check_facts(case["criteria"], case["post"])
    status = job_status(checked)
    count = sum(is_eligible(student, checked) for student in students) if status == "matched" else 0
    ok = status == case["expected_status"] and count == case["expected_count"]
    print(f'{case["name"]}: expected {case["expected_status"]}/{case["expected_count"]}, got {status}/{count} -> {"PASS" if ok else "FAIL"}')
    if not ok:
        failures += 1
print(f"\nResult: {len(tests) - failures}/{len(tests)} tests passed.")
sys.exit(1 if failures else 0)
