# Design log

Every change to the prompts (`PROMPT_VERSION`) or the decision rules (`RULES_VERSION`)
after design v1, with the reason and the practice case that showed the need. Kept so
the search for a working design (Hevner et al., 2004, guideline 6) stays visible.

| Date | Prompt | Rules | Change | Why |
|---|---|---|---|---|
| 2026-11-13 | 1 | 1 | First implementation of `thesis/DESIGN.md` v1 | First run on the four practice cases: the pinned model and strict schemas work, every quote was found in its source, and the instruction planted in the ad of p4 was ignored. But a degree dated 2023-2026 was judged `partly_met` or `not_met` ("not yet completed"), which turned the clear match p1 into Consider. The model does not know today's date. |
| 2026-11-13 | 2 | 1 | The date is passed with the CV, with a rule that a period ending before today is completed. Added: a specific example meets a category requirement (PostgreSQL meets "relational databases"). `assess()` takes `today`, so the evaluation can fix the date. | p1 became High Priority. p4 still judged the same degree `not_met`: only a year is given, and the model read "2026" as later than a date in 2026. |
| 2026-11-13 | 3 | 1 | Rule for year-only end dates: completed if the year is this year or earlier. | Worse: p2 and p4 both judged the degree `not_met` ("ongoing until 2026"), in all three runs. A rule in the system prompt does not override the model's own sense of the current year. |
| 2026-11-13 | 4 | 1 | The user message states the year in plain words before and after the CV: "Any study or job period in the CV that ends in 2026 or earlier has ended." (the year is filled in by code). | All four practice cases give the expected recommendation, with identical requirement statuses in three runs each. Recommendations never changed across runs in any version; what changed was single requirement judgements. |
| 2026-11-14 | 5 | 1 | Made after the freeze tag `thesis-prototype-v1` and before any evaluation case was written. (a) A rule for a stated amount of work experience: add up the work periods in the CV; met when the total reaches the amount, partly met from half of it, not met below half or with no relevant work. (b) The judgement's fields are written in the order quote, note, status, and the note must state the numbers. (c) Silence about a driving licence, work permit, citizenship, language or travel is always "not enough information". (d) Experience of a kind of work asked without a number is never "not met" when a job, internship or project in the CV involved it. (e) A quote is one unbroken piece of the CV. Three practice cases added (p5 to p7). | The first assessment in the live app (a real ad asking for "at least 4 years in a similar role", a CV with internships) judged that requirement "not enough information" and gave Consider, against a rule-based score of 94; the quote the model offered was not in the CV. Version 4 had no rule for how far short is too short. See the iterations below. |

### Prompt version 5: the iterations

Each step was run on all seven practice cases, five runs each.

| Step | Change | Result |
|---|---|---|
| 1 | The amount rule alone | p5 (5 months against 3 years) correct. p6 (8 months against 1 year) Low Priority in 4 of 5 runs and p7 (28 months against 2 years) Consider in 5 of 5: the model chose the status first and then wrote a note that contradicted it ("2 years and 4 months ... slightly more than half of the required 2 years"). |
| 2 | Status moved after quote and note in the output; the note must give total, amount asked and half of it in months | p5 to p7 correct in every run. But p3 turned Low Priority: the driving licence was now "not met" ("something a CV would typically list"). Reordering the fields changed judgements that the amount rule has nothing to do with. |
| 3 | Rule (c); the amount rule limited to requirements that state a number | p3 correct in 3 of 5 runs: "relevant experience of support" was "not met" in two runs although the CV describes an internship helping users. Seven quotes failed the check: the model had joined a heading to an item ("Skills" + "SQL"). |
| 4 | Rules (d) and (e) | All seven cases correct in 5 of 5 runs, identical requirement statuses across runs, 154 of 154 CV quotes found, both variants of p1 unchanged. |

## Observations kept for the thesis

- The date problem is a failure mode of the AI component that the rule-based matcher
  cannot have, and it was invisible in tests with a faked model.
- In version 1 the wrong judgement moved p1 from High Priority to Consider but never to
  Low Priority, because of how the rules treat `partly_met`. In versions 2 and 3 the wrong
  `not_met` on a mandatory degree did not change p2 or p4 only because they were Low
  Priority for another reason; on a case where the degree was the only gap it would have
  produced a wrong Low Priority.
- Quote checking never fired on these cases: every quote was in its source.
- Version 5 showed that a language model does not reliably do arithmetic and a verdict in
  one step: asked for the verdict first, it produced notes that contradicted it. Having it
  write the evidence and the numbers before the verdict removed this on the practice
  cases. The decision itself still comes from the fixed rules.
- A change aimed at one kind of requirement (amounts of experience) changed judgements on
  unrelated ones (a driving licence). Every prompt change therefore has to be rerun on all
  practice cases, not only on the case that motivated it.
- The half-way threshold for "partly met" is a design choice, not a finding. It was set
  before any evaluation case existed.
