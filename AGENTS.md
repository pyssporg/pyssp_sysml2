# Repository Guidelines

- This is a test and experiment repo. Prefer readability, agility, and clear behavior over minimal diffs.
- Keep changes focused on the task, but do not avoid a small refactor when it makes the code easier to understand or test.
- Prefer `rg` for search and inspect the existing implementation before editing.
- Use `apply_patch` for manual file edits.
- Preserve user changes in a dirty worktree; never revert unrelated edits.
- When behavior changes, update or add tests close to the affected code.
- Keep docs aligned with the actual CLI, file layout, and dependency setup.
- Prefer small modules with clear responsibilities when practical.
- Factor reusable behavior into focused helpers instead of letting one file accumulate unrelated concerns.
- Avoid abstraction for its own sake, but bias toward code disposition that keeps future experiments easy to extend.
- In reviews, prioritize bugs, regressions, unclear assumptions, and missing tests.
- Favor small, explicit tests that isolate one behavior at a time.
- Prefer test-local model setup over large shared fixtures unless the fixture itself is the contract under test.
- When asserting generated artifacts, use concise summaries or normalized text where possible so failures stay readable.
- Avoid small shims or wrappers when adopting legacy code if inlining is reasonable 
