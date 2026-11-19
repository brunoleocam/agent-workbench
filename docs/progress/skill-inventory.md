# Skill inventory and consolidation (0.7.0)

0.6.1 shipped 44 skills and 10 agents. The skill descriptions the model sees at session start were about 12,400 characters (about 3,100 tokens), plus about 2,200 characters of agent descriptions. In one Claude Code 2.1.322 session with the plugin installed, 17 of the plugin's skills were listed with no description at all. That is consistent with the listing running past its size budget. A skill listed without a description cannot be routed to by its description.

## Done in 0.7.0

| Before | After | Why |
| --- | --- | --- |
| `feature` (8-line alias) + `feature-development` | `feature` | Literal duplicate: `feature` only said "follow `feature-development`". |
| `debug` + `lean-investigation` | `debug`, section "Reading little" | `lean-investigation` opened with "Same principles as `debug`"; it only added a reading budget and an output format. |
| 14 descriptions over 330 characters | at most 300 | Total visible description text down to about 9,100 characters (42 skills). |

## Overlaps kept on purpose (pending the benchmark)

| Group | What each one does that the others do not | Proposal after the benchmark |
| --- | --- | --- |
| `debug`, `root-cause`, `bug-fix` | `debug` finds the cause; `root-cause` writes the record after it is confirmed; `bug-fix` chains debug, a failing test, the fix, and regression. A chain, not duplicates. | If `metrics.py` shows `root-cause` is rarely used on its own, fold it into `bug-fix` as its record step. |
| `implementation`, `staged-task`, `tdd` | `implementation` runs one spec'd task (drift check, checkpoint); `staged-task` splits an unspecified request into verified steps; `tdd` is the red-green-refactor cycle both use. Different layers. | Keep `tdd`; merge `staged-task` into `implementation` if the benchmark shows the model confuses them. |
| `investigation` vs `debug` | `investigation` explores how a system works without a failure; `debug` explains a failure. | Keep both; consider renaming `investigation` to `explore-system` if routing errors appear. |
| `design-*` (5) and `architecture-*` (5) | One pipeline skill plus four stage skills each. The stage skills let a user re-enter one stage. | Measure whether stage skills are ever invoked directly; if not, keep only the pipeline skills and move the stages to references. |
| `brainstorm`, `implementation-plan`, `new-project` | Greenfield design, a detailed plan from an approved design, and a project scaffold. | Measure usage. |

The benchmark records `SKILL_USED` events (Skill tool and typed slash commands), so `metrics.py` shows which skills actually run. Measured: description size per session. Still to measure: wrong skill or agent choices per step, scored from the benchmark logs.
