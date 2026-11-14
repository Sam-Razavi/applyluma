# Practice cases

Fictional CVs and job ads used while building the assessment, to try the prompts and
rules and to improve them. They were written by the developer of the prompts, so they are
**not** evaluation cases and nothing measured on them is reported as a result. The
evaluation cases are written separately and added only after the freeze.

| Case | Language | What it is for | Expected |
|---|---|---|---|
| `p1_clear_match_en` | English | Every mandatory requirement is stated in the CV | High Priority |
| `p2_clear_mismatch_sv` | Swedish | A mandatory technology is absent from a CV that lists its skills | Low Priority |
| `p3_missing_info_sv` | Swedish | Mandatory items a CV often omits (licence, language level); vague wording | Consider, limited information |
| `p4_instruction_in_ad_en` | English | The ad of p2's kind with a sentence telling a model how to rate | Low Priority, unchanged by the sentence |
| `p5_experience_short_en` | English | Skills fit, but 3 years of experience are required and the CV has a 5-month internship | Low Priority |
| `p6_experience_close_sv` | Swedish | 1 year of experience required, the CV shows 8 months | Consider |
| `p7_experience_enough_en` | English | 2 years required, the CV shows a running job of 28 months | High Priority |

Each folder has a `case.yaml` in the format the evaluation cases use (see
`thesis/eval/cases.py`), and `p1` has two variants, so the runner can be tried end to end:

```bash
python -m thesis.eval.run --cases thesis/practice_cases --out thesis/results/practice
```
