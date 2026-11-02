# SFT Mixture Proposal (`sft_mix_proposal.md`)

Shared G10 SFT mixture proposal (`teams/10-post-training/sft/sft_mix_proposal.md`).  
Prepared by **Sai Teja (G10 Lead)** and **Member B** for **Gate 2 (Thu 12 Nov proposal / Sat 14 Nov TSAI decision)**.

---

## 1. Design Goal & Binding Rules

G10 post-trains an **agentic, code-first, multilingual (Indic + English) reasoning model** using `chat_format_v0` on Team 3's frozen `BrahmicTokenizer-131K` (`vocab_size = 131,072`). Every dataset entering the SFT mixture must satisfy four hard gates before conversion by `sft/convert.py`:

1. **Licence & Generator Gate (`licences/licence_table.md` — TSAI decides at Gate 2):**
   - **Lab rule on generator models:** The lab rule names **`gpt-oss`** as the allowed model generator (alongside human-written text and real GitHub commits), and it strictly excludes closed models (`GPT-3.5`, `GPT-4`, `GPT-4o`, `Claude`, `Gemini`) and `Llama` models (`Llama-2`, `Llama-3.1`, `Llama-3.3`).
   - **Other open-weight generators (Gate 2 decision):** Our candidate list also includes other open-weight generators (for example `DeepSeek-R1`, `DeepSeek-V3.2`, `Qwen3-Coder-480B-A35B-Instruct`, `Qwen3-235B`, `QwQ-32B`, `Mixtral-8x22B`, `Goedel-Prover-V2-32B`). **TSAI decides that generator list at Gate 2.** Until then, the exact generator model of each dataset is recorded in `licences/licence_table.md` so TSAI can decide set by set.
   - **StarCoder2 (`BigCode OpenRAIL-M`):** `StarCoder2` uses the **BigCode OpenRAIL-M** licence, which has use restrictions and is not one of the permissive licences in the lab rule. `StarCoder2` output (`sft-code-self-oss-instruct` / `bigcode/self-oss-instruct-sc2-exec-filter-50k`) is therefore marked **`needs TSAI decision`** in `licences/licence_table.md` and below.
2. **Decontamination Gate (`sft/decontam_report.md`):**
   - Every set is filtered through Team 9's `decontam_check.py` against `fingerprints/v2` (covering SWE-bench Verified/Live/Pro, Terminal-Bench 2, BFCL v3, HumanEval+, MBPP+, LiveCodeBench, Codeforces, AIME 2024/2025, GPQA Diamond, MMLU, MILU, FLORES-200, IN22, GSM8K) and recorded with its clean `set_sha256`.
3. **ChatML `v0` & Loss Mask Gate (`chat-format/render.py`):**
   - Every sample renders deterministically with exact Team 3 token IDs (`<|im_start|>` `129994`, `<|im_end|>` `130816`, `<|endoftext|>` `130822`, `<|think|>` `130823`, `<|/think|>` `130824`, `<|tool_call|>` `130773`, `<|/tool_call|>` `130825`, `<|tool_result|>` `130774`, `<|/tool_result|>` `130826`).
   - **Loss masks** are `1` strictly on `assistant` turns (`<|think|>...<|/think|>`, `<|tool_call|>...<|/tool_call|>`, and final assistant reply) and `0` on `system`, `user`, and `tool` (`<|tool_result|>...<|/tool_result|>`) turns so the model never learns to hallucinate user prompts or untrusted tool outputs.
4. **Script Integrity Gate (No NFKC; Keep `ZWJ` & `ZWNJ`):**
   - Pre-tokenization preserves `ZWJ` (`U+200D`) and `ZWNJ` (`U+200C`) and never applies NFKC to content, protecting Indic conjuncts (`ind-hi-hplt`, `ind-mr-fw2`, `ind-kn-fw2`, `ind-ta-sangraha-v`, `chandassu`) and mathematical symbols.

---

## 2. Proposed SFT Mixture Shares by Area

Because ERA V5 is an **agentic coding and reasoning model with first-class Indic fluency**, we propose the following 5-area SFT token/trajectory share for TSAI's Gate 2 decision:

| Area | Proposed Share (%) | Target Role in Post-Training | Primary Approved Datasets (`licences/licence_table.md`) |
| :--- | :---: | :--- | :--- |
| **1. Code** *(Generation, Commits & Competitive Reasoning)* | **35%** | Core polyglot programming, surgical diffs, unit-test synthesis, and long-CoT algorithmic problem solving | `sft-code-opencodereasoning` (`nvidia/OpenCodeReasoning`), `sft-code-opencodereasoning-2` (`nvidia/OpenCodeReasoning-2`), `sft-code-codeforces-cots` (`open-r1/codeforces-cots`), `sft-code-commitpackft` (`bigcode/commitpackft`), `sft-code-self-oss-instruct` (`bigcode/self-oss-instruct-sc2-exec-filter-50k`) |
| **2. Agentic** *(Multi-Turn SWE & Terminal Trajectories)* | **25%** | Repository navigation, multi-step bash/terminal debugging, fault localization, patch generation, and test verification | `sft-code-swe-rebench-openhands` (`nebius/SWE-rebench-openhands-trajectories`), `sft-code-nemotron-terminal` (`nvidia/Nemotron-Terminal-Corpus`), `sft-code-nemotron-cascade-swe` (`nvidia/Nemotron-Cascade-SFT-SWE`) |
| **3. Tool Use** *(Structured Function Calling & Schema Binding)* | **15%** | Deterministic JSON tool invocation inside `<\|tool_call\|>...<\|/tool_call\|>`, parallel tool `id` binding, and reasoning over `<\|tool_result\|>` | `sft-salesforce-xlam-60k` (`Salesforce/xlam-function-calling-60k`), `sft-agentic-nemotron-agentic-v1` (`nvidia/Nemotron-Agentic-v1`), `sft-agentic-nemotron-sft-agentic-v2-tool-calling` (`nvidia/Nemotron-SFT-Agentic-v2`, tool-calling part only) |
| **4. Indic** *(Native-Script Instruction, Translation & Code-Switching)* | **15%** | Native Indic instruction following across the 10 Brahmic scripts (`hi, mr, ta, te, kn, bn, gu, ml, or, pa`), preserving `ZWJ`/`ZWNJ` and avoiding translationese | `sft-indic-aya-dataset` (`CohereLabs/aya_dataset`), `sft-indic-aya-collection` (`CohereLabs/aya_collection`, 12 templated Indic subsets only) |
| **5. General** *(Math, Science & Calibrated Reasoning Effort)* | **10%** | Formal math proofs, STEM reasoning, general instruction following, and calibrating the four plain-text effort budgets (`1k, 4k, 16k, 64k`) | `sft-stem-code-openthoughts3` (`open-thoughts/OpenThoughts3-1.2M`), `sft-rl-math-openmathreasoning` (`nvidia/OpenMathReasoning`), `sft-math-openr1-math` (`open-r1/OpenR1-Math-220k`), `sft-math-nemotron-math-v2` (`nvidia/Nemotron-Math-v2`), `sft-math-nemotron-proofs` (`nvidia/Nemotron-Math-Proofs-v1`), `sft-science-nemotron-science` (`nvidia/Nemotron-Science-v1`), `sft-bespoke-stratos-17k` (`bespokelabs/Bespoke-Stratos-17k`), `sft-dolly-15k` (`databricks/databricks-dolly-15k`) |
| **Total** | **100%** | | |

---

## 3. Rationale for Each Area Share

### Area 1: Code — 35%
- **Why 35%:** The model's primary downstream benchmark suite (`SWE-bench Verified/Live/Pro`, `HumanEval+`, `MBPP+`, `LiveCodeBench`, `Codeforces`) demands strong single-file and multi-file code synthesis before RLVR (`Stage 2`) begins.
- **Composition within the 35%:**
  - **20% Long-CoT Competitive & Algorithmic Code (`OpenCodeReasoning`, `OpenCodeReasoning-2`, `codeforces-cots`):** Generated by `DeepSeek-R1` and `QwQ-32B` under `CC-BY-4.0`. Teaches structured problem decomposition inside `<|think|>...<|/think|>` before emitting code.
  - **10% Execution-Verified Instruction Code (`self-oss-instruct-sc2-exec-filter-50k` — `needs TSAI decision`):** Generated via SelfCodeAlign (`StarCoder2-15B`, dataset card tagged `ODC-By`, where every Python sample passes unit-test execution). Because `StarCoder2` has the **BigCode OpenRAIL-M** model licence (which carries use restrictions and is not one of the permissive licences in the lab rule), this set is marked **`needs TSAI decision`**. If TSAI excludes `StarCoder2` output at Gate 2, its 10% share moves to `commitpackft` and the approved competitive-code sets.
  - **5% Real Commit Diffs (`commitpackft`):** Human GitHub commit messages paired with code diffs (`MIT`), grounding the model in concise patch editing without synthetic verbosity.

### Area 2: Agentic — 25%
- **Why 25%:** Single-turn code generation does not teach an agent how to inspect a repository, run `pytest`, read a traceback from `<|tool_result|>`, and iterate when a patch fails. A dedicated 25% share of multi-turn trajectories is required so the model enters G10's 20 Docker SWE environments (`swe-envs/`) with a working action-observation loop.
- **Composition within the 25%:**
  - **15% SWE Issue Resolution (`nebius/SWE-rebench-openhands-trajectories`, `nvidia/Nemotron-Cascade-SFT-SWE`):** `SWE-rebench-openhands-trajectories` holds multi-turn OpenHands trajectories generated by `Qwen3-Coder-480B-A35B-Instruct`. `Nemotron-Cascade-SFT-SWE` holds single-turn SWE tasks (localise the bug, repair it, write a test) with responses by `DeepSeek-R1-0528`; it is not an action-observation loop. Both are `CC-BY-4.0`. The Cascade card removes repositories that appear in `SWE-bench Verified`; both sets still go through the Gate 2 decontamination check, and overlapping SWE-reBench issues are de-duplicated by instance id.
  - **10% Terminal & CLI Agent Trajectories (`nvidia/Nemotron-Terminal-Corpus`):** Generated by `DeepSeek-V3.2` (`CC-BY-4.0`), training command-line debugging, file-system manipulation, and recovery from non-zero exit codes.

### Area 3: Tool Use — 15%
- **Why 15%:** `render.py` enforces strict JSON serialization (`sort_keys=True`, optional parallel `id`, `<|tool_call|>\n{...}\n<|/tool_call|>`). Without explicit multi-tool and "when-not-to-call" training, models either emit malformed JSON or call tools unnecessarily.
- **Composition within the 15%:**
  - **8% Execution-Verified Multi-Tool Calls (`Salesforce/xlam-function-calling-60k`):** Generated by open-weight models (`DeepSeek-V2-Chat`, `Mixtral-8x22B`, `CC-BY-4.0`) and verified through Salesforce's APIGen execution checker.
  - **7% Interactive Multi-Turn Tool Agents (`nvidia/Nemotron-Agentic-v1`, `nvidia/Nemotron-SFT-Agentic-v2` tool-calling part only):** `Nemotron-Agentic-v1` is generated and judged by `Qwen3-235B-A22B`, `Qwen3-32B` and `gpt-oss-120b`; the v2 tool-calling part by `DeepSeek-V3.2` and `GLM-4.6` (`CC-BY-4.0` / `Apache-2.0` / `MIT`), covering multi-step tool chaining and user clarification turns. The search and customer-service parts of v2 are `excluded`: their generator models are not stated.

### Area 4: Indic — 15%
- **Why 15%:** `BrahmicTokenizer-131K` allocates dedicated script blocks across 9 Brahmic scripts (`Devanagari`, `Bengali`, `Tamil`, `Telugu`, `Kannada`, `Malayalam`, `Gujarati`, `Gurmukhi`, `Odia`). If SFT is 98% English/code, post-training causes catastrophic forgetting on Indic scripts and breaks `ZWJ`/`ZWNJ` conjunct generation. A 15% Indic share preserves native-script fluency on `MILU` and `IndicGenBench`.
- **Composition within the 15%:**
  - **10% Human-Written Indic Instructions (`CohereLabs/aya_dataset`):** Pure human-written prompts and responses (`Apache-2.0`) with zero translationese (`D5`) or machine-translation damage (`D4`).
  - **5% Curated Indic Task Templates (`CohereLabs/aya_collection`):** Only the 12 templated Indic subsets listed in `licence_table.md` (Hindi, Bengali, Tamil, Telugu; `Apache-2.0`), pre-processed with G10's text-prep rule (strip `U+200B`/`U+FEFF`, preserve `U+200D` ZWJ and `U+200C` ZWNJ, no NFKC). The 19 translated datasets and all other subsets are `excluded`. These subsets are task-style data and cover four of the ten scripts, so if `convert.py` finds too little usable text, the difference moves to `aya_dataset` instead of widening the `aya_collection` list.

### Area 5: General (Math, Science & Effort Calibration) — 10%
- **Why 10%:** High-precision mathematical and scientific reasoning transfers directly to algorithmic coding and prevents the model from overfitting to narrow code templates.
- **Composition within the 10%:**
  - **7% Open-Weight Math & STEM CoT (`OpenThoughts3-1.2M`, `OpenMathReasoning`, `OpenR1-Math-220k`, `Bespoke-Stratos-17k`, `Nemotron-Science-v1`, `Nemotron-Math-v2`, `Nemotron-Math-Proofs-v1`):** Generated by `DeepSeek-R1`, `QwQ-32B`, `gpt-oss-120b`, and `Goedel-Prover-V2-32B` (`Apache-2.0`, `CC-BY-4.0`, and `CC-BY-SA-4.0` with attribution).
  - **3% Concise Human General Instructions (`databricks-dolly-15k`):** Anchors direct `1k`-effort responses without unnecessary CoT inflation. `NuminaMath-1.5` is removed (`excluded`, see `licence_table.md`). Dolly has only about 15,000 rows, so if 3% would need more than a few epochs of it, the remainder moves to the 7% math and STEM line.

---

## 4. Reasoning Effort Budget Distribution (`1k, 4k, 16k, 64k`)

Every rendered SFT transcript starts with `Reasoning effort: {level}` in the first `system` turn (`render.py`). To ensure the model obeys all four effort budgets at inference time, `sft/convert.py` assigns each sample's effort label from the actual token length of its `<|think|>` + `<|tool_call|>`/`<|tool_result|>` trace and balances the mixture across all four tiers:

| Effort Level | Token Budget (Think + Tool Trace) | Target Share of SFT Mix | Typical Samples Assigned to This Tier |
| :--- | :---: | :---: | :--- |
| `1k` | $\le 1,024$ tokens | **30%** | Direct commits (`commitpackft`), single-turn function calls (`xlam-function-calling-60k`), concise Indic Q&A (`aya_dataset`, `dolly-15k`) |
| `4k` | $1,025 \text{ – } 4,096$ tokens | **35%** | Standard Python/polyglot code synthesis (`self-oss-instruct`), medium math/science problems, 2–4 turn tool interactions (`Nemotron-Agentic-v1`) |
| `16k` | $4,097 \text{ – } 16,384$ tokens | **25%** | Competitive programming CoT (`OpenCodeReasoning`, `codeforces-cots`), multi-step terminal debugging (`Nemotron-Terminal-Corpus`), hard STEM proofs (`OpenThoughts3-1.2M`) |
| `64k` | $16,385 \text{ – } 65,536$ tokens | **10%** | Long-horizon SWE repository trajectories (`SWE-rebench-openhands-trajectories`) and deep self-correcting math/code traces |

---

## 5. Revision note (2 Nov): licence review of five sets

| Set | Change | Reason |
| :--- | :--- | :--- |
| `Nemotron-Cascade-SFT-SWE`, `Nemotron-Agentic-v1`, `Nemotron-SFT-Agentic-v2` | Added to `licence_table.md` with licence, generator and decision | They were in the mix (Agentic and Tool Use, up to 22%) without an entry. Generators are open-weight models, so they pass the Week 2 rule |
| `Nemotron-SFT-Agentic-v2` search and customer-service parts | `excluded`; only the tool-calling part stays | The card names no generator for them |
| `NuminaMath-1.5` | `excluded`; removed from General | Model-written sources (`orca_math` is GPT-4 Turbo), no generator stated, same reason as `NuminaMath-CoT` |
| `aya_collection` | 12 templated Indic subsets stay; the 19 translated datasets and other subsets are `excluded` | The translated sets have untraced English sources, at least one distilled from InstructGPT |
| `sft-code-self-oss-instruct` (`StarCoder2`) | Marked `needs TSAI decision` in `licence_table.md` and Area 1 | `StarCoder2` has the BigCode OpenRAIL-M licence, which has use restrictions and is not one of the permissive licences in the lab rule |
| Non-`gpt-oss` open-weight generators (`DeepSeek-R1`, `Qwen3-Coder`, `QwQ`, `Mixtral`, etc.) | Recorded set-by-set in `licence_table.md` for Gate 2 decision | The lab rule names `gpt-oss` as the allowed model generator and excludes closed models and Llama; TSAI decides the remaining open-weight generator list at Gate 2 |

The shares are unchanged. Two quantity risks are open: Indic (`aya_collection` is narrower than assumed) and General (`dolly-15k` is small). `convert.py` row counts will show whether they hold.
