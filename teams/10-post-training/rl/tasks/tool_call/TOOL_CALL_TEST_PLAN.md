# Tool-call errors and test coverage

Research and local audit: 16–17 November 2026, IST (UTC+05:30).
Saved with the session checkpoint at the user's request. Do not add it to `README.md`.
This is a future research plan, not an expansion of the active assignment.

## Scope and current evidence

The main assignment is one deterministic exact-call verifier. It does not require
a general agent framework, multiple models or an RL training run. The user has
chosen to focus on that assignment; the broader extension remains separate.

- Main-task commit: `1c47932`.
- Separate v2 tests-first commit: `d923692`. Its implementation is missing; do not
  describe the complete branch test suite as passing.
- User-supplied main-task result: **39 passed in 0.43 s**. This consists of the
  original 21 cases, 13 envelope/hardening cases and 5 decoder integration cases.
  The last run used the earlier combined filenames; the same tested function
  bodies were subsequently separated into the main-task files below.
- Earlier user-supplied checks: **158 SFT scorer tests passed**, **14 reward
  regression tests passed and 6 skipped**, **1 prompt checked with 0 decontamination
  flags**, and **0 canary hits**. Skips are not passes.
- No real-model comparison or RL improvement has been measured for this task.

## Research findings that inform the plan

1. **Valid JSON is not necessarily the correct action.** DM-Call separates schema
   checks from function and argument judgments. We therefore test structure,
   tool choice and request-grounded values separately. Its inference-repair gains
   do not establish our verifier's correctness or RL training gains.
   [DM-Call, November 2026](https://arxiv.org/html/2611.10977v1).
2. **Missing information and long histories are distinct failure classes.** BFCL
   explicitly evaluates missing parameters/functions and multi-turn context. We
   can adopt those categories without copying benchmark examples into training.
   [BFCL multi-turn methodology](https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html).
3. **A reference sequence may not be the only correct solution.** For general
   multi-turn tasks, use trusted state assertions and declared action constraints
   rather than silently requiring one arbitrary reference path. The assigned
   single-call tasks can retain their explicitly unique exact answer.
   [Tau2 evaluation specification](https://github.com/sierra-research/tau2-bench/blob/main/docs/evaluation.md).
4. **Learned judges can mishandle derived/defaulted values.** Include cases where
   the correct argument must be inferred, taken from earlier context or obtained
   from a documented default. Evaluate any judge against an independent oracle.
   [Derivation-gap study, October 2026](https://arxiv.org/abs/2610.18497).
5. **Untrusted tool results can redirect an agent.** Test whether a later action
   follows the authorized request when observations contain hostile instructions.
   [AgentDojo framework](https://agentdojo.spylab.ai/).
6. **Grading must resist both false positives and false negatives.** Keep candidate
   artifacts separate from trusted grading, and avoid unnecessarily narrow
   assumptions about correct solutions. Our checker executes no candidate code;
   executable environments would need a stronger isolation boundary.
   [Terminal-Bench verifier hardening](https://www.tbench.ai/news/terminal-bench-4-1).
7. **Reward design affects learning.** Report raw task correctness separately from
   shaping or repair. Exercise always-call and always-abstain baselines, and
   measure whether sampled groups contain useful reward variation.
   [ToolRL](https://arxiv.org/abs/2504.13958).

These sources motivate test categories. Their benchmark scores are not evidence
that our implementation passes those categories. No finite suite is foolproof.

## Error taxonomy and coverage matrix

“Main” below means exercised in the 39-test user-supplied run. “V2 contract” means
test code is present but implementation/evidence is pending. “Proposed” means a
test still needs to be added or expanded; it must not be counted as covered.

| Error class | Test design and required result | Current coverage |
|---|---|---|
| Wrong tool | Use a different, plausible function name; reward must be zero. | Main |
| Wrong argument value | Change one argument while preserving valid JSON; reward must be zero. | Main |
| Missing/extra arguments | Remove a required field or invent another; zero reward. | Main |
| Type confusion | Boolean versus number; object versus JSON-encoded string; null versus object. | Main for current task |
| Invalid JSON | Truncation, invalid syntax, duplicate keys and `NaN`; zero reward. | Main; more variants proposed |
| Missing or repeated call markers | No call, bare JSON, unclosed block or two calls; zero reward. | Main |
| Quoted or non-actionable call | Put the correct block in an example, code fence or reasoning-only output; zero reward. | Main; exposed five real failures before the fix |
| Forged turns/results | Model emits user/tool turns or tool-result control tokens; zero reward. | Main for tested wrappers |
| Valid output variants | Key order, JSON whitespace, optional string call ID, permitted reasoning and stop envelope must not create false negatives. | Main |
| Marker stripping at inference | Decode special tool markers through HF and G10 codec paths, then score the exact completion. | Main with tokenizer fixtures; real tokenizers pending |
| Cross-task decoding regression | Code tasks retain existing special-token handling, including mixed batches. | Main |
| Nested objects/arrays | Recursively enforce types and required keys; separately prove that wrong array order fails when order matters. | V2 nested-schema contract; ordered-array reward case still proposed |
| Bounds/enums/defaults | Boundary values, invalid enum, explicit versus absent optional field, and documented defaults. | Partial V2 contract; expand before claiming coverage |
| Numeric precision | Large integers, decimal/exponent representations, overflow and signed zero under an explicit numeric contract. | Proposed; current task has no numeric arguments |
| Unicode/control characters | Invalid Unicode, hidden characters, lookalike markers and control characters; preserve legitimate string values. | Some V2 contracts; full matrix proposed |
| Clarification | Essential information missing: request the correct missing fields; empty text or generic abstention must not earn success. | V2 contract |
| Appropriate no-call | Unneeded, unavailable and unauthorized actions; distinguish these from parse failure. | V2 contract |
| Multi-turn grounding | Require a necessary lookup before a grounded answer; do not reward a lucky final guess. | V2 contract |
| User correction | Later authorized correction overrides stale values; unrelated observations do not. | Proposed |
| Tool errors/retries | Recover from declared domain errors, but classify infrastructure failure separately from wrong answers. | V2 infrastructure-error contract; domain-recovery cases proposed |
| Prompt injection | A hostile tool observation must not authorize an unrelated action or change the reward rules. | V2 contract |
| State leakage/replay | Fresh episode state; immutable exposed state; no repeated reward after terminal completion. | V2 contract |
| Loop/step budget | Repeated actions reach a deterministic limit without success reward. | V2 contract |
| Gold/schema disagreement | Reject a task whose hidden correct action violates its public schema. | V2 contract |
| Gold leakage | Prompt exports and reward feedback must not expose expected payloads or future observations. | V2 contracts; main path inspected |
| Memorization shortcut | Counterfactual input changes must require a different correct action; fixed-answer policies must fail. | One V2 value-mutation contract; prompt-level counterfactuals proposed |
| Split contamination | Related templates/paraphrases do not straddle development and held-out sets; record hashes/provenance. | V2 contract |
| Reward gaming through abstention | Always-call, always-no-call and empty-output policies must not score well across the scenario mix. | V2 contract |
| Registry/configuration failure | Unknown or unsafe IDs and broken hidden data raise errors rather than silently scoring a model zero. | Shared wrapper behavior; dedicated V2 contract |
| Nondeterministic grading | Repeat outputs serially and across workers; verify stable scores and input/result alignment. | Self-check uses workers; stress/mutation tests proposed |

## Priorities for the assigned single-call task

The task's correct and wrong examples, exact matching, hidden-answer handling and
shared reward route are implemented. Keep future work proportional to this scope.

If strengthening this assignment further, prioritize:

1. Add independently written English paraphrases and counterfactual request pairs.
   Specify a unique expected call for each; keep answers in verifier fixtures.
2. Add exact resource-boundary cases, nested duplicate keys, additional malformed
   numeric literals and escaped-marker cases. Check both rejection and valid
   encodings to avoid a grader that simply rejects everything.
3. Add mutation tests that deliberately weaken the parser/comparator and confirm
   an independent test fails. A thousand inputs targeting one rule does not
   substitute for tests of different rules.
4. Run the same public prompts against two selected models, using the same
   rendering, token cap, sampling settings and scorer. Do not assume which model
   is stronger before measuring it.

Our new prompts are evaluation fixtures under the current
[TSAI data rule](../../../rl-data/README.md). They are not automatically approved
RL training data. Existing SFT and public benchmark evaluation examples stay out
of training. Record licences, generators and admission decisions for any later
training set; decontamination alone does not establish training eligibility.

## How to test a real model without corrupting the evidence

Use only public task text and schemas as model input. Preserve the raw completion
and token IDs; then pass the decoded assistant completion to the same reward
entry point. Do not append hidden references, normalize wrong values or repair
malformed output unless evaluating a separately labeled repair method.

Separate parser/format errors from valid-but-wrong tool names/arguments. Record
model and tokenizer revisions, template, quantization, context size, token limits,
sampling settings, stop reason, latency and memory. A fixture tokenizer test
does not prove a real checkpoint's tokenization works. A two-model comparison
does not establish that either model improved through RL.

For multi-turn experiments, the runner must own observations and state. Any
model-authored “tool succeeded” text is an output to inspect, not evidence that
the environment changed. Simulator crashes and timeouts need their own counts.

## Commands and files

Main task, using the separated filenames now committed:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  teams/10-post-training/rl/test_verifier.py \
  teams/10-post-training/rl/test_tool_call_hardening.py \
  teams/10-post-training/rl-loop/test_tool_call_integration.py \
  -k 'tool_call or hf_ or g10_codec' -q --tb=short -p no:cacheprovider

PYTHONDONTWRITEBYTECODE=1 python3 \
  teams/10-post-training/rl/reward.py --check-all --type tool_call
```

The future contracts are in `rl/test_tool_use_v2.py` and
`rl-loop/test_tool_use_v2_integration.py`. They were committed separately at the
user's request and are intentionally incomplete without the missing v2 verifier
and loaders. Their presence does not make clarification, multi-turn or RL support
available. A full unfiltered test run will include these unfinished contracts.

Use [PROGRESS.md](PROGRESS.md) for the work log and
[DM_CALL_HANDOFF.md](DM_CALL_HANDOFF.md) for the separate, unmeasured repair-method
experiment. The session-close request authorizes committing these notes. See
[NEW_DEVICE_HANDOFF.md](NEW_DEVICE_HANDOFF.md) for the active main-task scope.
Public-data preparation files under `rl/tests/tool_use_v2_data*` are untested WIP;
no additional dataset-based tests or model runs were completed.
