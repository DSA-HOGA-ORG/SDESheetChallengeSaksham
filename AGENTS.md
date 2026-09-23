# AGENTS.md

Workflow for **Striver's 45-Day SDE Challenge** — solve 180 problems across 45 days,
pushing code + logbook to GitHub daily.

## Repository layout

```
main.py                 # Python runner — KNOWN_PROBLEMS + TEST_CASES live here
main.cpp                # C++ runner — includes, run_<slug>() fns, PROBLEMS map
log.py                  # daily helper: logbook entries, registration, git commit/push
Topic/Subtopic/*.py     # pure LeetCode Solution classes (one language per problem)
Topic/Subtopic/*.cpp    # namespaced Solution classes for C++
logs/daily_log.md       # structured daily logbook (45 days / 180 problems)
.github/workflows/daily-commit.yml   # auto-commits + pushes every day (18:30 UTC)
```

## When the user asks to add a problem

Gather: **problem name**, **topic** + **subtopic** (existing folders first), **language**
(python / cpp), **method name**, and the **LeetCode link**.

1. **Create the solution file** at `Topic/Subtopic/<ModuleName>.py` (or `.cpp`) containing
   ONLY the `Solution` class. This is the code that gets pushed.
2. **Python:** register in `main.py` — add `"<slug>": ("Topic.Subtopic", "ModuleName", "method")`
   to `KNOWN_PROBLEMS` and a real test-case list to `TEST_CASES`.
   **C++:** add the `#include`, a `run_<slug>()` function with test cases, and a
   `PROBLEMS` map entry in `main.cpp`.
3. **Run the runner** until green: `python main.py <slug>`, or
   `g++ -std=c++17 main.cpp -o main && ./main <slug>`.
4. **Log the entry** (keeps `logs/daily_log.md` counters in sync):

   ```
   python log.py add --name "Two Sum" --topic Arrays --subtopic LinearScan \
       --language python --method twoSum --time 45m \
       --complexity "O(n) / O(n)" \
       --approach "hash map; track complement" \
       --mistakes "none" --learned "lookup beats brute force" --next "revisit in 3 days"
   ```

5. **Push.** The GitHub Actions workflow auto-commits + pushes daily, so just commit:
   `python log.py commit` (add `--push` if you want to push immediately).

`python log.py status` prints current counters (days / problems).

## Rules

- **One language per problem.** Python *or* C++, never both.
- **Solution files are pure solution classes.** All test cases live only in `main.py` /
  `main.cpp`.
- **Run lint/typecheck when relevant** — then the runner for the touched language.
- Never commit secrets; keep commit messages short and consistent
  (`chore: ...` / `feat(TopicSubtopic): ...`).