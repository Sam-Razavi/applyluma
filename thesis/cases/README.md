# Evaluation cases

The cases the thesis reports on. They were added after the freeze tag
`thesis-prototype-v1`, so the prompts and rules could not be adjusted to them.

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

## Checking and running

From the repository root:

```bash
python -m thesis.eval.run --cases thesis/cases --out thesis/results/run-1
```

The runner first checks every folder and lists everything that is missing or
misspelled; nothing is sent to the model until all cases are complete.
