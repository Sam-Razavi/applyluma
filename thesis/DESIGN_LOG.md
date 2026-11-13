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

## Observations kept for the thesis

- The date problem is a failure mode of the AI component that the rule-based matcher
  cannot have, and it was invisible in tests with a faked model.
- In version 1 the wrong judgement moved p1 from High Priority to Consider but never to
  Low Priority, because of how the rules treat `partly_met`. In versions 2 and 3 the wrong
  `not_met` on a mandatory degree did not change p2 or p4 only because they were Low
  Priority for another reason; on a case where the degree was the only gap it would have
  produced a wrong Low Priority.
- Quote checking never fired on these cases: every quote was in its source.
