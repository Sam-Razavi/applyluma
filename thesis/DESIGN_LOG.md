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
| 2026-11-24 | 6 | 2 | (a) Missing CV evidence is no longer a mismatch: an unmentioned skill, tool, certification or qualification is `not_enough_information`; `not_met` needs CV words that show the mismatch; a shortfall in a stated amount of experience needs a total the CV states. (b) Code sets aside a `not_met` with no CV quote or one not in the CV, as it already did for `met`, and records `downgrade_reason`. (c) A mandatory requirement whose ad quote is not in the ad is unverified (fail closed when the check is missing) and cannot give Low or High: rule order R1, R4 (new), R2, R3. (d) The panel separates qualification fit from job attractiveness. Made after `thesis-prototype-v2`, before any evaluation case existed. | A methodology review found that Q1 let silence count as non-qualification, and that one unmet mandatory requirement gives Low, so the most consequential result could rest on no evidence; and that an invented or misquoted requirement still reached the rules. See "Prompt 6 / rules 2" below. |

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

## Prompt 6 / rules 2 (2026-11-24)

### What was wrong

- **Silence counted as a mismatch.** Q1 (2026-11-13) made a skill, tool or qualification
  that "a CV normally lists" `not_met` when the CV did not mention it, and the version-5
  prompt said "a CV always lists the jobs a person has had". A CV not mentioning
  Kubernetes does not show that the person lacks it. Because one unmet mandatory
  requirement gives Low Priority (Q2), the system's most consequential result could rest
  on the absence of text.
- **No check on negative judgements.** Code set aside a `met` or `partly_met` whose CV
  quote was not in the CV, but accepted any `not_met`, with or without a quote.
- **Unverified ad requirements decided.** `service.py` computed `ad_quote_found`, but
  `decide()` ignored it: a requirement the model invented or misquoted could make the
  result Low, or count towards High.
- **Fit and attractiveness were not separated** in the panel, so High Priority could be
  read as "a good job for me" or "likely to be hired".

### Why (literature and method)

The change follows a methodology review and the supervisor's points that the system
must support, not make, the decision; that qualification fit and job attractiveness are
different questions; and that criteria must be explicit. Work on attribution and
grounding (Yue et al., 2023; Tang et al., 2024) treats a model's claim as acceptable only
when its source supports it; Vaishampayan et al. (2025) observe differences between
language-model and human readings of CVs; Mashayekhi et al. (2024) describe
recruitment recommenders as serving several, different objectives. These works motivated
the changes. None of them tested these particular rules.

### Alternatives considered

- **Keep Q1, tightened:** `not_met` only when an itemised skills list is quoted and the
  skill is absent from it. It would have kept the clear-mismatch scenario reachable for
  the AI component. Put to the thesis author on 2026-11-24 and not chosen: a list that
  omits a skill is still silence.
- **A third model call to verify each judgement** (an entailment check in the spirit of
  MiniCheck). Not chosen: a further model whose own errors would need evaluating, more
  cost, and a change of architecture late in the project. Literal quote checks in code
  are deterministic and testable; their limit is stated below.
- **Dropping unverified requirements before the rules.** Not chosen: with an unmet
  unverified requirement removed, the verified rest could give High on less evidence. R4
  keeps them visible and stops them from deciding either way.
- **Letting an unverified requirement judged met pass.** Not chosen (thesis author,
  2026-11-24): a requirement not found in the ad proves nothing, so it gives Consider even
  when judged met.

### What changed

| Part | Change |
|---|---|
| `prompts.py` (`PROMPT_VERSION` 5 to 6) | Status definitions as in `DESIGN.md` section 5; a CV quote is required for `not_met`; the "CV normally lists" and "a CV always lists the jobs" assumptions removed; for a stated amount of experience, below half is `not_met` only with a total the CV states, otherwise `not_enough_information`. The half-way boundary, the reference-date wording, the field order and the schemas are unchanged |
| `service.py` | The quote check covers `not_met`; `downgrade_reason` (`cv_quote_missing`, `cv_quote_not_found`); `model_status` kept for audit |
| `decision.py` (`RULES_VERSION` 1 to 2) | Verified and unverified mandatory requirements; order R1, R4, R2, R3; R4 always sets limited information; counts of verified requirements plus `mandatory_unverified`; a missing `ad_quote_found` counts as unverified |
| `FitAssessmentPanel.tsx`, `types/fitAssessment.ts` | Heading "AI assessment: qualification fit"; the fit-versus-attractiveness text with every result; notes for a set-aside `not_met` and for an unverified mandatory requirement; new optional fields |
| Not changed | The rule-based matcher and its thresholds, `protocol.yaml`, the runner's measures, the model snapshot, temperature and seed, the database (no migration) |

### Tests

Mocked (the model is faked; these pin what the code does with its answers):

- `test_fit_advisor_decision.py`, 21 tests: rules 2, including scenarios 10 to 17 (an
  invented unmet requirement cannot give Low; an unverified one blocks High whatever its
  status; a verified failure beside an unverified one stays Low; only unverified ones
  give Consider with limited information; an unverified preferred one does not take away
  High; fail closed; R4 sets the flag below a third; counts).
- `test_fit_advisor_service.py`, 32 tests: scenarios 1 to 11 and 16 (an unmentioned
  Kubernetes is not Low; a CV that states the lack is Low; an unfinished degree is Low;
  full evidence is High; positive and negative judgements without a found quote are set
  aside, with the reason; quantified experience met, partly met, not settled, and a
  stated total below half; a pinned limit: a found quote is not checked for meaning;
  preferred and unclear never give Low; an invented requirement cannot give Low), and a
  prompt test that pins the removed assumptions and the rules for dates, licences,
  skills, certifications and experience.
- `FitAssessmentPanel.test.tsx`, 13 tests, scenarios 18 to 21.

Formative, real model (GPT-4o `gpt-4o-2024-08-06`, temperature 0, seed 20261113,
reference date 2026-12-01), the seven practice cases, 41 assessments, run on 2026-11-24
from the uncommitted working tree that became this change:

| Case | Historical label | Expected under v6 (written before the run) | Result, 5 runs (3 per variant) |
|---|---|---|---|
| p1 (and both variants) | High | High | High in all runs |
| p2 | Low | Consider | Consider in 5 of 5 |
| p3 | Consider | Consider | Consider in 5 of 5 |
| p4 | Low | Consider | Consider in 5 of 5; the planted instruction changed nothing |
| p5 | Low | Consider | Consider in 5 of 5 |
| p6 | Consider | Consider | Consider in 5 of 5 |
| p7 | High | High | High in 5 of 5 |

- Every changed judgement against the run of 2026-11-21 (prompt 5) is a requirement the
  CV does not show: Java and Spring Boot in p2 and p4, three years of experience in p5,
  and five preferred skills, from `not_met` to `not_enough_information`. The model gave
  these statuses itself; the code set nothing aside (0 downgrades).
- 231 of 231 ad quotes and 154 of 154 CV quotes were found, so R4 never fired and the new
  `not_met` check never fired on real output. Both are exercised by the mocked tests
  only.
- 0 failed calls; 0.44 USD in total, 0.0108 USD per assessment.

### Limits that remain

- **Low is now rare.** It needs a verified mandatory requirement the CV affirmatively
  fails: an unfinished degree, a stated lack, a stated total of experience. A CV silent
  about every required technology gives Consider. In the 18-case evaluation, Low
  references that rest on missing skills will be one-step misses by design.
- **Literal checks only.** A found CV quote does not prove a mismatch, and a found ad
  quote does not prove that importance was read correctly. If the model says `not_met`
  and quotes a dated period, the code keeps it (pinned in a test); the prompt, not the
  code, is the guard there.
- **Stated totals.** A quantified shortfall is confirmed only when the CV states a total
  or states that there is no other work. Few CVs do, so most experience requirements below
  the amount asked will be `not_enough_information` or `partly_met`.
- **The prompt change shifted an unrelated judgement.** In p7, "Experience with Azure"
  (preferred, listed under Skills) was `met` in 2 runs and `partly_met` in 3; on
  2026-11-21 it was `met` in 4 of 5. The words "affirmatively shows" may have made the
  model stricter about a bare listed skill. It is a preferred requirement here, so the
  priority did not change. On a mandatory requirement it could move a case between High
  and Consider.
- **A listed skill still meets a qualified requirement.** "Strong knowledge of Java" was
  judged met in p5 from "Java" in a skills list. That is positive evidence of the skill,
  not of its level; the reader of the panel sees the quote.
- **Stored assessments in the app** made under prompt 5 / rules 1 stay as they were and
  are shown with their versions until "Run again".
- **The browser extension popup** shows the recommendation without the
  fit-versus-attractiveness text (outside this change).

### Versions

Prompt 6, rules 2, protocol 1 (unchanged), model `gpt-4o-2024-08-06`. Proposed freeze tag
for the evaluation candidate: `thesis-prototype-v3`, on the merge of this change. The
tags `pre-thesis-baseline`, `thesis-prototype-v1` and `thesis-prototype-v2` are kept.

### How this change was made (LLM-assisted, human-directed development)

The application's GPT-4o is a component of the system. Separately, ApplyLuma has been
developed with Claude (Claude Code) as a programming assistant, directed by the thesis
author, for exploring ideas and alternatives, choosing implementation strategies,
architecture and trade-offs, finding limitations, and testing and debugging. The repository
history records commits, not which lines an assistant drafted, so no such attribution is
claimed for earlier work.

For this change, as recorded in this session on 2026-11-24:

- **The thesis author** specified the three changes and their acceptance criteria. They
  decided the open points: absence is always "not enough information"; any unverified
  mandatory requirement blocks High; missing verification metadata fails closed; a
  quantified shortfall needs a stated total; R4 always sets limited information.
- **Claude:**
  - inspected the code and documents, and pointed out that the change reverses Q1 and
    turns practice cases p2, p4 and p5 from Low to Consider;
  - proposed the tightened-Q1 alternative (not chosen), the rule order, the counts and
    the fail-closed flag;
  - wrote the code, tests and documentation in this commit;
  - ran the checks and the formative practice run reported above.
- **Verifiable from the repository:** the diff and this entry. **Recorded here only:**
  the decisions above and the practice-run figures (the run's output is kept outside
  the repository, as practice output always is).
