# Benchmark report: simple

| metric | baseline | workbench | baseline vs workbench |
|---|---|---|---|
| hidden_pass_rate | 1 ± 0 (n=3) | 1 ± 0 (n=3) | within dispersion |
| mutation_score | 0.621 ± 0.097 (n=3) | 0.717 ± 0.031 (n=3) | within dispersion |
| ruff_issues | 9 ± 1 (n=3) | 10 ± 2.6 (n=3) | within dispersion |
| mypy_errors | 0 ± 0 (n=3) | 0 ± 0 (n=3) | within dispersion |
| cost_usd | 0.106 ± 0.0073 (n=3) | 0.402 ± 0.015 (n=3) | workbench higher |
| minutes | 0.802 ± 0.26 (n=3) | 2.87 ± 0.57 (n=3) | workbench higher |
| output_tokens | 5.52e+03 ± 2.5e+02 (n=3) | 2.47e+03 ± 7e+02 (n=3) | workbench lower |
| cache_read_tokens | 7.26e+04 ± 4.1e+04 (n=3) | 1.98e+05 ± 4.8e+04 (n=3) | workbench higher |
| first_call_tokens | 1.72e+04 ± 1.2 (n=3) | 2.61e+04 ± 0.58 (n=3) | workbench higher |
| interventions | 0 ± 0 (n=3) | 0 ± 0 (n=3) | within dispersion |
| skills_used | 0 ± 0 (n=3) | 0 ± 0 (n=3) | within dispersion |
| agents_used | 0 ± 0 (n=3) | 1 ± 0 (n=3) | workbench higher |
| review_correctness | n/a | n/a |  |
| review_security | n/a | n/a |  |
| review_maintainability | n/a | n/a |  |
| review_edge_coverage | n/a | n/a |  |

## Cost per quality point
No difference in hidden pass rate: the extra cost buys no measured quality on this metric.

## Workbench-only

| run | stop | skills used | agents used |
|---|---|---|---|
| simple-workbench-r1 | finished | - | agent-workbench:reviewer |
| simple-workbench-r2 | finished | - | agent-workbench:reviewer |
| simple-workbench-r3 | finished | - | agent-workbench:reviewer |
