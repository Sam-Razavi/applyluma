# Design: AI-assisted job-fit assessment

Status: **design v1, decisions made on 2026-11-13** (section 10), built and tagged as
`thesis-prototype-v1` and `-v2`. **Revised on 2026-11-24: prompt version 6, rules
version 2** (decisions Q1 revised, Q9 and Q10). Changes after design v1 are recorded
in `DESIGN_LOG.md`.

This is activity 2 ("define the objectives for a solution") and the design half of
activity 3 in the design science research process of Peffers et al. (2007). The state
of the system before this work is recorded in [`docs/thesis/BASELINE.md`](../docs/thesis/BASELINE.md).

## 1. Decision problem

- **Who decides:** a recent IT graduate looking for a junior IT job.
- **The decision:** should I prioritise this vacancy?
- **The alternatives:** High Priority, Consider, Low Priority.
- **Why it is hard:** job ads list many skills without saying which are essential, and
  ask for "relevant experience" that is hard to judge when most of a graduate's
  experience comes from university projects.
- **What the system does:** it explains how the CV matches the ad, points out what is
  missing or unclear, and gives a recommendation with reasons. The choice stays with
  the job seeker.

The existing rule-based matcher answers a narrower question (how many known skill
terms overlap) with a number. It does not separate mandatory from preferred
requirements, and it cannot tell "the CV shows you lack this" from "the CV does not
say".

## 2. Objectives

Each objective is something the evaluation can check.

| # | Objective | Checked by |
|---|---|---|
| O1 | Identify the requirements in a job ad and mark each as mandatory, preferred or unclear | Review of practice and evaluation cases |
| O2 | For each requirement, say whether the CV meets it, and quote the CV text the judgement rests on | Automatic quote check; manual review sheet |
| O3 | Keep "not enough information" separate from "not met" | Scenario type 2 (unclear or missing information) |
| O4 | Derive the recommendation from the requirement judgements by documented, fixed rules | Unit tests on the rules; agreement with reference decisions |
| O5 | Give the same recommendation when the same CV and ad are assessed again | Repeated runs (scenario type 3) |
| O6 | Not change the recommendation because of irrelevant text, a different name on the CV, or instructions written inside an ad | Variant runs (scenario type 3) |
| O7 | Leave the user in control: runs only on request, states its limits, changes nothing by itself | Design review against Amershi et al. (2019) |
| O8 | Work on English and Swedish ads and CVs | Cases in both languages |
| O9 | Stay separate from the rule-based matcher, so both run on the same cases | Evaluation runner |

## 3. Requirements

Functional:

- **FR1** Input: one CV as text and one job ad as text.
- **FR2** Output: a recommendation (High Priority, Consider, Low Priority); a short
  summary; the list of requirements with importance, status and quoted evidence; a
  list of missing or unclear information; a "limited information" flag.
- **FR3** Every quote is checked against its source text. A quote that cannot be found
  is flagged. A judgement that rests on a CV quote that is not in the CV counts neither
  as met nor as not met. A mandatory requirement whose ad quote is not in the ad cannot
  make the recommendation Low or High (rules version 2).
- **FR4** Every assessment is stored with the model name, prompt version, rules
  version and the full model output.
- **FR5** In the app, an assessment starts only when the user asks for it, on one job
  at a time, and uses the user's default CV (the same CV the rule-based score uses).
- **FR6** The same service function is callable from the evaluation runner without
  the app or the database.

Non-functional:

- **Access:** administrators only until the evaluation is finished.
- **Cost:** about 0.02 USD per assessment with GPT-4o; a daily limit per user.
- **Time:** two model calls, 10 to 30 seconds; runs in the background worker.
- **Privacy:** the CV and ad text are sent to the model provider, as for CV tailoring
  today; the privacy policy is updated. The evaluation uses fictional CVs only.

## 4. Architecture

```mermaid
flowchart TD
    AD[Job ad text] --> S1
    S1["Step 1 (model): extract requirements<br/>importance + quote from the ad"] --> S2
    CV[CV text] --> S2
    S2["Step 2 (model): judge each requirement<br/>status + quote from the CV"] --> QC
    QC["Quote check (code): is each quote in its source?"] --> RULES
    RULES["Decision rules (code): fixed table"] --> OUT
    OUT["Recommendation + reasons + missing information"]
    S2 -. "model's own suggestion, stored for comparison only" .-> OUT
```

The model reads; code decides. The model is used for what rules cannot do (reading
free text in two languages). The decision itself is made by a rule table that can be
printed, tested and explained. This is the "structured decision logic combined with an
AI component" the thesis topic asks for.

Why two model calls and not one:

- Step 1 depends only on the ad, so the requirement list is not shaped by what the
  CV happens to contain.
- Errors can be located: a wrong recommendation is traced to a missed requirement
  (step 1), a wrong judgement (step 2) or the rules.

Where the code will live:

| Part | Location |
|---|---|
| Assessment logic (no database access) | `backend/app/services/fit_advisor/` |
| Storage, background task, API | `backend/app/models/fit_assessment.py`, `backend/app/tasks/fit_assessment.py`, `backend/app/api/v1/endpoints/fit_assessments.py`, migration `0035` |
| Panel in the app | `frontend/src/components/discover/fit/` |
| Cases, protocol, runner, results | `thesis/` |

## 5. Workflow in detail

### Step 1: requirements from the ad

For each requirement the model returns:

| Field | Values |
|---|---|
| `id` | R1, R2, ... |
| `text` | The requirement in one short English sentence |
| `category` | skill, experience, education, language, certification, other |
| `importance` | mandatory, preferred, unclear |
| `ad_quote` | The sentence or phrase in the ad, word for word, in the ad's language |

How importance is decided:

- **mandatory:** the ad says so ("must", "required", "you have", "krav", "ska ha",
  "vi kräver").
- **preferred:** the ad says so ("nice to have", "a plus", "meriterande", "gärna").
- **unclear:** the ad lists it without saying either.

### Step 2: evidence from the CV

For each requirement the model returns:

| Field | Values |
|---|---|
| `status` | met, partly_met, not_met, not_enough_information |
| `cv_quote` | The CV text the judgement rests on, word for word; empty if there is none |
| `note` | One sentence explaining the judgement |

It also returns a `summary` (two or three sentences), a list `missing_information`
(what the CV or the ad would need to say for a firmer answer), and its own
`model_recommendation`, which is stored but never shown as the result.

### Status definitions (decision Q1, revised 2026-11-24)

This is the most important definition in the design, because objective O3 depends on it.
Version 6 of the prompt separates **missing evidence** from **evidence of a mismatch**:

| Status | Meaning |
|---|---|
| met | The CV affirmatively shows it. A quote is required. |
| partly_met | The CV shows something relevant but less than asked: a similar tool, or a documented amount of work experience that is at least half of the amount asked. A quote is required. |
| not_met | The CV affirmatively shows a mismatch, and the CV words that show it are quoted: studies described as ongoing or ending later when a completed degree is required; a statement that the person does not have the skill or certificate; a stated total of relevant experience below half of the amount asked. |
| not_enough_information | The CV does not settle it either way: a skill, tool, certification or qualification it does not mention; a licence, work permit, citizenship, language level or willingness to travel it does not state; dates too few or unclear to total an amount of experience; a requirement too vague to judge. The note says what the CV would need to show. |

**Absence is not a mismatch.** A CV that does not mention Kubernetes does not show that
the person lacks Kubernetes, so the status is `not_enough_information`, never `not_met`.
The motivation is the concern, in work on attribution and grounding (Yue et al., 2023;
Tang et al., 2024), that a model's claim should be supported by its source, and the
observation that language models and human screeners can differ in what they infer
from a CV (Vaishampayan et al., 2025). These works motivate the rule; they did not test
it.

**Stated amounts of experience** (version 5, revised in version 6): the work periods the
CV documents are added up, an internship counting for its length and a running job up to
the reference date. At least the amount asked is met; at least half of it is partly met.
Below half is `not_met` **only when the CV itself states the total** (for example "6
months of professional experience in total") or states that there is no other relevant
work. A dated history of jobs and internships does not establish the person's complete
experience: the jobs a CV lists are not necessarily all the work a person has done. So a
documented period below half, without such a statement, is `not_enough_information`. The
half-way boundary is unchanged from version 5; it is a formative design convention, not
a finding.

Q1 as decided on 2026-11-13 made an unmentioned skill, tool or qualification "that a CV
normally lists" `not_met`, and rejected the alternative above because "a CV with none of
the required technologies could then never be Low Priority". The revision accepts that
consequence knowingly. Low Priority now needs a verified mandatory requirement that the
CV affirmatively shows is not met; a CV that is merely silent about the required
technologies gives Consider, with the missing evidence named. See section 8 (validity) and
`DESIGN_LOG.md` for what this does to the clear-mismatch scenario.

### Quote checks

Code compares every `ad_quote` with the ad and every `cv_quote` with the CV, ignoring
case, spacing and typographic variants (`evidence.py`).

- A `met`, `partly_met` **or `not_met`** whose CV quote is missing or not found in the CV
  is changed to `not_enough_information`. The model's own status is kept as
  `model_status`, with `downgraded: true` and `downgrade_reason` (`cv_quote_missing` or
  `cv_quote_not_found`). Before rules version 2 only `met` and `partly_met` were checked.
- An `ad_quote` not found in the ad marks the requirement **unverified**. It stays in the
  output, marked, and the rules treat it as below.
- **What the checks do not do.** They are literal: a quote that is found shows that the
  words exist in the source, not that they mean what the judgement says. A found CV quote
  does not prove a mismatch (or a match), and a found ad quote does not prove that the
  requirement was read correctly, for example as mandatory rather than preferred. These
  remain for the reader of the panel and for the manual review sheet of the evaluation.
- The share of quotes that pass is a transparency measure in the evaluation.

### Decision rules, version 2 (decisions Q2 to Q4, Q9)

A mandatory requirement is **verified** when its ad quote was found in the ad. A
requirement without that check counts as unverified (fail closed). Applied in this order,
after both quote checks:

| # | Condition | Recommendation |
|---|---|---|
| R1 | At least one verified mandatory requirement is `not_met` | Low Priority |
| R4 | Otherwise, at least one mandatory requirement is unverified, whatever its status | Consider, limited information |
| R2 | Otherwise, there is at least one mandatory requirement and every one is `met` | High Priority |
| R3 | Anything else | Consider |

- A verified failure (R1) is enough on its own, even beside unverified requirements.
- An unverified requirement can neither make the result Low (it may be invented) nor
  support High (a requirement judged met but not found in the ad proves nothing), so it
  gives Consider (R4) unless R1 applies.
- "Anything else" (R3) covers a mandatory requirement that is `partly_met` or
  `not_enough_information`, and an ad with no requirement marked mandatory.
- The counts in the output (`mandatory_total`, `_met`, `_not_met`, `_unknown`) are of the
  verified mandatory requirements, the ones the rules use; `mandatory_unverified` counts
  the others.

The **limited information** flag is always set by R4. Otherwise it is set when a third or
more of the mandatory requirements are `not_enough_information` or unverified, or when the
ad has no mandatory requirement. It is shown next to the recommendation.

Version 1 (2026-11-13 to 2026-11-24) had R1 to R3 without the verification condition: an
unverified requirement counted like any other.

Preferred and unclear requirements do not change the recommendation (versions 1 and 2),
verified or not; an unverified one is only marked.
They are shown and counted in the summary ("3 of 5 preferred requirements met").

Alternatives considered and not chosen for version 1:

- Low Priority only when half or more of the mandatory requirements are not met.
  Rejected because one unmet essential requirement is what the research report calls
  a clear mismatch, and a single rule is easier to explain to the user.
- Requiring half of the preferred requirements for High Priority. Rejected to keep
  the rules to the distinction the report stresses: mandatory against preferred.
- Treating an unclear requirement as mandatory. Rejected because it would turn vague
  ads into Low Priority results, when the honest answer is that the ad does not say.

### Worked examples (rules version 2)

| Case | Mandatory requirements after the quote checks | Result |
|---|---|---|
| Ad requires Python, SQL and a bachelor's degree; the CV states all three | met, met, met | High Priority (R2) |
| Same ad; the CV has Python and SQL, and says the degree is expected in 2027 | met, met, not_met | Low Priority (R1) |
| Same ad; the CV has Python and the degree but never mentions SQL | met, not_enough_information, met | Consider (R3) |
| Same ad; the CV has Python, mentions "databases" but not SQL, has the degree | met, partly_met, met | Consider (R3) |
| Ad requires Java and a driving licence; the CV has Java, says nothing about a licence | met, not_enough_information | Consider, limited information (R3) |
| Ad requires 3 years of experience; the CV shows one dated 5-month internship and states no total | not_enough_information (and the rest met) | Consider (R3) |
| Ad requires 3 years; the CV states "6 months of professional experience in total" | not_met | Low Priority (R1) |
| The model lists a mandatory requirement whose quote is not in the ad; everything else met | met, met, (unverified) | Consider, limited information (R4) |
| Same, but a verified mandatory requirement is also not met | not_met, met, (unverified) | Low Priority (R1) |
| Ad lists skills without saying which are required | (none) | Consider, limited information (R3) |

## 6. Interaction design

The panel sits in the job detail view in Discover, under the existing match score,
which is not changed. The design follows Amershi et al. (2019):

| Guideline | How the panel meets it |
|---|---|
| G1 Make clear what the system can do | One line above the button: it reads this ad and your default CV, and nothing else |
| G2 Make clear how well it can do it | "It can be wrong. Check the quoted evidence." The limited-information notice; a note on every judgement that was set aside and every mandatory requirement not found in the ad |
| G6 Mitigate social biases | The prompt tells the model to ignore name, age, gender, nationality and photo; name-swap cases test it |
| G7 Support efficient invocation | One button, on the job the user is already looking at |
| G8 Support efficient dismissal | The panel collapses; nothing else on the page depends on it |
| G10 Scope services when in doubt | "Not enough information" and Consider, never a guess presented as certain |
| G11 Make clear why it did what it did | Requirement table with importance, status and the quoted text; the rule that produced the recommendation is named |
| G12 Remember recent interactions | A stored assessment is shown again without a new model call |

Left for later: G9 (letting the user correct a requirement's status, after which the
rules would recompute the recommendation with no new model call) and G15 (feedback
buttons).

**Qualification fit, not job attractiveness (decision Q10, 2026-11-24).** Recommender
systems in recruitment pursue different objectives, for the job seeker and for the
employer (Mashayekhi et al., 2024); this one pursues only one of them. The
recommendation answers one question: does the documented background meet the job's
requirements? It does not answer whether the job is worth having for this person
(salary, location, the work itself, career plans), and it does not predict hiring. The
panel's heading says "AI assessment: qualification fit", and with every result it shows:

> This compares the qualifications shown in your CV with the job's requirements. It does
> not judge whether the job suits you (salary, location, the work itself or your plans),
> and it does not predict whether you would be hired. Whether to apply is your decision.

It replaces the earlier line "This is a recommendation. The decision is yours." The
labels High Priority, Consider and Low Priority are unchanged. The app is in English
only, so there is no Swedish wording to keep in step.

## 7. Reproducibility

- One dated GPT-4o snapshot (for example `gpt-4o-2024-08-06`), the same for the
  whole evaluation. Temperature 0 and a fixed seed.
- `PROMPT_VERSION` and `RULES_VERSION` are stored with every assessment.
- Every change to a prompt or a rule gets an entry in `thesis/DESIGN_LOG.md`: what
  changed, why, and which practice case showed the need. This is the "design as a
  search process" of Hevner et al. (2004), kept visible.
- The prompts are tuned only on practice cases. The evaluation cases are written by
  the thesis author, kept outside the repository, and added only after the prompts
  and rules are frozen and tagged.

## 8. Evaluation design

The full procedure will be in `thesis/README.md` and `thesis/protocol.yaml`. This
section fixes the design; nothing here has been run.

### Strategy

Following FEDS (Venable, Pries-Heje & Baskerville, 2016), the strategy is **Technical
Risk & Efficacy**: the main design risk is technical (can a language model judge
requirements reliably?), and evaluating with real job seekers is out of reach for
this project. Evaluation is therefore artificial throughout, in two kinds of episode:

| Episode | Purpose (FEDS) | Material | Use of the result |
|---|---|---|---|
| During the build | Formative | Practice cases written by the developer | Improve prompts and rules; every change logged |
| After the freeze | Summative | Evaluation cases written by the thesis author | Reported in the thesis; no changes afterwards without a new version |

In the terms of Hevner et al. (2004, Table 2) the methods are simulation with
artificial data, functional black-box testing, and scenarios.

### Cases

- Fictional CV and job ad pairs for junior IT roles, in English and Swedish, across
  three scenario types: clear match or mismatch; unclear or missing information;
  consistency and robustness.
- **18 cases**, one for each combination of the comparisons intended: scenario type
  (3) by language (2) by reference decision (3). Each system's result can then be
  read for every combination, and no case counts for more than one cell. The runner
  reports every combination, empty ones included, so a missing case is visible.
  (The research report allowed 12 to 18; with 12, at least six combinations would
  have had no case.)

### Reference decisions, independent of both systems

- Each case has a reference decision (High Priority, Consider, Low Priority) with a
  written rationale, made by reading the CV and the ad, **before either system runs**.
- The criteria for reference decisions are written for a human reader. They are not a
  copy of the rule-based matcher's formula, and not a copy of the rule table in
  section 5.
- A second person labels the same cases without seeing the first labels or either
  system's output, from a sheet that shows only each CV and ad, numbered in a shuffled
  order (`python -m thesis.eval.labelling sheet`). Agreement is reported (same label,
  one step apart, opposite, Cohen's kappa); disagreements are recorded and resolved by
  discussion before either system runs, and the resolution is kept in the case's
  `case.yaml`.
- The evaluation cases are kept outside the repository, and away from the developer
  of the prompts, until the prompts and rules are frozen and tagged.

A limitation to state openly: the component's rules and the reference criteria share
the idea that mandatory requirements weigh most. That is the design objective, but it
means agreement with the reference partly reflects a shared view of the problem. The
second labeller and the separately written criteria reduce this; they do not remove it.

### The baseline on the same cases

The rule-based matcher runs unchanged on the same pairs. Its score is turned into a
priority by thresholds fixed here, before any result exists, and justified from the
formula (see `docs/thesis/BASELINE.md`), not from outcomes:

| Score | Skills part | Priority |
|---|---|---|
| 86 or more | 80 or more: all or nearly all of the ad's recognised skills are in the CV (3 of 3, 4 of 4, 5 of 6) | High Priority |
| 70 to below 86 | 40 to below 80: a good part of them (2 of 3, 3 of 5, 4 of 5) | Consider |
| Below 70 | Below 40: half or fewer with little evidence (1 of 2, 2 of 4), or no recognised skill in the ad (66) | Low Priority |

### Measures

Correctness and consistency are measured separately: a system can be consistently wrong.

| Property | Measure |
|---|---|
| Correctness | Agreement with the reference decision, per system, scenario type and language; a miss by one step is reported apart from an opposite result |
| Consistency | Share of the 5 repeated runs of a case that give the same priority, whether or not it is the correct one |
| Robustness | Share of cases whose priority changes under each variant (irrelevant text in the ad, in the CV, a changed name, an instruction inside the ad), 3 runs each |
| Transparency | Share of quotes that pass the check; a review sheet on which each explanation is judged as supported by the texts or not |
| Missing or ambiguous information | Whether the information the case was built to lack is flagged; how often the limited-information flag is set |
| Reliability | Failed calls, invalid outputs, time and cost per assessment |

Every wrong recommendation and every unsupported explanation is listed with the full
output of both systems, for the failure-case analysis.

### Validity and limits

- Fictional cases written by one person may not represent real ads and CVs; findings
  hold for these scenarios and are an initial evaluation, not proof of general
  performance.
- The sample is small: results are counts and percentages, without significance tests.
- Since rules version 2, the AI component gives Low Priority only when a verified mandatory
  requirement is affirmatively not met. A case whose reference is Low because required
  skills are absent from the CV will, by design, come out Consider: a one-step miss that
  reflects the evidence-conservative definition, to be reported as such, not tuned away.
  The reference criteria are written for a human reader and must not be adjusted to
  either system's rules.
- The model is a hosted service. The model snapshot, temperature, seed, prompt and
  rules versions are stored with every run, but the provider can change behaviour
  behind a snapshot name; repeated runs measure this, they do not prevent it.
- No user study: usefulness to real job seekers is argued from the design, not measured.

## 9. Out of scope

- Changing the rule-based matcher.
- Assessing many jobs at once, or re-ranking the Discover feed.
- Training or fine-tuning a model.
- A user study. The empirical material is controlled test runs.
- Real applicants' CVs in the evaluation.

## 10. Decisions

Made by the thesis author on 2026-11-13.

| # | Question | Decision |
|---|---|---|
| Q1 | A required skill is not mentioned in the CV | `not_met` for skills, tools and qualifications; `not_enough_information` for things CVs often omit. *Superseded on 2026-11-24, see the revised Q1 below* |
| Q2 | Is one unmet mandatory requirement enough for Low Priority? | Yes |
| Q3 | Do preferred requirements affect the recommendation? | No, they are shown only |
| Q4 | Does an unclear requirement count as mandatory or preferred? | Preferred |
| Q5 | Repeated runs | 5 per case, 3 per variant |
| Q6 | Thresholds for the rule-based score | By skill coverage: High at 86 or more, Low below 70 (section 8) |
| Q7 | Who checks the reference decisions? | A second person, labelling blind |
| Q8 | How many evaluation cases? | 18: one per combination of scenario type, language and reference decision (decided 2026-11-24) |
| Q1 (revised 2026-11-24) | A required skill is not mentioned in the CV | `not_enough_information`, always. `not_met` needs CV words that show the mismatch, and a quantified shortfall needs a stated total (section 5) |
| Q9 (2026-11-24) | A requirement's quote is not found in the ad | It stays in the output, marked unverified; if mandatory, it gives Consider with limited information unless a verified mandatory requirement is not met (rules version 2) |
| Q10 (2026-11-24) | What does the recommendation claim? | Qualification fit only: not job attractiveness, not a hiring prediction; the panel says so with every result |

Still open: who the second labeller is.

## References

- Amershi, S., Weld, D., Vorvoreanu, M., et al. (2019). Guidelines for human-AI
  interaction. *Proceedings of the 2019 CHI Conference on Human Factors in Computing
  Systems*. https://doi.org/10.1145/3290605.3300233
- Mashayekhi et al. (2024). A challenge-based survey of e-recruitment
  recommendation systems. *ACM Computing Surveys*. https://doi.org/10.1145/3659942
- Hevner, A. R., March, S. T., Park, J., & Ram, S. (2004). Design science in
  information systems research. *MIS Quarterly, 28*(1), 75–105.
- Peffers, K., Tuunanen, T., Rothenberger, M. A., & Chatterjee, S. (2007). A design
  science research methodology for information systems research. *Journal of
  Management Information Systems, 24*(3), 45–77.
- Tang et al. (2024). MiniCheck: Efficient fact-checking of LLMs on grounding
  documents. *Proceedings of EMNLP 2024*. https://doi.org/10.18653/v1/2024.emnlp-main.499
- Vaishampayan et al. (2025). Human and LLM-based resume matching: An observational
  study. *Findings of NAACL 2025*. https://doi.org/10.18653/v1/2025.findings-naacl.270
- Venable, J., Pries-Heje, J., & Baskerville, R. (2016). FEDS: A framework for
  evaluation in design science research. *European Journal of Information Systems,
  25*(1), 77–89. https://doi.org/10.1057/ejis.2014.36
- Yue et al. (2023). Automatic evaluation of attribution by large language models.
  *Findings of EMNLP 2023*. https://doi.org/10.18653/v1/2023.findings-emnlp.307
