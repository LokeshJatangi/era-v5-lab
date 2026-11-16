"""Prepare a pinned, evaluation-only public prompt subset outside the repository.

This is test-data plumbing, not a verifier or the official BFCL/When2Call scorer.
Normal tests never use the network. Run this file with --download explicitly on
a new device. Source answers are written only to hidden_tests.json.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import tempfile
import urllib.request
from collections import Counter
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
PINS = HERE / "tool_use_v2_data_pins.json"
REPO = HERE.parents[3]
_TYPES = {"dict": "object", "object": "object", "str": "string", "string": "string",
          "int": "integer", "integer": "integer", "float": "number", "number": "number",
          "bool": "boolean", "boolean": "boolean", "list": "array", "array": "array", "null": "null"}


def _json(text):
    return json.loads(text) if isinstance(text, str) else copy.deepcopy(text)


def manifest():
    return json.loads(PINS.read_text(encoding="utf-8"))


def cache_path(root, relative):
    root = Path(root).resolve()
    rel = PurePosixPath(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise ValueError("unsafe cache path")
    result = root.joinpath(*rel.parts)
    if not result.resolve().is_relative_to(root):
        raise ValueError("cache path escapes root")
    return result


def verify_cache(root, pins=None):
    pins = manifest() if pins is None else pins
    for item in pins["files"]:
        path = cache_path(root, item["path"])
        data = path.read_bytes()
        if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError(f"source hash/size mismatch: {item['path']}")
        rows = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
        if len(rows) != item["rows"]:
            raise ValueError(f"source row-count mismatch: {item['path']}")
    return pins


def download_cache(root):
    pins = manifest()
    for item in pins["files"]:
        path = cache_path(root, item["path"])
        if path.is_file():
            data = path.read_bytes()
            if len(data) == item["bytes"] and hashlib.sha256(data).hexdigest() == item["sha256"]:
                continue
            raise ValueError(f"refusing to overwrite a mismatched cache file: {item['path']}")
        with urllib.request.urlopen(item["url"], timeout=30) as response:
            data = response.read(item["bytes"] + 1)
        if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError(f"download hash/size mismatch: {item['path']}")
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            stream.write(data)
            temporary = Path(stream.name)
        temporary.replace(path)
    return verify_cache(root)


def _rows(root, relative):
    return [json.loads(line) for line in cache_path(root, relative).read_text(encoding="utf-8").splitlines()
            if line.strip()]


def normalize_schema(schema):
    """Explicitly adapt the source's Python-style type labels to JSON Schema."""
    if not isinstance(schema, dict):
        raise ValueError("schema must be an object")
    result = copy.deepcopy(schema)
    if "type" in result:
        raw = result["type"]
        if isinstance(raw, list):
            if not raw or any(t not in _TYPES for t in raw):
                raise ValueError("unsupported source schema type")
            result["type"] = [_TYPES[t] for t in raw]
        elif raw in _TYPES:
            result["type"] = _TYPES[raw]
        else:
            raise ValueError("unsupported source schema type")
    for key in ("properties", "$defs", "definitions"):
        if key in result:
            result[key] = {k: normalize_schema(v) for k, v in result[key].items()}
    for key in ("items", "additionalProperties"):
        if isinstance(result.get(key), dict):
            result[key] = normalize_schema(result[key])
        elif key == "items" and key in result:
            raise ValueError("tuple-style item schemas are not adapted")
    for key in ("oneOf", "anyOf", "allOf"):
        if key in result:
            result[key] = [normalize_schema(v) for v in result[key]]
    return result


def _tools(raw):
    tools = [_json(t) for t in raw]
    for tool in tools:
        tool["parameters"] = normalize_schema(tool["parameters"])
    return tools


def unique_bfcl_call(gold):
    """Keep only a single call with one allowed value per argument; never pick among alternatives."""
    answers = gold.get("ground_truth")
    if not isinstance(answers, list) or len(answers) != 1 or not isinstance(answers[0], dict) or len(answers[0]) != 1:
        raise ValueError("not a unique single-call annotation")
    name, args = next(iter(answers[0].items()))
    if not isinstance(args, dict) or any(not isinstance(v, list) or len(v) != 1 for v in args.values()):
        raise ValueError("multiple accepted argument values")
    return {"action": "call", "name": name, "arguments": {k: copy.deepcopy(v[0]) for k, v in args.items()}}


def _record(source, row, category, tools, messages, expected):
    row_id = str(row.get("uuid", row.get("id")))
    key = source + "-" + row_id
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", key):
        raise ValueError("unsupported source row id")
    return {"id": key, "category": category, "tools": tools, "messages": messages,
            "expected": expected, "family": source + ":" + str(row.get("source_id", row_id)),
            "provenance": {"source": source, "row_id": row_id, "source_id": row.get("source_id"),
                           **manifest()["sources"][source]}}


def select_records(root, per_category=12):
    if isinstance(per_category, bool) or not isinstance(per_category, int) or per_category < 1:
        raise ValueError("per_category must be a positive integer")
    verify_cache(root)
    records, kept, rejected = [], Counter(), Counter()
    for kind in ("simple", "multiple", "irrelevance"):
        category = "bfcl_" + kind
        gold = {} if kind == "irrelevance" else {
            r["id"]: r for r in _rows(root, f"bfcl/possible_answer/BFCL_v3_{kind}.json")}
        for row in _rows(root, f"bfcl/BFCL_v3_{kind}.json"):
            try:
                expected = ({"action": "no_call", "reason": "unavailable"} if kind == "irrelevance"
                            else unique_bfcl_call(gold[row["id"]]))
                messages = row["question"]
                if len(messages) != 1 or not isinstance(messages[0], list):
                    raise ValueError("not a single-turn prompt")
                record = _record("bfcl", row, category, _tools(row["function"]), messages[0], expected)
            except (ValueError, KeyError, TypeError):
                rejected[category] += 1
                continue
            if kept[category] < per_category:
                records.append(record)
                kept[category] += 1
    for row in _rows(root, "when2call/test.jsonl"):
        category = "when2call_" + row["correct_answer"]
        try:
            if row["correct_answer"] == "tool_call":
                expected = {"action": "call", **_json(row["answers"]["tool_call"])}
            elif row["correct_answer"] == "request_for_info":
                missing = row.get("held_out_param")
                if not isinstance(missing, str) or not missing:
                    raise ValueError("missing explicit held-out parameter annotation")
                expected = {"action": "clarify", "missing": [missing]}
            elif row["correct_answer"] == "cannot_answer":
                expected = {"action": "no_call", "reason": "unavailable"}
            else:
                raise ValueError("unsupported decision label")
            record = _record("when2call", row, category, _tools(row["tools"]),
                             [{"role": "user", "content": row["question"]}], expected)
        except (ValueError, KeyError, TypeError):
            rejected[category] += 1
            continue
        if kept[category] < per_category:
            records.append(record)
            kept[category] += 1
    categories = {"bfcl_simple", "bfcl_multiple", "bfcl_irrelevance", "when2call_tool_call",
                  "when2call_request_for_info", "when2call_cannot_answer"}
    if set(kept) != categories or any(n != per_category for n in kept.values()):
        raise ValueError("not enough supported records in every requested category")
    return records, {"selected": dict(kept), "unsupported": dict(rejected), "eligibility": "eval",
                     "metric": "adapted strict subset; not an official benchmark score"}


def public_prompt(record):
    # Deliberately whitelist fields; the record also holds verifier-only answers.
    data = {"tools": record["tools"], "messages": record["messages"]}
    return ("Use the supplied tools only when appropriate. Emit one tool-call block, or a structured "
            "decision with action clarify and missing fields, or action no_call and reason unavailable.\n"
            + json.dumps(data, ensure_ascii=False, sort_keys=True))


def materialize(root, output, per_category=12):
    output = Path(output).resolve()
    if output.is_relative_to(REPO):
        raise ValueError("public benchmark fixtures must stay outside the repository")
    records, report = select_records(root, per_category)
    for record in records:
        folder = output / record["id"]
        folder.mkdir(parents=True, exist_ok=True)
        meta = {"id": record["id"], "version": 2, "language": "en", "eligibility": "eval",
                "source": "public benchmark evaluation only", "family": record["family"],
                "tools": record["tools"], "category": record["category"], "provenance": record["provenance"]}
        hidden = {"steps": [{"expected": record["expected"]}], "initial_state": {}, "final_state": {}}
        (folder / "task.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        (folder / "prompt.md").write_text(public_prompt(record) + "\n", encoding="utf-8")
        (folder / "hidden_tests.json").write_text(json.dumps(hidden, indent=2) + "\n", encoding="utf-8")
    report["row_ids"] = [r["id"] for r in records]
    output.mkdir(parents=True, exist_ok=True)
    (output / "selection.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--per-category", type=int, default=12)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    if args.download:
        download_cache(args.cache)
    print(json.dumps(materialize(args.cache, args.out, args.per_category), sort_keys=True))


if __name__ == "__main__":
    main()
