# DM-Call effectiveness experiment — handoff

Prepared: 16 November 2026, IST (UTC+05:30).

## Status and objective

**Experiment design only. No DM-Call effectiveness result has been measured.**
The objective is to determine whether DM-Call improves independently verified
tool-use success over credible, budget-controlled baselines on our held-out
English tasks. A negative or inconclusive result is a valid outcome; do not
design the experiment to guarantee a positive conclusion.

Repository branch: `g10-week3-tool-call-verifier-LokeshJatangi`, currently based
on `adc33cf`. Session mode is **pair programming**: explain each change, provide
exact experiment commands, and assess the complete output supplied by the user.
Main-task code is committed as `1c47932`; deferred v2 tests are a separate
checkpoint, `d923692`. This research plan is saved in the session-close commit. Preserve
unrelated untracked worktree files and do not modify README.

The original verifier passed its focused tests and decontamination checks, as
recorded in [PROGRESS.md](PROGRESS.md). The expanded tool-use tests are written;
the first probes exposed seven boundary/decoding failures, and the user verified
the fixes in a 39-test run. The broader v2 implementation is deferred and still
missing. The active scope is the main assignment. Finish that trusted
evaluation path before using it to measure this experiment. This document is
separate from [NEW_DEVICE_HANDOFF.md](NEW_DEVICE_HANDOFF.md), which covers only
the original assignment. No DM-Call experiment is needed to submit that task.

## Verified research and code references

- [DM-Call paper, v1, 7 November 2026](https://arxiv.org/html/2611.10977v1).
- [Authors' repository](https://github.com/gogoymh/decision-model-guided-function-calling).
- Repository commit inspected:
  `fae5c32b5817f480c5f7cebc7c0fff9f8dfb9807`; code licence: MIT. Dataset and model
  licences are separate and must be recorded when choosing those artifacts.
- [Pinned core implementation](https://github.com/gogoymh/decision-model-guided-function-calling/blob/fae5c32b5817f480c5f7cebc7c0fff9f8dfb9807/src/dmcall/core.py),
  [decision client](https://github.com/gogoymh/decision-model-guided-function-calling/blob/fae5c32b5817f480c5f7cebc7c0fff9f8dfb9807/src/dmcall/decision.py),
  and [loop tests](https://github.com/gogoymh/decision-model-guided-function-calling/blob/fae5c32b5817f480c5f7cebc7c0fff9f8dfb9807/tests/test_loop.py)
  were read during handoff preparation; no upstream tests were run.

The paper studies inference-time repair: schema validation plus separate
function/argument judgments, cumulative rejected-candidate feedback, threshold
0.5, and three repair rounds. It reports BFCL accuracy of 64.12% for Direct and
74.63% for DM-Call/Jev with its weakest generator; benefits vary by generator and
benchmark. Its benchmark evaluation is single-turn/first-call, not evidence of
multi-turn RL improvement. These are author-reported results, not ours.
[Paper](https://arxiv.org/html/2611.10977v1).

The repository does **not** include experiment runners, baseline implementations
or raw run records. Its conformance tests establish protocol behavior, not the
reported accuracy gains. Its README also states that settings were selected on
the evaluated benchmarks without a held-out split. A new independent study must
freeze settings on development data before examining the final test results.
[Authors' README](https://github.com/gogoymh/decision-model-guided-function-calling#faq).

## Questions to answer

1. Does repair improve final exact-call correctness over the shared initial
   candidate and over comparable extra inference without a decision model?
2. Do separate function and argument checks add value beyond schema validation?
3. Does cumulative history help more than retaining only the latest rejection?
4. Does the judge reject correct derived/defaulted arguments, or accept plausible
   but unsupported values? Add independent cases motivated by the
   [derivation-gap study](https://arxiv.org/abs/2610.18497).
5. Are gains retained on clarification/no-call cases and under longer histories,
   distractor tools and injected tool-result instructions?
6. At what token, request, memory and latency cost are any gains obtained?

## Independent ground truth and trust boundaries

The decision model is part of the method under test. **Its acceptance probability
must never become the correctness label or replace the deterministic RL reward.**

- Keep gold calls, future observations and final-state assertions in verifier-only
  files. Neither generator nor decision model may receive them.
- Allow repairs to use schema errors and the method's own feedback, never the
  hidden oracle's mismatched argument names, values or failure explanations.
- Score final calls with the same frozen exact checker across all methods. Record
  differences from any benchmark's normalization rules instead of mixing scores.
- For episode experiments, a trusted simulator supplies user/tool observations
  and owns state. Reject model-authored tool results, role spoofing and reward
  fields. A final-state check alone must not permit skipping required reads or
  violating explicitly declared action constraints.
- Preserve raw output and any adapter conversion. Do not silently repair malformed
  JSON or strip markers for one method while leaving them intact for another.
- Keep candidate-call quality separate from whether an execution gate accepts it.
  Do not perform real external actions in this study.

Code inspection found two behaviors that need explicit accounting: an initial
readable no-call can bypass verification, and exhausting repairs can return the
initial candidate with `accepted=False`. Test these and log their status rather
than treating every returned candidate as approved. Use `call()`, which does not
execute tools, for the offline study.
[Pinned implementation](https://github.com/gogoymh/decision-model-guided-function-calling/blob/fae5c32b5817f480c5f7cebc7c0fff9f8dfb9807/src/dmcall/core.py).

## Data and splits — proposed experiment design

Start with a small development pilot to verify the adapter and estimate paired
disagreement rates. The size of a later confirmatory test must be chosen from a
power calculation, not from a desired positive result. A small pilot cannot
establish a sub-percentage-point advantage.

Use original, unambiguous English scenarios covering:

| Scenario group | Intended stress |
|---|---|
| Close tool names and distractors | Correct function selection |
| Exact copying and strict JSON types | Strings, booleans, integers, null and omitted values |
| Defaults and derived values | Grounding beyond verbatim copying |
| Nested objects and ordered arrays | Argument structure and item order |
| Missing information | Appropriate clarification instead of guessing |
| Irrelevance and unavailable tools | Appropriate no-call decisions |
| Corrections and earlier results | Correct use of conversation history |
| Tool failures and recovery | Recovery without invented success |
| Untrusted result instructions | Maintaining the user's authorized objective |
| Resource limits and truncation | Partial outputs, long contexts and exhausted budgets |

Use a range of difficulty. If every initial answer is right or every one is wrong,
the pilot does not measure a useful repair trade-off. The RL objective also drops
equal-reward groups; task difficulty must be calibrated before a training study.

Split by underlying request/template lineage, not just row or random seed.
Paraphrases and value substitutions from the same scenario must not cross the
development/test boundary. Include counterfactual pairs where changing the user
request changes the correct action. Freeze IDs, source revisions and hashes.

Existing `sft/tests/toolcall_v1.jsonl` stays held out. It may support a separately
reported evaluation with its existing scorer, but must never be used to tune the
method or train the model. Public benchmark examples must remain evaluation data;
do not copy them into the RL pool. Decontaminate any newly proposed training data.

Generated challenge fixtures are **evaluation-only** under the current
[TSAI data rule](../../../rl-data/README.md). Training needs human-written,
properly licensed/admitted tasks; human review alone must not silently relabel
model-authored text as human-authored.

## Comparison arms

Use the same frozen generator weights, tokenizer, chat template, sampling settings
and original candidate per task/seed across paired arms. For each arm, log all
generator and verifier calls, retries, tokens and durations.

| Arm | Purpose |
|---|---|
| Direct | Shared original candidate; reference point |
| Schema-only repair | Isolate benefits of fixing structural errors |
| Self-refinement | Test whether additional generation alone explains the gain |
| DM-Call, both checks, cumulative history | Main method |
| DM-Call, latest rejection only | Isolate cumulative history |
| Function-only / arguments-only | Isolate separate judgments |
| Numeric / text / hybrid feedback | Isolate feedback representation |

Begin with Direct, schema-only, self-refinement and the main method. Add ablations
after this comparison works. Choose the final model and all settings on the
development split. Record them before opening held-out labels.

A cap of three repairs means at most four generator candidates, **not** equal
total compute: DM-Call additionally invokes a judge. Report both a fixed-repair
comparison and a separately budget-matched comparison against self-refinement or
additional sampling. Match the declared total token/cost budget as closely as
possible and report the actual usage. Never label oracle-selected best-of-N as a
deployable baseline; it is only an explicitly marked upper bound.

Any new local experiment runner and baseline code must be implemented and tested;
none currently exists in our branch. Do not invent a command that implies it does.

## Hardware choices for the 16 GB Mac

The authors' open decision model is 27B in BF16. Its weights alone require about
54 GB at two bytes per parameter, before runtime overhead. Therefore the exact
open-model setup does not fit into 16 GB. Four-bit weights alone are roughly
13.5 GB, which does not establish a workable two-model setup, and quantization
would change the experiment.

Choose and label one path before downloading anything:

1. **Method reproduction with an available original judge:** a local generator
   plus the paper's hosted judge, or a separately provisioned original open judge.
   Record service/model versions, cost and any deviation from original conditions.
   No remote service or job has been requested or authorized in this session.
2. **Local adaptation:** a smaller generator and smaller judge that fit within
   measured memory limits. This tests the method's transfer to those models; it
   does not reproduce the paper's numerical results. Report probability extraction
   and calibration. A judge's self-reported confidence is not automatically
   equivalent to a native decision-model probability.
3. **Protocol-only smoke test:** scripted generator/judge responses. Useful for
   implementation tests, but not evidence of model effectiveness.

The pinned client expects the PPLX model's native decision endpoint; substituting
an ordinary chat endpoint is a method change. Verify the serving protocol and
checkpoint provenance before comparing results.
[Pinned decision client](https://github.com/gogoymh/decision-model-guided-function-calling/blob/fae5c32b5817f480c5f7cebc7c0fff9f8dfb9807/src/dmcall/decision.py).

## Unit checks before spending model compute

Create and pass tests for shared initial candidates, repair caps, chronological
history, no gold leakage, immutable original requests, and no execution during
verification. Also test judge timeout, NaN/missing probabilities, schema-invalid
candidates, initial no-call bypass, exhaustion fallback and correct-to-incorrect
repairs. Infrastructure errors must be recorded separately from wrong answers.

To inspect and test the upstream library later, in an isolated temporary checkout
on the target device, these are preparation commands; **not run in this session**:

```bash
git clone https://github.com/gogoymh/decision-model-guided-function-calling.git /tmp/dmcall-repro
git -C /tmp/dmcall-repro checkout --detach fae5c32b5817f480c5f7cebc7c0fff9f8dfb9807
cd /tmp/dmcall-repro
uv sync --frozen --extra dev
uv run pytest -q
uv run ruff check src tests spec
```

Use a fresh checkout path if that directory already contains work. Record Python,
dependency and OS versions and complete output. Passing these tests does not run
BFCL, API-Bank or our model experiment.

## Metrics and acceptance evidence — our proposed protocol

Select one primary comparison before the held-out run: main DM-Call versus the
strongest development-selected budget-matched non-DM baseline. Treat Direct and
the ablations as additional reported comparisons; adjust for multiple testing
before making several confirmatory significance claims.

Report at least:

- Independently verified exact-call accuracy and episode success, separately.
- Per-family counts and rates; call, clarification and no-call performance.
- Wrong-call acceptance, correct-call rejection, abstention/accepted coverage,
  and repair outcomes: wrong-to-right versus right-to-wrong.
- Context truncations, timeouts, infrastructure failures, missing results and
  budget exhaustion. Report denominators and do not silently discard failures.
- Generator/judge calls and tokens; wall-clock mean and p95 latency; summed
  request duration as a separate metric; peak memory and actual priced cost.

Use a paired confidence interval on the held-out accuracy difference, resampling
at independent scenario-family level and keeping repeated seeds/counterfactuals
together. Run multiple seeds without counting correlated trials as new tasks.
Estimate needed sample size from the development pilot's disagreement rate.

Before the test, declare the smallest useful gain, acceptable wrong-call risk and
resource budget. Support an effectiveness claim only when the interval and the
declared practical/risk criteria are satisfied. Otherwise report negative,
inconclusive, or insufficient-power evidence. Never change thresholds or remove
difficult examples after seeing held-out scores.

## RL-specific follow-up

DM-Call is an inference-time wrapper, not the RL objective. Once both components
are ready, evaluate a 2-by-2 design on the same held-out tasks:

| Weights | Inference |
|---|---|
| Before RL | Direct |
| Before RL | DM-Call |
| After RL | Direct |
| After RL | DM-Call |

This distinguishes learning in the weights from improvements bought by repair.
Keep the deterministic reward independent of the learned judge throughout. Log
raw success alongside any shaped reward, and monitor equal-reward groups, dropped
groups and effective updates. Training runs still follow the TSAI job-request and
data-admission process. Do not claim that a gain from inference repair proves RL
training gains or safety in arbitrary tool environments.

## Artifacts and resume checklist

Store experimental artifacts under a new `out/dm_call/<run_id>/` directory:
configuration and hashes, per-task/seed candidates, decision scores, repair
history, independent outcomes, resource metrics and a paired analysis report.
Keep credentials out of logs. Do not commit model weights, benchmark examples or
private transcripts to the team repo. Commit only permitted code and summaries.

The next session should:

1. Read [PROGRESS.md](PROGRESS.md), verify the branch/worktree and finish the new
   verifier tests before running model experiments.
2. Choose a hardware/judge path and pin its artifacts; make no model-performance
   assumptions from the original unit-test pass counts.
3. Implement the experiment adapter, baselines and independent scorer boundary;
   test them using scripted outputs first.
4. Run a development pilot, freeze settings and comparison criteria, then run
   the untouched held-out evaluation and save complete evidence.
5. Write a results table with uncertainty, costs and limitations. Report what
   happened, including no improvement, rather than claiming universal proof.
