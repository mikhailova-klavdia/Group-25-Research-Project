# Benchmark Run Spec — RQ1 Standardisation

All four team members run this spec identically, differing only in `--team`.

---

## Team assignments

| Person | `--team` flag |
|--------|---------------|
| Karthik | `worker-critic-plus-plus` |
| Person 2 | `solo` |
| Person 3 | `worker-critic` |
| Person 4 | `human-in-the-loop` |

---

## Before you start

1. **Sync to the agreed commit**
   ```bash
   git pull origin main
   git checkout <agreed-sha>
   ```

2. **Check `.env`** has your `OPENAI_API_KEY`.

3. **Check `Papers/`** (or `papers/` on Windows — same dir) contains ranked subfolders
   `01-3M-CyteOnto` through `26-NbM-tabpfn`, each with `repo/` and `paper.pdf`.

4. **Ranks 25–26 only (sam2, tabpfn):** confirm each has a `biorxiv_link.txt`.
   If missing, create it:
   - `papers/25-NbM-sam2/biorxiv_link.txt` → `https://github.com/facebookresearch/sam2`
   - `papers/26-NbM-tabpfn/biorxiv_link.txt` → `https://github.com/PriorLabs/TabPFN`

---

## Run

Single command runs all 46 questions across all 26 repos:

```bash
uv run python run_eval.py \
  --repos 1-26 \
  --team <YOUR_TEAM> \
  --model gpt-5-mini-2025-08-07 \
  --timeout 1800
```

- `--timeout 1800` = 30 min wall-clock cap per question (kill + skip if exceeded).
- Workspaces are created fresh per question automatically.
- Results land in `papers/<folder>/runs/<run-id>/<ID>.json` as they complete.
- Expected runtime: **8–15 hours total** (~10–20 min per question average).

---

## Metrics captured per chain JSON

| Field | What it measures |
|-------|-----------------|
| `correct` | Heuristic accuracy vs `ground_truth` |
| `token_usage.total_tokens` | Total tokens consumed |
| `token_usage.estimated_cost_usd` | Estimated USD cost |
| `elapsed_seconds` | Wall-clock seconds from run start to chain saved |
| `chain` | Full T/A/O/R steps for CoT analysis |
| `failure_analysis.blocker_type` | Why the question was blocked (if it was) |

---

## After your run — collect results

Create your folder under `eval_runs/` and copy chains into it:

```
eval_runs/<YYYY-MM-DD>-<your-name>-<team>/
  chains/     ← one <ID>.json per question (copy from papers/*/runs/*/...)
  costs/      ← copy papers/*/costs.json files, rename to <slug>-costs.json
  logs/       ← terminal output (redirect stdout when running if possible)
  README.md   ← owner, date, model, team, headline score (X/46 correct)
```

Quick collect command (run from project root after all questions finish):

```bash
# Linux / Mac
find papers -path "*/runs/*/*.json" -not -name "costs.json" \
  | xargs -I{} cp {} eval_runs/<your-folder>/chains/

# Windows PowerShell
Get-ChildItem papers -Recurse -Filter "*.json" |
  Where-Object { $_.DirectoryName -match "runs\\" -and $_.Name -ne "costs.json" } |
  Copy-Item -Destination eval_runs\<your-folder>\chains\
```

Then **push your `eval_runs/<your-folder>/`** to origin/main so everyone can compare.

---

## What NOT to change

- Do not change `--model` — everyone uses `gpt-5-mini-2025-08-07`.
- Do not change `--timeout` — everyone uses `1800`.
- Do not reuse workspaces across questions.
- Do not modify `benchmark_42.csv` during your run.
