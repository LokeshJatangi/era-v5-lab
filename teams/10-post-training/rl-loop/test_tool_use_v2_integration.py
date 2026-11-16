"""Deferred v2 prompt-admission and split contracts; implementation is pending.

These tests are separate from the validated single-call assignment checkpoint.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent

parametrize = pytest.mark.parametrize


def tasks_module():
    spec = importlib.util.spec_from_file_location("g10_tool_use_tasks_under_test", HERE / "tasks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_public_task(tmp_path, *, eligibility="eval", source="original: Codex-authored evaluation fixture"):
    task = tmp_path / "fixture"
    task.mkdir()
    meta = {"id": "fixture", "version": 2, "eligibility": eligibility, "source": source,
            "language": "en", "family": "fixture-family", "tools": [], "licence": "original"}
    (task / "task.json").write_text(json.dumps(meta))
    (task / "prompt.md").write_text("Please check the current status.")
    # The loader must not read or export this file, even when it is invalid JSON.
    (task / "hidden_tests.json").write_text("PRIVATE_SENTINEL_DO_NOT_EXPORT")
    return task


def test_public_prompt_loader_never_reads_or_exports_hidden_answers(tmp_path):
    tasks = tasks_module()
    task = write_public_task(tmp_path)
    rows = tasks.tool_use_task_prompts([task], purpose="eval")
    assert len(rows) == 1 and rows[0][0] == "tool_use/fixture"
    assert "Please check the current status." in rows[0][1]
    assert "PRIVATE_SENTINEL_DO_NOT_EXPORT" not in rows[0][1]


@parametrize("eligibility,source", [
    ("eval", "original: human-written evaluation task"),
    ("train", "original: Codex-authored task"),
    ("train", "original: Claude-authored task"),
    ("pending", "original: human-written task pending admission"),
])
def test_training_loader_refuses_evaluation_pending_and_model_authored_tasks(tmp_path, eligibility, source):
    tasks = tasks_module()
    task = write_public_task(tmp_path, eligibility=eligibility, source=source)
    with pytest.raises(ValueError):
        tasks.tool_use_task_prompts([task], purpose="train")


def test_existing_original_tool_call_task_is_explicitly_evaluation_only():
    path = HERE.parent / "rl" / "tasks" / "tool_call" / "order_status" / "task.json"
    meta = json.loads(path.read_text())
    assert meta.get("eligibility") == "eval"


def test_split_guard_rejects_paraphrases_from_the_same_family_in_both_splits():
    tasks = tasks_module()
    train = [{"id": "a", "family": "same-request", "prompt": "Please check the status."}]
    heldout = [{"id": "b", "family": "same-request", "prompt": "What is the current status?"}]
    with pytest.raises(ValueError):
        tasks.validate_tool_use_splits(train, heldout)


def test_split_guard_accepts_disjoint_families():
    tasks = tasks_module()
    train = [{"id": "a", "family": "request-a", "prompt": "Please check the status."}]
    heldout = [{"id": "b", "family": "request-b", "prompt": "List matching files."}]
    tasks.validate_tool_use_splits(train, heldout)
