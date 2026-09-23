"""
Striver's 45-Day SDE Challenge — daily helper script.

Manages logs/daily_log.md, registers problems in main.py (or creates a C++
stub), writes a solution stub, and can commit/push the day's work.

Usage (from the repo root):
    python log.py status                         # print current counters
    python log.py add --name "Two Sum" ...       # log a problem for today
    python log.py commit [--push]                # git add + commit (+ push)

add options:
    --name "Two Sum"            problem title (required)
    --topic Arrays              topic folder (required)
    --subtopic LinearScan       subtopic folder (required)
    --language python|cpp       default python
    --method twoSum             method on the Solution class (required)
    --slug                      url slug (default: derived from --name)
    --module                    module/class name (default: derived from slug)
    --link URL                  LeetCode link (defaults to /problems/<slug>/)
    --status solved|unsolved|review   default solved
    --time 45m|1h30m            time taken (used for the day's total)
    --complexity "O(n) / O(n)"
    --approach "hash map"       semicolons split into multiple bullets
    --mistakes "..."
    --learned "..."
    --next "..."
    --summary "..."             day summary (only used when opening a new day)
    --no-register               skip main.py registration + solution stub
    --commit                    git add + commit after logging
    --push                      git push after committing
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG = ROOT / "logs" / "daily_log.md"
MAIN_PY = ROOT / "main.py"

TOTAL_DAYS = 45
TOTAL_PROBLEMS = 180

STATUS_TEXT = {"solved": "Solved", "unsolved": "Unsolved", "review": "Need Review"}

TEMPLATE = """<!--
HOW TO USE THIS LOG:
Run helpers from the repo root:

    python log.py status
    python log.py add --name "Two Sum" --topic Arrays --subtopic LinearScan \\
        --language python --method twoSum --time 45m \\
        --complexity "O(n) / O(n)" --approach "hash map for lookup" \\
        --mistakes "..." --learned "..." --next "..."
    python log.py commit [--push]

The script opens/creates today's day block, appends the problem entry, and
updates every counter (days, problems solved, per-day time spent) automatically.

Day block:
## Day NN — Weekday, DD Mon YYYY

**Topic:** ...
**Subtopic:** ...
**Problems solved:** n
**Total time spent:** 1h 05m

### Summary
One or two lines on how the day went.

Problem block (logged under its day):
### Problem: Name
- **Link:** [LeetCode](https://leetcode.com/problems/<name>/) | [Solution](../Topic/Subtopic/Module.py)
- **Status:** Solved | Unsolved | Need Review
- **Time taken:** 45m
- **Approach:**
  - Technique / heuristic used
- **Complexity:** Time O(n) / Space O(n)
- **Mistakes made:**
  - Edge cases missed, slips, wrong initial idea
- **What I learned:**
  - Pattern recognized, takeaway
- **Next steps:**
  - Revisit blindly, follow-up, alternate approach
-->
"""

DAY_RE = re.compile(r"^## Day (\d+) — .*$", re.MULTILINE)
PROBLEM_RE = re.compile(r"^### Problem:", re.MULTILINE)
PROB_COUNT_RE = re.compile(r"(\*\*Problems solved:\*\*)\s*\S+")
TIME_TAKEN_RE = re.compile(r"-\s*\*\*Time taken:\*\*\s*([^\n]+)")
TIME_TOTAL_RE = re.compile(r"(\*\*Total time spent:\*\*)\s*[^\n]*")
HEADER_DAYS_RE = re.compile(r"Total days:\s*\*\*[^\n]*\*\*")
HEADER_PROBS_RE = re.compile(r"Total problems solved:\s*\*\*[^\n]*\*\*")
TRAILING_COMMENT_RE = re.compile(r"\n?<!--\n.*?\n-->\s*$", re.DOTALL)


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "problem"


def class_name(slug: str) -> str:
    parts = [p for p in re.split(r"[-_ ]+", slug) if p]
    return "".join(p[0].upper() + p[1:] for p in parts) or "Solution"


def parse_minutes(s: str) -> int:
    s = (s or "").strip().lower()
    if not s or s in ("—", "-"):
        return 0
    hours = re.search(r"(\d+)\s*(?:h|hr|hrs|hour|hours)", s)
    mins = re.search(r"(\d+)\s*(?:m|min|mins|minute|minutes)", s)
    h = int(hours.group(1)) if hours else 0
    m = int(mins.group(1)) if mins else 0
    if hours or mins:
        return h * 60 + m
    if re.fullmatch(r"\d+(?:\.\d+)?", s):
        return int(round(float(s)))
    return 0


def fmt_minutes(m: int) -> str:
    if m <= 0:
        return "—"
    h, rem = divmod(m, 60)
    if h and rem:
        return f"{h}h {rem}m"
    if h:
        return f"{h}h"
    return f"{rem}m"


def bullets(text: str) -> list[str]:
    if not text:
        return ["  - "]
    parts = [p.strip() for p in text.split(";") if p.strip()]
    return [f"  - {p}" for p in parts] or ["  - "]


def read_log() -> str:
    text = LOG.read_text(encoding="utf-8")
    text = TRAILING_COMMENT_RE.sub("", text)
    text = re.sub(r"\n?---\s*$", "", text).rstrip() + "\n"
    return text


def top_day_number(text: str) -> int:
    nums = [int(n) for n in DAY_RE.findall(text)]
    return max(nums) if nums else 0


def day_spans(text: str) -> dict[str, tuple[int, int]]:
    heads = list(DAY_RE.finditer(text))
    spans = {}
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        spans[h.group(0)] = (h.start(), end)
    return spans


def update_day_fields(block: str) -> str:
    n = len(PROBLEM_RE.findall(block))
    block = PROB_COUNT_RE.sub(lambda m: f"{m.group(1)} {n}", block)
    mins = sum(parse_minutes(t) for t in TIME_TAKEN_RE.findall(block))
    total = fmt_minutes(mins)
    block = TIME_TOTAL_RE.sub(lambda m: f"{m.group(1)} {total}", block)
    return block


def update_header(text: str) -> str:
    n_days = len(DAY_RE.findall(text))
    n_probs = len(PROBLEM_RE.findall(text))
    text = HEADER_DAYS_RE.sub(f"Total days: **{n_days:02d} / {TOTAL_DAYS}**", text)
    text = HEADER_PROBS_RE.sub(
        f"Total problems solved: **{n_probs} / {TOTAL_PROBLEMS}**", text
    )
    return text


def problem_block(p: argparse.Namespace) -> str:
    ext = "cpp" if p.language == "cpp" else "py"
    link = p.link or f"https://leetcode.com/problems/{p.slug}/"
    sol = f"../{p.topic}/{p.subtopic}/{p.module}.{ext}"
    lines = [
        f"### Problem: {p.name}",
        f"- **Link:** [LeetCode]({link}) | [Solution]({sol})",
        f"- **Status:** {STATUS_TEXT[p.status]}",
        f"- **Time taken:** {p.time}",
        "- **Approach:**",
    ]
    lines.extend(bullets(p.approach))
    lines.append(f"- **Complexity:** {p.complexity or 'Time O(?) / Space O(?)'}")
    lines.append("- **Mistakes made:**")
    lines.extend(bullets(p.mistakes))
    lines.append("- **What I learned:**")
    lines.extend(bullets(p.learned))
    lines.append("- **Next steps:**")
    lines.extend(bullets(p.next))
    return "\n".join(lines)


def day_block(p: argparse.Namespace, datestr: str, day_no: int) -> str:
    lines = [
        f"## Day {day_no:02d} — {datestr}",
        "",
        f"**Topic:** {p.topic}",
        f"**Subtopic:** {p.subtopic}",
        "**Problems solved:** 1",
        f"**Total time spent:** {p.time}",
        "",
        "### Summary",
        p.summary or "<!-- One or two lines on how the day went. -->",
        "",
    ]
    return "\n".join(lines)


def insert_before_dict_close(text: str, header: str, entry: str) -> str:
    head = text.index(header)
    brace = text.index("{", head)
    close = text.index("}", brace)
    prefix = text[:close].rstrip("\n")
    return prefix + "\n" + entry + text[close:]


def register_main_py(p: argparse.Namespace) -> None:
    text = MAIN_PY.read_text(encoding="utf-8")
    if f'"{p.slug}"' in text:
        return
    np_entry = f'    "{p.slug}": ("{p.topic}.{p.subtopic}", "{p.module}", "{p.method}"),\n'
    tc_entry = f'    "{p.slug}": [],\n'
    text = insert_before_dict_close(text, "KNOWN_PROBLEMS = {", np_entry)
    text = insert_before_dict_close(text, "TEST_CASES:", tc_entry)
    MAIN_PY.write_text(text, encoding="utf-8")


def stub_py(p: argparse.Namespace) -> str:
    return f"""class Solution:
    def {p.method}(self, *args, **kwargs):
        ...
"""


def stub_cpp(p: argparse.Namespace) -> str:
    return f"""namespace {p.module} {{

class Solution {{
public:
    void {p.method}() {{}}
}};

}}  // namespace {p.module}
"""


def ensure_solution_file(p: argparse.Namespace) -> Path:
    ext = "cpp" if p.language == "cpp" else "py"
    path = ROOT / p.topic / p.subtopic / f"{p.module}.{ext}"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        if p.language == "cpp":
            path.write_text(stub_cpp(p), encoding="utf-8")
        else:
            path.write_text(stub_py(p), encoding="utf-8")
    return path


def cmd_add(p: argparse.Namespace) -> None:
    p.slug = p.slug or slugify(p.name)
    p.module = p.module or class_name(p.slug)
    p.time = p.time or "—"
    unsafe = bool(re.search(r"[/\\]", p.topic + p.subtopic))
    if unsafe:
        print("[!] --topic / --subtopic must be plain folder names.")
        sys.exit(1)

    path = None
    if not p.no_register:
        path = ensure_solution_file(p)
        if p.language == "cpp":
            print(
                "[i] C++ solutions are registered manually in main.cpp "
                "(add #include, a run_<slug>() function, and a PROBLEMS entry)."
            )
        else:
            register_main_py(p)

    datestr = dt.date.today().strftime("%A, %d %b %Y")
    text = read_log()
    spans = day_spans(text)
    today_heading = None
    for heading, (start, end) in spans.items():
        if heading.rstrip().endswith(datestr):
            today_heading = heading
            break

    prob = problem_block(p)
    if today_heading:
        start, end = spans[today_heading]
        block = text[start:end].rstrip() + "\n\n" + prob + "\n"
        text = text[:start] + update_day_fields(block) + text[end:]
    else:
        day_no = top_day_number(text) + 1
        day = day_block(p, datestr, day_no)
        text = text.rstrip() + "\n" + day + "\n\n" + prob + "\n"

    text = update_header(text)
    LOG.write_text(text.rstrip() + "\n\n" + TEMPLATE, encoding="utf-8")

    n_days = len(DAY_RE.findall(text))
    n_probs = len(PROBLEM_RE.findall(text))
    print(f"Logged \"{p.name}\" under the block for {datestr}.")
    print(f"Counter: {n_days:02d} / {TOTAL_DAYS} days, {n_probs} / {TOTAL_PROBLEMS} problems.")
    if path:
        print(f"Solution: {path.relative_to(ROOT)}")

    if p.commit:
        do_commit(push=p.push)


def cmd_status(_: argparse.Namespace) -> None:
    text = read_log()
    n_days = len(DAY_RE.findall(text))
    n_probs = len(PROBLEM_RE.findall(text))
    print(f"Today:      {dt.date.today().strftime('%A, %d %b %Y')}")
    print(f"Days:       {n_days:02d} / {TOTAL_DAYS}")
    print(f"Problems:   {n_probs} / {TOTAL_PROBLEMS}")
    try:
        runner_out = subprocess.run(
            [sys.executable, str(ROOT / "main.py")],
            capture_output=True, text=True, timeout=60,
        ).stdout
        summary = [ln for ln in runner_out.splitlines() if "/" in ln and "passed" in ln]
        print("\nRunner summary (last run of main.py):")
        print("\n".join(summary[-5:]) or runner_out.strip()[:300] or "(no problems registered)")
    except subprocess.TimeoutExpired:
        print("[i] main.py run timed out — skipped.")


def do_commit(push: bool) -> None:
    subprocess.run(["git", "-C", str(ROOT), "add", "-A"], check=True)
    r = subprocess.run(
        ["git", "-C", str(ROOT), "commit", "-m", f"chore: daily update {dt.date.today().isoformat()}"],
        capture_output=True, text=True,
    )
    out = (r.stdout + r.stderr).strip()
    if r.returncode == 0:
        print(out)
    else:
        print("[i] nothing to commit" if "nothing to commit" in out else out)
    if push:
        subprocess.run(["git", "-C", str(ROOT), "push"], check=True)
        print("Pushed.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Striver's 45-Day SDE Challenge — daily log helper.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="log a problem for today (creates day block if needed)")
    p_add.add_argument("--name", required=True)
    p_add.add_argument("--topic", required=True)
    p_add.add_argument("--subtopic", required=True)
    p_add.add_argument("--language", default="python", choices=["python", "cpp"])
    p_add.add_argument("--method", required=True)
    p_add.add_argument("--slug")
    p_add.add_argument("--module")
    p_add.add_argument("--link")
    p_add.add_argument("--status", default="solved", choices=["solved", "unsolved", "review"])
    p_add.add_argument("--time", default="")
    p_add.add_argument("--complexity", default="")
    p_add.add_argument("--approach", default="")
    p_add.add_argument("--mistakes", default="")
    p_add.add_argument("--learned", default="")
    p_add.add_argument("--next", default="")
    p_add.add_argument("--summary", default="")
    p_add.add_argument("--no-register", action="store_true")
    p_add.add_argument("--commit", action="store_true")
    p_add.add_argument("--push", action="store_true")

    p_status = sub.add_parser("status", help="print current counters")
    p_status.set_defaults(func=cmd_status)

    p_commit = sub.add_parser("commit", help="git add + commit (optionally push)")
    p_commit.add_argument("--push", action="store_true")
    p_commit.set_defaults(func=lambda a: do_commit(push=a.push))

    p_add.set_defaults(func=cmd_add)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()