"""
clone_benchmark.py — one command to set up everything for benchmark_42.csv.

Reads benchmark_42.csv from the project root, clones every repo into
papers/<slug>/repo/, and downloads the paper PDF into papers/<slug>/paper.pdf.

Usage:
    uv run python clone_benchmark.py           # set up all 16 repos
    uv run python clone_benchmark.py --dry-run # preview without doing anything
    uv run python clone_benchmark.py --repos CyteOnto SEGMA  # specific repos only
"""

import argparse
import csv
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT       = Path(__file__).parent
PAPERS_DIR = ROOT / "papers"
CSV_PATH   = ROOT / "benchmark_42.csv"

# ── GitHub URLs for every repo in benchmark_42.csv ─────────────────────────
# Verify these before running — if a clone fails the script tells you clearly.
GITHUB_URLS: dict[str, str] = {
    "CyteOnto":         "https://github.com/bhklab/CyteOnto",
    "GWAS-Epistasis-Bias": "https://github.com/tobsecret/GWAS-Epistasis-Bias",
    "USHER":            "https://github.com/yatisht/usher",
    "sentieon-cli":     "https://github.com/Sentieon/sentieon-cli",
    "GWProt":           "https://github.com/NikolaiKrogh/GWProt",
    "LARIS":            "https://github.com/theislab/LARIS",
    "SC-Framework":     "https://github.com/theislab/sc-framework",
    "SEGMA":            "https://github.com/Arcadia-Science/segma",
    "ScisTreeCNA":      "https://github.com/khuranalab/ScisTreeCNA",
    "distortions":      "https://github.com/Arcadia-Science/distortions",
    "ARCADIA_public":   "https://github.com/Arcadia-Science/ARCADIA_public",
    "RegFormer":        "https://github.com/bowang-lab/RegFormer",
    "fadvi":            "https://github.com/Arcadia-Science/fadvi",
    "PPLM":             "https://github.com/junliu621/PPLM",
    "metapointfinder":  "https://github.com/aldertzomer/metapointfinder",
    "CrossPPI":         "https://github.com/drugparadigm/CrossPPI",
}


def load_csv() -> dict[str, str]:
    """Return {repo_slug: biorxiv_url} from benchmark_42.csv."""
    if not CSV_PATH.exists():
        print(f"ERROR: {CSV_PATH} not found. Run from the project root.", file=sys.stderr)
        sys.exit(1)
    repos: dict[str, str] = {}
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            slug = row["repo"].strip()
            url  = row["biorxiv_link"].strip()
            if slug and url and slug not in repos:
                repos[slug] = url
    return repos


def pdf_url(biorxiv_url: str) -> str:
    """Convert a biorxiv abstract URL to the full-PDF URL."""
    base = biorxiv_url.rstrip("/")
    if not base.endswith(".full.pdf"):
        base = base + ".full.pdf"
    return base


def clone_repo(slug: str, github_url: str, repo_path: Path, dry_run: bool) -> bool:
    """Git clone into repo_path. Returns True on success."""
    if repo_path.exists() and any(repo_path.iterdir()):
        print(f"    repo/ already exists — skip clone")
        return True
    if dry_run:
        print(f"    [dry-run] would clone {github_url}")
        return True
    print(f"    cloning {github_url} ...")
    result = subprocess.run(
        ["git", "clone", "--depth", "1", github_url, str(repo_path)],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"    cloned OK")
        return True
    print(f"    CLONE FAILED (exit {result.returncode})")
    if result.stderr:
        for line in result.stderr.strip().splitlines():
            print(f"      {line}")
    return False


def download_pdf(slug: str, biorxiv_url: str, pdf_path: Path, dry_run: bool) -> bool:
    """Download paper PDF from bioRxiv. Returns True on success."""
    if pdf_path.exists() and pdf_path.stat().st_size > 10_000:
        print(f"    paper.pdf already exists — skip download")
        return True
    url = pdf_url(biorxiv_url)
    if dry_run:
        print(f"    [dry-run] would download {url}")
        return True
    print(f"    downloading paper PDF ...")
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp, \
             open(pdf_path, "wb") as f:
            f.write(resp.read())
        size_kb = pdf_path.stat().st_size // 1024
        print(f"    downloaded paper.pdf ({size_kb} KB)")
        return True
    except Exception as exc:
        print(f"    PDF download failed: {exc}")
        print(f"    Manual fix: download {url}")
        print(f"      and save to {pdf_path.relative_to(ROOT)}")
        return False


def setup_repo(slug: str, biorxiv_url: str, dry_run: bool) -> tuple[bool, bool]:
    """Set up papers/<slug>/. Returns (clone_ok, pdf_ok)."""
    github_url = GITHUB_URLS.get(slug)
    if not github_url:
        print(f"    UNKNOWN GitHub URL — add '{slug}' to GITHUB_URLS in this script")
        return False, False

    paper_dir = PAPERS_DIR / slug
    repo_path  = paper_dir / "repo"
    pdf_path   = paper_dir / "paper.pdf"

    if not dry_run:
        paper_dir.mkdir(parents=True, exist_ok=True)

    clone_ok = clone_repo(slug, github_url, repo_path, dry_run)
    pdf_ok   = download_pdf(slug, biorxiv_url, pdf_path, dry_run)
    return clone_ok, pdf_ok


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clone all repos and download PDFs for benchmark_42.csv"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview what would happen without cloning or downloading",
    )
    parser.add_argument(
        "--repos", nargs="+", metavar="SLUG",
        help="Only set up these specific repo slugs, e.g. --repos CyteOnto SEGMA",
    )
    args = parser.parse_args()

    all_repos = load_csv()

    # Filter to requested repos if --repos was given
    if args.repos:
        unknown = set(args.repos) - set(all_repos)
        if unknown:
            print(f"WARNING: these slugs are not in benchmark_42.csv: {unknown}")
        repos = {s: u for s, u in all_repos.items() if s in args.repos}
    else:
        repos = all_repos

    total = len(repos)
    print(f"Setting up {total} repo(s) under papers/")
    print(f"Dry run: {args.dry_run}")
    print(f"{'─' * 60}\n")

    PAPERS_DIR.mkdir(exist_ok=True)

    clone_ok_count = pdf_ok_count = 0
    failed_clones: list[str] = []
    failed_pdfs: list[str] = []

    for i, (slug, biorxiv_url) in enumerate(repos.items(), 1):
        print(f"[{i}/{total}] {slug}")
        print(f"    biorxiv: {biorxiv_url}")
        clone_ok, pdf_ok = setup_repo(slug, biorxiv_url, args.dry_run)
        if clone_ok:
            clone_ok_count += 1
        else:
            failed_clones.append(slug)
        if pdf_ok:
            pdf_ok_count += 1
        else:
            failed_pdfs.append(slug)
        print()

    # Summary
    print(f"{'─' * 60}")
    print(f"Repos cloned : {clone_ok_count}/{total}")
    print(f"PDFs saved   : {pdf_ok_count}/{total}")

    if failed_clones:
        print(f"\nFailed clones — fix the GitHub URL in GITHUB_URLS:")
        for s in failed_clones:
            print(f"  {s}")

    if failed_pdfs:
        print(f"\nFailed PDFs — download manually and save as papers/<slug>/paper.pdf:")
        for s in failed_pdfs:
            url = pdf_url(repos[s])
            print(f"  {s}: {url}")

    if not failed_clones and not failed_pdfs:
        print(f"\nAll done! Run the benchmark:")
        print(f"  uv run python -m research_agents.react_main \\")
        print(f"    --project papers/CyteOnto \\")
        print(f"    --questions-file question-answers/CyteOnto.json \\")
        print(f"    --team worker-critic-plus-plus")
        print(f"\nOr batch all repos:")
        print(f"  uv run python run_eval.py --repos 1-21 --team worker-critic-plus-plus --timeout 600")


if __name__ == "__main__":
    main()
