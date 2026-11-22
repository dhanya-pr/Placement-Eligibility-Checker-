
import os
import re
import json
import time
import pandas as pd

from dotenv import load_dotenv
from google import genai


# --------------------------------
# 1. Load API Key
# --------------------------------

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("Gemini API key not found in .env file")

client = genai.Client(api_key=API_KEY)

MODEL = "gemini-3.8-flash"

JOB_FILE = "job.csv"
STUDENT_FILE = "student.csv"
PROMPT_FILE = "system_prompt.txt"

OUTPUT_FOLDER = "outputs"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# --------------------------------
# 2. Load System Prompt
# --------------------------------

def load_prompt():

    with open(PROMPT_FILE, "r", encoding="utf-8") as file:
        return file.read()


# --------------------------------
# 3. Load CSV Files
# --------------------------------

def load_jobs():

    return pd.read_csv(JOB_FILE)


def load_students():

    students = pd.read_csv(STUDENT_FILE)

    students["cgpa"] = pd.to_numeric(
        students["cgpa"], errors="coerce"
    )

    students["backlogs"] = pd.to_numeric(
        students["backlogs"], errors="coerce"
    )

    students["batch"] = pd.to_numeric(
        students["batch"], errors="coerce"
    )

    return students


# --------------------------------
# 4. Read Criteria using Gemini API
# --------------------------------

def read_criteria(post, system_prompt):

    prompt = f"""
    {system_prompt}

    Extract criteria from this job post:

    {post}

    Return JSON with exactly these fields:
    branches, min_cgpa, max_backlogs, batch, summary.
    """

    for attempt in range(2):

        try:

            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config={
                    "response_mime_type": "application/json"
                }
            )

            data = json.loads(response.text)

            if is_valid(data):
                return data

            print("Invalid response. Retrying...")

        except Exception as error:

            print(f"API error, attempt {attempt + 1}: {error}")

        time.sleep(1)

    print("Using fallback criteria.")

    return {
        "branches": [],
        "min_cgpa": None,
        "max_backlogs": None,
        "batch": None,
        "summary": "Could not extract criteria"
    }


# --------------------------------
# 5. Validate LLM Response
# --------------------------------

def is_valid(data):

    required = {
        "branches",
        "min_cgpa",
        "max_backlogs",
        "batch",
        "summary"
    }

    if not isinstance(data, dict):
        return False

    if set(data.keys()) != required:
        return False

    if not isinstance(data["branches"], list):
        return False

    allowed = {
        "CSE", "IT", "AIDS", "ECE",
        "EEE", "MECH", "CIVIL", "ALL"
    }

    if not all(
        isinstance(b, str) and b in allowed
        for b in data["branches"]
    ):
        return False

    if "ALL" in data["branches"] and len(data["branches"]) != 1:
        return False

    cgpa = data["min_cgpa"]

    if cgpa is not None:
        if isinstance(cgpa, bool):
            return False
        if not isinstance(cgpa, (int, float)):
            return False
        if not 0 <= cgpa <= 10:
            return False

    backlog = data["max_backlogs"]

    if backlog is not None:
        if type(backlog) != int or backlog < 0:
            return False

    batch = data["batch"]

    if batch is not None:
        if type(batch) != int:
            return False

    if not isinstance(data["summary"], str):
        return False

    if len(data["summary"].split()) > 12:
        return False

    return True


# --------------------------------
# 6. Check Facts Against Original Post
# --------------------------------

BRANCH_ALIASES = {
    "CSE": ["cse", "computer science"],
    "IT": ["it", "information technology"],
    "AIDS": ["aids", "ai&ds", "ai and ds"],
    "ECE": ["ece"],
    "EEE": ["eee"],
    "MECH": ["mech", "mechanical"],
    "CIVIL": ["civil"]
}


def check_facts(criteria, post):

    text = post.lower()

    # Check branches
    mentioned = []

    for branch, aliases in BRANCH_ALIASES.items():

        for alias in aliases:

            pattern = r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])"

            if re.search(pattern, text):
                mentioned.append(branch)
                break

    if re.search(r"\b(any branch|all branches)\b", text):
        valid_branches = ["ALL"]
    else:
        valid_branches = mentioned

    branches = criteria["branches"]

    if branches == ["ALL"] and valid_branches != ["ALL"]:
        branches = []
    elif branches != ["ALL"]:
        branches = [
            b for b in branches if b in valid_branches
        ]

    # Check CGPA only when explicitly mentioned
    cgpa_match = re.search(
        r"(?:cgpa|gpa)\s*(?:of\s*)?(?:is\s*)?"
        r"(?:minimum\s*)?(?:at least\s*)?"
        r"(\d+(?:\.\d+)?)"
        r"|(?:minimum\s*)?(\d+(?:\.\d+)?)\s*cgpa",
        text
    )

    factual_cgpa = None

    if cgpa_match:
        number = next(
            (x for x in cgpa_match.groups() if x is not None),
            None
        )
        if number:
            value = float(number)
            if 0 <= value <= 10:
                factual_cgpa = value

    if criteria["min_cgpa"] != factual_cgpa:
        factual_cgpa = None

    # Check backlog rule
    factual_backlogs = None

    if re.search(r"\b(no|zero)\s+(active\s+)?backlogs?\b", text):
        factual_backlogs = 0

    else:
        backlog_match = re.search(
            r"(?:maximum|max|up to|upto)\s+(\d+)\s+backlogs?",
            text
        )

        if backlog_match:
            factual_backlogs = int(backlog_match.group(1))

    if criteria["max_backlogs"] != factual_backlogs:
        factual_backlogs = None

    # Check batch
    batch_match = re.search(r"\b(20\d{2})\s+batch\b", text)

    factual_batch = (
        int(batch_match.group(1))
        if batch_match else None
    )

    if criteria["batch"] != factual_batch:
        factual_batch = None

    return {
        "branches": branches,
        "min_cgpa": factual_cgpa,
        "max_backlogs": factual_backlogs,
        "batch": factual_batch,
        "summary": criteria["summary"]
    }


# --------------------------------
# 7. Determine Job Status
# --------------------------------

def job_status(criteria):

    if not criteria["branches"]:
        return "needs_review"

    if criteria["min_cgpa"] is None:
        return "needs_review"

    return "matched"


# --------------------------------
# 8. Check Student Eligibility
# --------------------------------

def is_eligible(student, criteria):

    branches = criteria["branches"]

    if "ALL" not in branches:
        if student["branch"] not in branches:
            return False

    if student["cgpa"] < criteria["min_cgpa"]:
        return False

    if criteria["max_backlogs"] is not None:

        if student["backlogs"] > criteria["max_backlogs"]:
            return False

    if criteria["batch"] is not None:

        if student["batch"] != criteria["batch"]:
            return False

    return True


# --------------------------------
# 9. Write Four Output Reports
# --------------------------------

def write_reports(job_results, eligible_rows,
                  review_rows, students, matched_rolls):

    job_df = pd.DataFrame(job_results)

    eligible_df = pd.DataFrame(
        eligible_rows,
        columns=[
            "job_id", "company", "roll",
            "name", "branch", "cgpa",
            "backlogs", "batch"
        ]
    )

    review_df = pd.DataFrame(
        review_rows,
        columns=[
            "job_id", "company", "post", "reason"
        ]
    )

    job_df.to_csv(
        OUTPUT_FOLDER + "/job_summary.csv",
        index=False
    )

    eligible_df.to_csv(
        OUTPUT_FOLDER + "/eligible.csv",
        index=False
    )

    review_df.to_csv(
        OUTPUT_FOLDER + "/review.csv",
        index=False
    )

    # Find students eligible for no job
    no_job = students[
        ~students["roll"].isin(matched_rolls)
    ]

    with open(
        OUTPUT_FOLDER + "/summary.txt",
        "w",
        encoding="utf-8"
    ) as file:

        file.write("PLACEMENT ELIGIBILITY SUMMARY\n")
        file.write("=" * 40 + "\n\n")

        for job in job_results:

            file.write(
                f"{job['job_id']} - {job['company']}\n"
            )

            file.write(
                f"Eligible Students: {job['eligible_count']}\n"
            )

            file.write(
                f"Status: {job['status']}\n\n"
            )

        file.write("\nSTUDENTS ELIGIBLE FOR NO JOB\n")
        file.write("=" * 40 + "\n")

        for _, student in no_job.iterrows():

            file.write(
                f"{student['roll']} - {student['name']}\n"
            )


# --------------------------------
# 10. Main Function
# --------------------------------

def main():

    print("PLACEMENT ELIGIBILITY CHECKER")
    print("=" * 40)

    jobs = load_jobs()
    students = load_students()

    system_prompt = load_prompt()

    job_results = []
    eligible_rows = []
    review_rows = []

    matched_rolls = set()

    for _, job in jobs.iterrows():

        print(f"\nProcessing: {job['company']}")

        criteria = read_criteria(
            job["post"],
            system_prompt
        )

        criteria = check_facts(
            criteria,
            job["post"]
        )

        status = job_status(criteria)

        eligible_count = 0

        if status == "matched":

            for _, student in students.iterrows():

                if is_eligible(student, criteria):

                    eligible_count += 1

                    matched_rolls.add(student["roll"])

                    eligible_rows.append({
                        "job_id": job["id"],
                        "company": job["company"],
                        "roll": student["roll"],
                        "name": student["name"],
                        "branch": student["branch"],
                        "cgpa": student["cgpa"],
                        "backlogs": student["backlogs"],
                        "batch": student["batch"]
                    })

        else:

            review_rows.append({
                "job_id": job["id"],
                "company": job["company"],
                "post": job["post"],
                "reason": "Missing or unverified branch / CGPA criteria"
            })

        job_results.append({
            "job_id": job["id"],
            "company": job["company"],
            "branches": ", ".join(criteria["branches"]),
            "min_cgpa": criteria["min_cgpa"],
            "max_backlogs": criteria["max_backlogs"],
            "batch": criteria["batch"],
            "status": status,
            "eligible_count": eligible_count
        })

        print("Status:", status)
        print("Eligible students:", eligible_count)

    write_reports(
        job_results,
        eligible_rows,
        review_rows,
        students,
        matched_rolls
    )

    print("\n" + "=" * 40)
    print("PROCESS COMPLETED SUCCESSFULLY!")
    print("Four output files created in outputs folder.")


# --------------------------------
# 11. Run Program
# --------------------------------

if __name__ == "__main__":

    try:
        main()

    except Exception as error:

        print("Program Error:", error)
