# AI Decision Journal

| Decision | Reason | Risk noticed | Safeguard |
|---|---|---|---|
| Send only the post to the LLM | Student records should remain private | Accidentally including CSV data in prompt | `call_llm()` accepts only `post` and system prompt |
| Use exactly five JSON fields | Makes validation and matching predictable | Model may add explanation or extra keys | `is_valid()` rejects unexpected keys |
| Use explicit examples in the prompt | Shows the expected output shape | Model may imitate a value not present in a new post | `check_facts()` checks each extracted value against the post |
| Do not convert percentage to CGPA | The specification forbids conversion | Percentage may be mistaken for a CGPA | Percentage-only/vague posts are sent to review |
| Retry once, then fall back | A single bad response should not crash the program | Fallback may miss nuanced wording | Uncertain criteria remain empty and status can become `needs_review` |
| Keep reports as drafts | Eligibility mistakes can affect students | Someone may share output without checking | README, console, and reports state the officer checkpoint |
| Use synthetic student data | Safe demonstration data | Real data could be committed accidentally | Dataset uses made-up names and `.gitignore` excludes secrets |

## What I would verify before a real deployment
- Test every supported branch spelling against real placement-post wording.
- Confirm the chosen API provider's data-retention and privacy settings with the institution.
- Ask the placement officer to approve criteria and output reports.
- Keep an audit record of the original post, criteria, status, and human corrections.
