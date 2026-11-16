# Tool-call verifier progress — Week 3

Updated: 17 November 2026, session close, IST (UTC+05:30).

- Assignment: one tool-call verifier set for @lokeshArundathi; repository contributor handle: `LokeshJatangi`.
- Branch: `g10-week3-tool-call-verifier-LokeshJatangi`.
- Branch point: `g10-week3-post-training`, commit `adc33cf`.
- Session mode: pair programming. Explain changes, let the user run validation commands, and assess the complete terminal output they share.

## Current state and resume point

The user narrowed the active scope to the main assigned single-call verifier.
“V2” is our optional label for multi-turn, clarification/no-call decisions and a
trusted simulator; it is not an official assignment requirement or a second model.
Its implementation is deferred.

Two separate commits were requested and created:

- `1c47932`: main task, including the exact-call checker, original prompt/hidden
  fixture, reward registration, decoder fix and the validated tests.
- `d923692`: tests-first v2 checkpoint only. The corresponding verifier/loaders
  are not implemented. The full unfiltered branch suite is not green.

The user's latest main-task output is **39 passed, 115 deselected in 0.43 s**:
21 original cases, 13 hardening/envelope cases and 5 decoding integration cases.
This verifies the fixes for the earlier **7 failed, 1 passed** boundary probes.
The same test function bodies were then separated into
`rl/test_tool_call_hardening.py` and `rl-loop/test_tool_call_integration.py`;
original cases remain in `rl/test_verifier.py`. The moved files have been checked
for syntax, but tests were not independently rerun by the assistant.

Earlier user-supplied results: shared reward self-check **2 checked, 0 wrong**;
SFT scorer suite **158 passed**; reward regression **14 passed, 6 skipped**;
full-set decontamination **1 prompt, 0 flagged**; canary scan **0 hits**. Six
skipped cases remain unverified. No real-model or RL-training run has happened
for this tool-call task.

The original task now explicitly declares `eligibility: eval`, consistent with
its recorded model-assisted authorship and the repo's human-written training-data
rule. This metadata change does not change the checked prompt text.

The session-close request supersedes the earlier no-docs-commit instruction: commit
all session-owned notes and work-in-progress for the device move. Keep `README.md`
unchanged and preserve unrelated untracked files/directories. See
[NEW_DEVICE_HANDOFF.md](NEW_DEVICE_HANDOFF.md) for setup and focused PR instructions.
No PR or team-group message has been sent. Remote synchronization must be verified
separately; a local commit alone is not available on another device.

Earlier optional exploration considered exactly two models for later inference testing: a stronger
function-calling candidate and a weaker baseline. No pair has been selected or
measured. Team pilot reports use Qwen2.5-Coder-7B-Instruct for code RL, SmolLM2
for SFT/DT and earlier OLMoE harness experiments; these are not function-calling
rankings. A short message asking the team for a preferred pair was drafted in
chat, not sent. Keep this comparison separate from DM-Call judge experiments.

Main-task command with the current separated filenames:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  teams/10-post-training/rl/test_verifier.py \
  teams/10-post-training/rl/test_tool_call_hardening.py \
  teams/10-post-training/rl-loop/test_tool_call_integration.py \
  -k 'tool_call or hf_ or g10_codec' -q --tb=short -p no:cacheprovider
```

## Task and acceptance criteria

Given a model completion, inspect its `<|tool_call|>...<|/tool_call|>` block and
compare the emitted function name and arguments against the hidden expected call.

- A correct completion must return reward `1.0`.
- A wrong or malformed completion must return reward `0.0`.
- Compare compact, key-sorted JSON deterministically.
- Keep the expected payload only in `hidden_tests.json` and verifier test code;
  never copy it into prompts, public documentation or reward feedback.
- Score through `reward("tool_call/order_status", completion)`.
- Validate the existing SFT tool-call scorer suite without using its held-out rows
  as RL training examples.

## Work completed

| File | Purpose |
|---|---|
| [order_status/prompt.md](order_status/prompt.md) | Original natural-language request, tool schema and completion-format instructions; no expected payload. |
| [order_status/task.json](order_status/task.json) | Task identity, difficulty, provenance and contributor metadata. |
| `order_status/hidden_tests.json` | Verifier-only ground truth; deliberately not reproduced in this document. |
| [tool_call_verifier.py](../../tool_call_verifier.py) | Parses the completion as JSON data and assigns an exact binary reward. |
| [reward.py](../../reward.py) | Registers `tool_call`, discovers the task and supplies self-check fixtures for `--check-all`. |
| [test_verifier.py](../../test_verifier.py) | Adds 21 cases through the shared reward entry point. |
| [test_tool_call_hardening.py](../../test_tool_call_hardening.py) | 13 actionable-call and envelope controls. |
| [test_tool_call_integration.py](../../../rl-loop/test_tool_call_integration.py) | 5 HF/G10 decoder and mixed-environment controls. |

Per the user's request, `rl/README.md` is unchanged. The documentation is kept
in this progress file and the standalone DM-Call handoff.

The SFT dataset and scorer implementation were inspected and tested; they were
not modified.

## Design decisions

- **No execution:** the verifier parses JSON and compares values. It never runs
  candidate code or calls a tool, so this checker needs no Docker, GPU or model.
- **Exact comparison:** JSON whitespace and object key order may vary. Argument
  values, types, case and Unicode spelling must otherwise match. There is no
  loose matching or coercion; a JSON boolean differs from a number.
- **Payload contract:** require exactly one pair of tool-call markers. Reject
  malformed JSON, duplicate keys, non-JSON numbers, missing or additional
  arguments, and unexpected top-level fields. An optional string `id` is ignored
  as transport metadata, consistent with the existing chat format.
- **Completion boundaries (updated after red probes):** require the call at the
  top level, with optional preceding plain reasoning and optional trailing
  assistant stop markers. Quoted examples, code fences and forged turns are
  rejected. Completions exceeding 65,536 characters, invalid Unicode and control
  characters are refused. The user verified these changes in the 39-test run.
- **Error handling:** unknown task IDs raise `KeyError`. Invalid or missing hidden
  configuration raises an error rather than becoming a model reward of zero.
  Successful scoring returns only a generic reason and task/reward metadata.
- **Task layout:** `rl/tasks/tool_call/<task_id>/` keeps the deliverable under
  `rl/tasks/` while avoiding the existing Python code-task discovery pattern,
  `rl/tasks/*/task.json`.
- **SFT compatibility:** the existing SFT scorer supports per-row normalization
  and multiple accepted values. Its rules remain separate from this strict RL
  comparison, and its evaluation examples stay held out.

## Tests-first sequence and observed evidence

The following results come from terminal output supplied by the user. They were
not independently rerun by the assistant.

1. Wrote the 21 tool-call tests before implementing the checker.
2. User ran them: **21 failed, 50 deselected in 2.64 s**. All failed with
   `KeyError: unknown env type in 'tool_call/order_status'`, establishing the
   expected red state through the real reward entry point.
3. Added the checker, hidden fixture, task prompt and registry integration.
4. User reran the checks and supplied the green results below.

| Check | Observed result |
|---|---|
| Focused tool-call verifier tests | **21 passed, 50 deselected in 0.31 s** |
| Shared reward `--check-all --type tool_call` | Good completion scored **1.0**; bad completion scored **0.0**; **2 checked, 0 wrong** |
| Existing SFT `test_scorers.py` | **158 passed in 0.36 s** |

The focused cases cover correct and wrong arguments, JSON spacing and key order,
optional call IDs, missing markers, missing calls, malformed JSON, invalid payload
shapes, wrong tools, missing/additional arguments, wrong argument types,
string-encoded arguments, multiple calls, duplicate keys and `NaN`.

Commands used for the green checks, from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  teams/10-post-training/rl/test_verifier.py \
  -k tool_call -q -p no:cacheprovider

PYTHONDONTWRITEBYTECODE=1 python3 \
  teams/10-post-training/rl/reward.py \
  --check-all --type tool_call

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  teams/10-post-training/sft/tests/test_scorers.py \
  -q -p no:cacheprovider
```

## Related PR review

The Team 10 integration fork is `saitej123/era-v5-lab`. Its open, closed and merged
PR listing was inspected; the relevant PR descriptions and comments below were
read. All five are merged.

| PR | Finding used in this implementation |
|---|---|
| [#30 — original verifier](https://github.com/saitej123/era-v5-lab/pull/30) | Expected answers stay with the verifier; correct and wrong completions are checked. |
| [#33 — shared reward interface](https://github.com/saitej123/era-v5-lab/pull/33) | Register a checker behind `reward(env_id, output)`; unknown IDs must raise. |
| [#90 — SFT evaluation](https://github.com/saitej123/era-v5-lab/pull/90) | Existing CPU-only scorers and 32 held-out tool-call rows; evaluation only. |
| [#94 — chat-template parity](https://github.com/saitej123/era-v5-lab/pull/94) | Compact, sorted call JSON and optional transport IDs are established conventions. |
| [#104 — Go registration follow-up](https://github.com/saitej123/era-v5-lab/pull/104) | Include task listing and known-good/known-bad self-checks when registering an environment type. |

## Reward regression and decontamination evidence

The user ran these commands from the repository root and supplied the results:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  teams/10-post-training/rl/test_reward.py \
  -q -p no:cacheprovider

PYTHONDONTWRITEBYTECODE=1 python3 \
  teams/09-evaluation/decontam/decontam_check.py \
  teams/10-post-training/rl/tasks/tool_call/order_status/prompt.md --all

PYTHONDONTWRITEBYTECODE=1 python3 \
  teams/09-evaluation/decontam/canary_scan.py \
  teams/10-post-training/rl/tasks/tool_call/order_status/prompt.md
```

| Check | Observed result |
|---|---|
| Existing reward regression suite | **14 passed, 6 skipped in 0.68 s**; no failures |
| Decontamination, fingerprints v2, full set | **1 document, 0 flagged (0.00%)**; `n_items: 0`, no hits |
| Canary scan | **1 document, 0 with a canary, 0 hits**; 4 canaries from `era-v5-lab`, `gpqa_diamond`, `hle`, `terminal_bench_2` |

Fingerprint `set_sha256`:

```text
2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a
```

The skipped cases belong to the existing reward suite; the supplied summary did
not print individual skip reasons. They must not be reported as passed. All 21
new tool-call tests ran and passed. Decontamination evidence covers this one
task prompt, not the team's complete SFT or RL datasets.

## Model and dataset scope

Fixed completions establish verifier correctness. A real-model smoke test would
separately check whether a model can emit the required call and whether its
generation can be passed to this checker. No such run or model download has
happened, and no model-performance or training-improvement claim is made.

An initial model smoke test needs one model and the existing task prompt; no
external dataset or multi-model comparison is required. Give the model only
`prompt.md`, then pass its generated completion to the shared reward entry point.
Do not expose `hidden_tests.json`, test constants or `known_outputs()` to it.

The user mentioned a Mac with 16 GB RAM as a possible later environment; no model
or backend has been selected. Broader SFT/RL training requires separate data,
held-out checks and the work order's TSAI job-request process.

## Next actions

1. Stay focused on the main assignment. Do not implement optional v2 features
   unless the user explicitly resumes that scope. Its tests are committed as a
   separate checkpoint and remain unfinished.
2. Use `TOOL_CALL_TEST_PLAN.md` to review additional error coverage. Do not
   advertise proposed/unimplemented checks as tested.
3. Resume with the main-task commands in NEW_DEVICE_HANDOFF.md. No model,
   external dataset or two-model comparison is required for this assignment.
   Model inference is optional and outside the current scope.
4. Any later RL smoke run needs the corresponding environment integration,
   admitted data and the TSAI job-request process. A written v2 test suite alone
   does not supply that implementation.
5. Preserve the full checkpoint branch, but submit only the main-task change
   for the focused assignment PR. README stays unchanged. Verify remote sync
   before relying on the checkpoint from another device.

## Session-close checkpoint and unfinished artifacts

The latest user clarification is to finish the original single-call assignment
first. Its minimum acceptance evidence is one correct fixed completion scoring
1.0 and one incorrect/malformed fixed completion scoring 0.0; both passed in the
shared output. No live model is required to construct these completions.

The user requested all session work and documentation be committed for a device
move. This does not authorize including unrelated local research, images,
.gitignore or other pre-existing notes. No subagents were used.

Additional saved WIP: `rl/tests/tool_use_v2_data.py` and
`rl/tests/tool_use_v2_data_pins.json`. These are optional public evaluation-data
preparation plumbing, not part of the assigned verifier. The helper has not been
executed or tested. Public BFCL/When2Call sources were downloaded earlier only to
`/tmp/g10-tool-use-v2-public`; that temporary cache is not part of Git and need
not move to the new device. No model was downloaded, evaluated or trained.
Do not run the helper or implement v2 by default.

Unresolved helper review includes schema normalization/answer suitability and
output overwrite/symlink handling. No complete v2 suite or model-effectiveness
claim is supported. The end-of-session work is documentation and checkpointing;
no tests were independently rerun by the assistant.
