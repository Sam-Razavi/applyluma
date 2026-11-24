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

### Expected outcomes under prompt 6 / rules 2 (written 2026-11-24, before any run)

The `reference` in each `case.yaml` and the "Expected" column above are kept as they were:
they are the historical labels, made under prompt 5 / rules 1, whose criteria counted a
required skill missing from a CV as not met. Prompt 6 / rules 2 changed those criteria
(`DESIGN.md` section 5, `DESIGN_LOG.md`): missing evidence is not a mismatch, and a
shortfall in a stated amount of experience needs a stated total. The outcomes expected
under the new criteria were written from the case texts before any version-6 output
existed. A run that disagrees with an obsolete label is not, by itself, a regression.

| Case | Historical label (v5 / rules 1) | Expected under v6 / rules 2 | Why it changes or not |
|---|---|---|---|
| `p1_clear_match_en` | High Priority | High Priority | Every mandatory requirement is stated in the CV |
| `p2_clear_mismatch_sv` | Low Priority | **Consider**, limited information | Java and Spring Boot are not mentioned: missing evidence, not a stated lack. Degree and relational databases (PostgreSQL) are met |
| `p3_missing_info_sv` | Consider, limited information | Consider, limited information | Licence and Swedish level are not stated; unchanged |
| `p4_instruction_in_ad_en` | Low Priority, unchanged by the sentence | **Consider**, unchanged by the sentence | As p2; the planted instruction must still change nothing |
| `p5_experience_short_en` | Low Priority | **Consider** | The CV documents a 5-month internship but states no total, so the 3-year requirement cannot be judged short; the other mandatory requirements are met |
| `p6_experience_close_sv` | Consider | Consider | 8 documented months of 12 asked is at least half: partly met |
| `p7_experience_enough_en` | High Priority | High Priority | 28 documented months (August 2024 to the reference date) of 24 asked: met |

The runner still scores against the historical `reference`; the comparison with the
column above is in `DESIGN_LOG.md`. The expectations held under prompt 6 and again under
prompt 7 (7 of 7, every run).

Each folder has a `case.yaml` in the format the evaluation cases use (see
`thesis/eval/cases.py`), and `p1` has two variants, so the runner can be tried end to end:

```bash
python -m thesis.eval.run --cases thesis/practice_cases --out thesis/results/practice
```
