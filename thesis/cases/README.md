# Evaluation cases

The cases the thesis reports on. They were added after the freeze tag
`thesis-prototype-v2`, so the prompts and rules could not be adjusted to them.

## One folder per case

```
thesis/cases/
  c01_short_name/
    cv.md        the CV, plain text
    ad.md        the job ad, plain text
    case.yaml    what the case is for and the reference decision
```

- Name folders `c01_...`, `c02_...` so they sort in order. Use only letters, digits
  and underscores.
- A folder whose name starts with `_` (such as `_template`) is ignored by the runner.
- Write the cases as if they are read on **2026-12-01**: a degree that ends in 2026
  is finished, one that ends in 2027 is not.

## Making a case

1. Copy the `_template` folder and rename the copy, for example `c01_clear_match_en`.
2. Replace the text in `cv.md` with the CV and in `ad.md` with the job ad.
3. Fill in `case.yaml`. Every line in the template explains itself.
4. For a robustness case, add the changed text as an extra file in the same folder
   (for example `cv_name_swap.md`) and list it under `variants` in `case.yaml`.

The reference decision and its rationale are written before either system is run.

## The 18 cases

One case for each combination below (`DESIGN.md` section 8, decision Q8). Tick them
off as you write them; the runner's "per cell" table shows any that are still empty.

| # | `scenario` | `language` | `reference` |
|---|---|---|---|
| 1 | clear | en | high_priority |
| 2 | clear | en | consider |
| 3 | clear | en | low_priority |
| 4 | clear | sv | high_priority |
| 5 | clear | sv | consider |
| 6 | clear | sv | low_priority |
| 7 | unclear_or_missing | en | high_priority |
| 8 | unclear_or_missing | en | consider |
| 9 | unclear_or_missing | en | low_priority |
| 10 | unclear_or_missing | sv | high_priority |
| 11 | unclear_or_missing | sv | consider |
| 12 | unclear_or_missing | sv | low_priority |
| 13 | consistency_robustness | en | high_priority |
| 14 | consistency_robustness | en | consider |
| 15 | consistency_robustness | en | low_priority |
| 16 | consistency_robustness | sv | high_priority |
| 17 | consistency_robustness | sv | consider |
| 18 | consistency_robustness | sv | low_priority |

- Cases 13 to 18 carry the variants. With six cases and four variant types, two
  variants per case would give each type three times.
- If a combination cannot be written so that it is realistic, leave it empty and say
  so in the thesis rather than forcing it; the table will show it as empty.

## The second labeller

The second labeller decides each case without seeing your labels, rationales or any
system's output.

1. When all 18 cases are written and labelled, make the sheet. Put it outside the
   repository:

   ```bash
   python -m thesis.eval.labelling sheet --cases thesis/cases --out ../labelling
   ```

   It writes `labelling_sheet.html` (only each CV and ad, as "Case 1" to "Case 18" in a
   shuffled order, so neither the folder names nor the order give anything away),
   `labelling_answers.xlsx` and `.csv` (the form to fill in), and `labelling_key.csv`
   (which number is which folder). Give the labeller the sheet and the form; keep the
   key. If you write your criteria for the decisions in `thesis/cases/CRITERIA.md`,
   the sheet starts with them.
2. When the form comes back, compare:

   ```bash
   python -m thesis.eval.labelling compare --cases thesis/cases \
       --key ../labelling/labelling_key.csv --answers ../labelling/labelling_answers.xlsx
   ```

   It lists both labels for every case, the labeller's reason where you differ, and the
   line to add to each `case.yaml`.
3. Add `second_label:` to every `case.yaml`. Discuss each disagreement and settle it;
   then `reference` is the settled decision, `first_label` is your own label if the
   discussion changed it, and `resolution` says what was decided and why. The runner
   refuses a case whose labels differ without a `resolution`.
4. Only then run the evaluation. The summary starts with the agreement between the
   two labellers.

## Checking and running

From the repository root:

```bash
python -m thesis.eval.run --cases thesis/cases --out thesis/results/run-1
```

The runner first checks every folder and lists everything that is missing or
misspelled; nothing is sent to the model until all cases are complete.
