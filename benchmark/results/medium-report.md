# Benchmark report: medium

| metric | baseline | workbench | lean | baseline vs workbench |
|---|---|---|---|---|
| hidden_pass_rate | 1 ± 0 (n=3) | 0.695 ± 0.53 (n=3) | 0.695 ± 0.53 (n=3) | within dispersion |
| mutation_score | 0.733 ± 0.044 (n=3) | 0.756 ± 0.069 (n=3) | 0.711 ± 0.042 (n=3) | within dispersion |
| ruff_issues | 7.67 ± 0.58 (n=3) | 5.67 ± 1.5 (n=3) | 9.33 ± 3.2 (n=3) | workbench lower |
| mypy_errors | 0.667 ± 0.58 (n=3) | 0.667 ± 0.58 (n=3) | 1 ± 0 (n=3) | within dispersion |
| cost_usd | 0.147 ± 0.0093 (n=3) | 0.351 ± 0.11 (n=3) | 0.471 ± 0.14 (n=3) | workbench higher |
| minutes | 1.05 ± 0.29 (n=3) | 1.92 ± 0.62 (n=3) | 2.82 ± 0.66 (n=3) | workbench higher |
| output_tokens | 8.27e+03 ± 8.7e+02 (n=3) | 8.13e+03 ± 6.2e+03 (n=3) | 4.67e+03 ± 7.1e+03 (n=3) | within dispersion |
| cache_read_tokens | 7.59e+04 ± 4.5e+04 (n=3) | 3.36e+05 ± 2.5e+05 (n=3) | 2.61e+05 ± 2.9e+05 (n=3) | workbench higher |
| first_call_tokens | 1.72e+04 ± 0 (n=3) | 2.61e+04 ± 2 (n=3) | 2.16e+04 ± 0.58 (n=3) | workbench higher |
| interventions | 0 ± 0 (n=3) | 0 ± 0 (n=3) | 0 ± 0 (n=3) | within dispersion |
| skills_used | 0 ± 0 (n=3) | 0 ± 0 (n=3) | 0 ± 0 (n=3) | within dispersion |
| agents_used | 0 ± 0 (n=3) | 0.333 ± 0.58 (n=3) | 0.667 ± 0.58 (n=3) | within dispersion |
| review_correctness | 4 ± 0 (n=3) | 4.33 ± 0.58 (n=3) | 4.33 ± 0.58 (n=3) | within dispersion |
| review_security | 3.67 ± 1.2 (n=3) | 4.67 ± 0.58 (n=3) | 4 ± 0 (n=3) | within dispersion |
| review_maintainability | 4 ± 0 (n=3) | 4 ± 0 (n=3) | 3.67 ± 0.58 (n=3) | within dispersion |
| review_edge_coverage | 3 ± 1 (n=3) | 3.33 ± 0.58 (n=3) | 3.33 ± 0.58 (n=3) | within dispersion |

## Cost per quality point
Extra cost US$ 0.20 for -30.5 points of hidden pass rate: US$ -0.01 per point (not meaningful if the verdict above is 'within dispersion').

## Workbench-only

| run | stop | skills used | agents used |
|---|---|---|---|
| medium-workbench-r1 | finished | - | - |
| medium-workbench-r2 | finished | - | agent-workbench:reviewer |
| medium-workbench-r3 | finished | - | - |
