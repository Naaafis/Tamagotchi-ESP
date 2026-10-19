# Rules for agents

Read this, [STATUS.md](STATUS.md), and [../docs/PLAN.md](../docs/PLAN.md) before starting.

1. **Claim before you work.** Pick a `todo` task in STATUS.md whose dependencies are `done`. Set its owner to your agent name, status to `in progress`, and the branch name. Commit that change first.
2. **One task, one branch, one PR.** Branch name: `task/<ID>-<short-slug>` (e.g. `task/T1-screen-bringup`). Never commit straight to `main`.
3. **Nafis merges.** Open the PR and stop. Don't merge your own PRs. Put a short test checklist in the PR description that Nafis can run.
4. **Log as you go.** Append dated entries to [LOG.md](LOG.md): what you did, what you found, what's blocking. Newest at the bottom.
5. **Update the board when you finish.** In the same PR: status `review`, link the PR. Nafis flips it to `done` on merge.
6. **Hardware is Nafis's.** You can't press buttons or see the screen. When a step needs the physical board, write exact instructions in the PR and mark the task `blocked: needs Nafis`.
7. **Keep `firmware/pet/` hardware-agnostic.** No `board`, `busio`, `displayio` hardware calls or pygame imports there. Hardware lives in `firmware/hw/`, the simulator in `sim/`.
8. **Don't commit `references/`.** Clone upstream code with `scripts/fetch-references.sh`. If you copy code from a reference, keep its license header and note the source in [../docs/REFERENCES.md](../docs/REFERENCES.md).
9. **Prefer reuse over writing.** Check the references and Adafruit libraries before writing something from scratch.
10. **Ask instead of guessing** on anything in "Game requirements" in the plan. Put the question in LOG.md and the PR.
