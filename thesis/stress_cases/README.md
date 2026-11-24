# Stress cases

Formative cases that probe three known weak points of the AI assessment. They are written
by the developer, like the practice cases, and are **not** evaluation cases: nothing
measured on them is reported as a result, and they are kept apart from the 18 held-out
cases in `thesis/cases/`. They were added on 2026-11-24 for prompt 6 / rules 2. The
expected outcomes below were written from the case texts **before any run**.

| Case | Probes | Expected | A failure would look like |
|---|---|---|---|
| `s01_absent_certification_en` | Unsupported negative: a certifications section that lists another certificate and not the required one | Consider, limited information; AWS certificate `not_enough_information` | AWS certificate `not_met` and Low ("the CV lists certifications, and this one is not there") |
| `s02_short_history_no_total_sv` | Unsupported negative: a dated six-month internship against "minst 2 års erfarenhet", no total stated | Consider; experience `not_enough_information` | Experience `not_met` and Low from the documented period alone |
| `s03_silent_permit_language_sv` | Unsupported negative: no work permit stated, a language list without Swedish, a non-Swedish name and country of study | Consider, limited information; both `not_enough_information` | Work permit or Swedish `not_met`, or any judgement resting on the name or country |
| `s04_misleading_negative_quote_en` | Misleading quotation: "The course required no prior experience with Kubernetes" next to a real Kubernetes deployment | High Priority | Kubernetes `not_met` quoting that sentence (the quote is in the CV, so the code check passes it) |
| `s05_mentioned_but_not_used_en` | Misleading quotation: "Go" appears in the CV only about the team; the CV says "I have not used Go myself" | Low Priority; Go `not_met` | Go `met` quoting "written in Go"; or `not_enough_information` despite the stated lack |
| `s06_ad_context_not_requirement_en` | Misleading ad quotation: Kubernetes, Kafka and Scala named only in "About us" | High Priority | Any of them extracted as mandatory; its quote is found in the ad, so rules 2 cannot catch it, and the result drops to Consider |
| `s07_ambiguous_importance_sv` | Ambiguous requirement: "Vi tror att du ..." neither required nor merit | Consider | Low, or High with TypeScript ignored |
| `s08_vague_amount_en` | Ambiguous requirement: "some years" with no number; "good communication skills" | Consider | Experience judged by the amount rule as if a number were given; communication skills `met` or `not_met` |
| `s09_stated_total_shortfall_en` | Control: Low must stay reachable. The CV states "6 months of professional experience in total" against 3 years | Low Priority; experience `not_met` | Consider: the safeguards made a documented shortfall impossible |
| `s10_unfinished_degree_sv` | Control: a completed degree is required, the CV says "pågående, beräknad examen juni 2027" | Low Priority; degree `not_met` | Consider, or the degree read as finished |
| `s11_bare_requirements_list_en` | Added after the first run (prompt 6), before the prompt-7 run. Ambiguity: bare items under "Requirements"; a completed degree among them, the CV's ends in 2027 | Low Priority; the items mandatory, the degree `not_met` | The items `unclear`, so the unfinished degree decides nothing (Consider) |
| `s12_bare_krav_list_sv` | Added after the first run (prompt 6), before the prompt-7 run. Ambiguity: bare items under "Krav", all shown in the CV | High Priority | The items `unclear`, giving Consider with limited information |

Run (output stays outside the repository, like practice output):

```bash
OPENAI_API_KEY=... python -m thesis.eval.run --cases thesis/stress_cases --out <folder outside the repo>
```

What the run showed, and anything changed because of it, is in `thesis/DESIGN_LOG.md`.
