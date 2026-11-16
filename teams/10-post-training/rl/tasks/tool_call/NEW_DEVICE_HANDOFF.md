# Tool-call verifier — new-device handoff

Session close: 17 November 2026, IST (UTC+05:30).
Mode: pair programming; explain changes, give exact commands, and inspect the
complete terminal output supplied by the user. Do not launch model experiments.

## Active objective and readiness

Finish the assigned single-call verifier first. It parses a model completion's
`<|tool_call|>...<|/tool_call|>` JSON and compares the function name and arguments
using compact, sorted JSON against verifier-only ground truth.

The two required tests already exist and passed in the user's supplied output:

- `test_tool_call_correct_completion_scores_one`: reward 1.0.
- `test_tool_call_wrong_argument_scores_zero`: reward 0.0.

A fixed example string is a completion for this purpose. No actual model,
training dataset, GPU, model download or inference comparison is required.
The checker does not execute tools. Never give hidden answers or verifier test
constants to a model, or copy the expected payload into public documentation.

Core implementation: `1c47932` (parent `adc33cf`). It is a suitable focused PR
candidate after rerunning the commands below with the final filenames and
checking the intended target branch with the team lead. This is not a claim that
a PR has been opened or that all branch tests pass.

## Checkpoint versus assignment PR

The checkpoint branch is `g10-week3-tool-call-verifier-LokeshJatangi` in
`https://github.com/LokeshJatangi/era-v5-lab`.

- `1c47932`: main task, hidden fixture, reward registration, strict parser,
  decoding fix and main tests.
- `d923692`: optional v2 tests-first contracts; implementation is absent and the
  contracts are intentionally red. Do not include these in the core PR.
- Session-close checkpoint: saves these notes and untested v2 data-preparation
  helper/metadata. Not evidence that v2 works.

Keep the checkpoint for continuity. To prepare the focused PR without deleting
any saved work, create a separate branch at the core commit:

```bash
git switch -c g10-week3-tool-call-verifier-core-LokeshJatangi 1c47932
```

This branch excludes the later documentation and unfinished v2 checkpoint. Read
this handoff on the checkpoint branch first, or keep it open separately. Confirm
the lead's target repository/branch and review its diff before opening a PR. If
the base changed, port the core commit onto the agreed base rather than merging
all optional work. Do not reset the checkpoint branch.

## Setup on the new device

The current device must push the checkpoint branch successfully first; local
commits alone do not transfer. If session-close sync did not succeed, run here:

```bash
git push -u origin g10-week3-tool-call-verifier-LokeshJatangi
```

On the new device, with Git and Python 3.10+ available:

```bash
git clone --branch g10-week3-tool-call-verifier-LokeshJatangi https://github.com/LokeshJatangi/era-v5-lab.git
cd era-v5-lab
git log -4 --oneline
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pytest
```

No torch, transformers, model weights or external benchmark download is needed
for these focused checks. The HF/G10 integration tests use tokenizer fixtures.
Create the core branch as above, then run:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  teams/10-post-training/rl/test_verifier.py \
  teams/10-post-training/rl/test_tool_call_hardening.py \
  teams/10-post-training/rl-loop/test_tool_call_integration.py \
  -k 'tool_call or hf_ or g10_codec' -q --tb=short -p no:cacheprovider

PYTHONDONTWRITEBYTECODE=1 python \
  teams/10-post-training/rl/reward.py --check-all --type tool_call

PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  teams/10-post-training/sft/tests/test_scorers.py \
  -q -p no:cacheprovider

PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  teams/10-post-training/rl/test_reward.py \
  -q -rs -p no:cacheprovider
```

Share the complete output. The focused command should exercise all 39 main
cases; the broader selection includes decoder cases whose function names do not
contain `tool_call`. Six reward-regression cases were previously skipped;
inspect `-rs` reasons and do not count them as passed. Docker is not needed for
the assigned tool-call checker; other reward environments can have dependencies.
Do not use an unfiltered whole-branch run as a release gate while v2 is absent.

## Evidence already supplied by the user

- Main suite before test-file separation: 39 passed, 115 deselected, 0.43 s.
  Same function bodies were moved into the current main files; the final file
  layout has not been rerun in this session.
- Shared reward self-check: correct 1.0, incorrect 0.0; 2 checked, 0 wrong.
- SFT scorer suite: 158 passed.
- Existing reward regression: 14 passed, 6 skipped; skip reasons unavailable.
- Original task prompt: 1 document, 0 decontamination flags, 0 canary hits.
  Fingerprint full-set SHA and scan commands are recorded in PROGRESS.md.

No model inference, RL run or effectiveness claim is supported by these results.
The task metadata marks the model-assisted fixture evaluation-only under the
repository's data rule; admission as RL training data is a separate decision.

## Deferred work and preservation

V2 means optional multi-turn, clarification/no-call decisions and a trusted
simulator. It is not an assignment requirement and is not implemented.
`rl/tests/tool_use_v2_data.py` is an unexecuted, untested preparation helper;
its pinned public-source metadata is in `tool_use_v2_data_pins.json`. Review
answer/schema suitability and overwrite/symlink behavior before any future use.
Earlier public benchmark downloads live only in `/tmp/g10-tool-use-v2-public`
and are not transferred or needed for this task. No dataset rows are committed.

DM_CALL_HANDOFF.md is a separate proposed experiment, with no measured result.
TOOL_CALL_TEST_PLAN.md distinguishes tested behavior from proposed coverage.
Do not resume these extensions without an explicit scope change. README is
unchanged. No PR or team-group message has been sent. No subagents were used.
Unrelated local research notes, images, .gitignore and docs/session-notes existed
outside this work and are intentionally not included in the checkpoint.
