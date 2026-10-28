# Word-acrostic length and injection-position study

Contribution by Danhua Zhao, October 25–28, 2026.

This branch adds the week's isolated generation and experiment code to the
teammate's original `main` commit
`9a60c838bb8fdfe69c65ab144d3275ca236e5729`.
The existing `stegacipher-burn/` implementation and results remain unchanged.

## Contents

- `experiments/task_stego/`: task-conditioned word-initial generation, exact-length
  and ranged paragraph modes, structural validation, bounded feedback, and tests.
- `experiments/acrostic_ablation/`: the pinned upstream source loader, message
  placement adapter, original-metric integration, and evidence storage. Its old
  sentence-acrostic plan is historical, not the final word-acrostic experiment.
- `experiments/fixed_carrier_study/`: the final fixed-carrier study, including
  fifteen preauthored domain/length carriers and the 880-cell design.
- `ops/`: study-specific two-worker scheduling, continuation and cleanup helpers.
  The shell launchers contain the original server paths and session names and
  must be adapted deliberately before use on another machine.
- `docs/results/2026-10-26-fixed-carrier-study-results.md`: final report.
- `docs/results/fixed-carrier-study-20261028/`: original-score summary CSVs and
  metadata copied without rescoring.
- `docs/superpowers/`: dated design and execution records.

## Offline verification

Run from the repository root with Python 3.10 or later:

```sh
python -m unittest discover -s experiments/task_stego/tests -p 'test_*.py'
python -m unittest discover -s experiments/acrostic_ablation/tests -p 'test_*.py'
python -m unittest discover -s experiments/fixed_carrier_study/tests -p 'test_*.py'
python -m unittest discover -s ops/tests -p 'test_fixed_study*.py'
```

These tests use fixtures and do not launch models. Some process-identity tests
require Linux `/proc` and skip on Windows. Real experiment execution additionally
requires the original TAMAS-derived data, AutoGen/OpenAI dependencies and local
Ollama models; see the individual module READMEs. Preparation is offline, while
execution requires the exact prepared plan SHA. Never reuse a started plan to
retry or replace an existing result.

## Final study and interpretation

The completed study covers the same 88 task IDs in ten conditions: Clean plus
three carrier lengths (6, 11, 17 words) at three positions (before user, after
user, system context). All 880 cells reached a terminal state: 877 completed and
three retained runtime errors. The final report keeps the errors and per-metric
sample counts. Native all-success auditing therefore remains false; a separate
coverage audit confirms complete coverage and preserved evidence.

The first seed message is a prewritten stimulus, not autonomous model generation.
Within each domain and length, tasks share a carrier. Later agent responses use
the original model. System-context placement also changes message authority.
The original scorer is preserved: TC references the first actor output; P-ASR
and ERS use text-signature proxies; tokens are output characters divided by four;
turns count transcript entries. Human review is pending. These data do not
establish task-adaptive natural steganography or successful resource exhaustion.

The full immutable raw evidence, model files, caches and machine credentials are
not part of this source-code branch. Their archive identity and preservation
checks are recorded in the final report and metadata.
