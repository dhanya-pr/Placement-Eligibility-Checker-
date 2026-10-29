# Judgment Framework

| Tool part | What could go wrong? | Wrongly left out | Wrongly included | Rule / mitigation | Human checkpoint |
|---|---|---|---|---|---|
| LLM extraction | A branch or cut-off is misread | Eligible student misses an opportunity | Ineligible student appears on list | Strict schema, two attempts, examples, fallback | Officer checks the source post and criteria |
| JSON validator | Missing/extra fields or bad types accepted | Valid criteria discarded | Invalid criteria used | `is_valid()` checks exact five fields and types | Officer reviews incomplete criteria |
| Fact checker | LLM invents branch, CGPA or batch | True criterion may be removed after mismatch | Student matched using an unstated criterion | `check_facts()` compares extracted values with post text | Officer checks post wording |
| Eligibility matcher | Wrong comparison or string CGPA | Student above cut-off excluded | Student below cut-off included | Numeric conversion; inclusive CGPA boundary; optional backlog/batch limits | Officer checks list against official requirements |
| CSV input | Wrong/malformed student data | Valid student skipped | Incorrect record matched | Conversion with `try/except`; invalid row is skipped with warning | Placement cell checks source spreadsheet |
| Reports | Stale or misleading output | A job's eligible list omitted | Wrong list sent onward | Output is labelled draft; report status and review reason shown | **Placement officer checks every list before it is shared** |
| Privacy boundary | Student data sent to provider | Not applicable | Privacy exposure | API receives only job-post text; no student records in prompt or request | Review code and API logs/settings |

## Comparing error costs
A **wrongly left-out** student may lose a legitimate placement opportunity. A **wrongly included** student can cause an inaccurate list to be sent to a company and may expose student information. Both matter; the system therefore does not automatically send lists. The placement officer checks the original post, the extracted criteria, and every draft list before sharing.
