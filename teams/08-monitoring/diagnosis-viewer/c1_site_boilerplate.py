"""Site-specific C1 medicines for Vartha Bharati and News18; new Parquet copy only."""
import argparse
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from c1_navigation import MONTH, DAY, CLOCK, ZONE


FOOTER_LINES = (
    "‘ವಾರ್ತಾ ಭಾರತಿ’ ನಿಮಗೆ ಆಪ್ತವೇ ? ಇದರ ಸುದ್ದಿಗಳು ಮತ್ತು ವಿಚಾರಗಳು ಎಲ್ಲರಿಗೆ ಉಚಿತವಾಗಿ ತಲುಪುತ್ತಿರಬೇಕೇ?",
    "ಬೆಂಬಲಿಸಲು ಇಲ್ಲಿ ಕ್ಲಿಕ್ ಮಾಡಿ",
)
FOOTER = "\n".join(FOOTER_LINES)
FOOTER_PATTERN = re.compile(
    r"(?m)^" + re.escape(FOOTER_LINES[0]) + r"\r?\n"
    + re.escape(FOOTER_LINES[1]) + r"(?=[ \t\r\n]*\Z)"
)
NEWS18_HEADER = re.compile(r"[ \t]*news18-kannada[ \t]+Updated:[ \t]*")
NEWS18_TIMESTAMP = re.compile(
    rf"[ \t]*{MONTH}\.?[ \t]+{DAY},[ \t]*[0-9]{{4}},[ \t]*{CLOCK}[ \t]+{ZONE}[ \t]*",
    re.IGNORECASE,
)


def is_varthabharati_url(url):
    try:
        parsed = urlsplit(url or "")
        host = (parsed.hostname or "").lower()
        return parsed.scheme in {"http", "https"} and (
            host == "varthabharati.in" or host.endswith(".varthabharati.in")
        )
    except (TypeError, ValueError, AttributeError):
        return False


def find_varthabharati_footer(text, url=None):
    """Exact two-line appeal at document end; original code-point offsets.

    Accept LF/CRLF between the two lines and optional trailing whitespace.
    Preserve that trailing whitespace and the newline before the appeal.
    A URL mention inside article text or a look-alike hostname is insufficient.
    """
    if not is_varthabharati_url(url):
        return []
    return [{"start": m.start(), "end": m.end(),
             "detail": "Vartha Bharati donation/support footer"}
            for m in FOOTER_PATTERN.finditer(text)]


def fix_varthabharati_footer(text, url=None):
    pieces, previous = [], 0
    for match in find_varthabharati_footer(text, url):
        pieces.append(text[previous:match["start"]])
        previous = match["end"]
    pieces.append(text[previous:])
    return "".join(pieces)


def is_news18_news_url(url):
    try:
        parsed = urlsplit(url or "")
        return (parsed.scheme in {"http", "https"} and parsed.hostname == "kannada.news18.com"
                and (parsed.path == "/news" or parsed.path.startswith("/news/")))
    except (TypeError, ValueError, AttributeError):
        return False


def news18_blocks(text, url=None):
    """Complete publisher/category lines, with timestamp only after publisher.

    Original source offsets are code points. Never remove an inline India
    mention or consume a following headline that is not a supported timestamp.
    """
    if not is_news18_news_url(url):
        return []
    lines = text.splitlines(keepends=True)
    starts, offset = [], 0
    for line in lines:
        starts.append(offset)
        offset += len(line)
    blocks, i = [], 0
    while i < len(lines):
        body = lines[i].rstrip("\r\n")
        header = NEWS18_HEADER.fullmatch(body)
        if not header and body.strip(" \t") != "India":
            i += 1
            continue
        matches = [{"start": starts[i], "end": starts[i] + len(body),
                    "detail": "News18 publisher/update label" if header else "News18 standalone India category"}]
        first, last = i, i
        if header and i + 1 < len(lines):
            timestamp = lines[i + 1].rstrip("\r\n")
            if NEWS18_TIMESTAMP.fullmatch(timestamp):
                last = i + 1
                matches.append({"start": starts[last], "end": starts[last] + len(timestamp),
                                "detail": "News18 timestamp following update label"})
        blocks.append({"start": starts[first], "end": starts[last] + len(lines[last]),
                       "matches": matches})
        i = last + 1
    return blocks


def find_news18_boilerplate(text, url=None):
    return [match for block in news18_blocks(text, url) for match in block["matches"]]


def fix_news18_boilerplate(text, url=None):
    pieces, previous = [], 0
    for block in news18_blocks(text, url):
        pieces.append(text[previous:block["start"]])
        previous = block["end"]
    pieces.append(text[previous:])
    return "".join(pieces)


def site_name(url):
    if is_varthabharati_url(url):
        return "varthabharati"
    if is_news18_news_url(url):
        return "news18-kannada"
    return None


def find_site_boilerplate(text, url=None):
    return find_varthabharati_footer(text, url) + find_news18_boilerplate(text, url)


def fix_site_boilerplate(text, url=None):
    if is_varthabharati_url(url):
        return fix_varthabharati_footer(text, url)
    return fix_news18_boilerplate(text, url)


def harm_test(gold_rows):
    total = changed = 0
    for row in gold_rows:
        if not isinstance(row.get("text"), str):
            raise ValueError("Gold rows require non-null string text")
        # Missing URLs must not produce an artificial zero-harm pass.
        if not isinstance(row.get("url"), str) or not row["url"].strip():
            raise ValueError("Gold rows require URL provenance for this site-specific medicine")
        total += 1
        changed += fix_site_boilerplate(row["text"], row["url"]) != row["text"]
    if not total:
        raise ValueError("Gold set must not be empty")
    return {"gold_documents": total, "changed_documents": changed,
            "dropped_documents": 0, "changed_or_dropped_documents": changed,
            "harm_percent": 100 * changed / total,
            "passes_harm_test": changed * 100 <= total}


def clean_table(table):
    """Keep row order, IDs, schema/metadata and every non-text column intact."""
    import pyarrow as pa

    for name in ("doc_id", "url", "text"):
        if name not in table.column_names:
            raise ValueError(f"Pack requires {name} column")
    texts, records, site_documents = [], [], 0
    site_counts, changed_counts = {}, {}
    for i, row in enumerate(table.select(["doc_id", "url", "text"]).to_pylist()):
        text, url = row["text"], row["url"]
        if not isinstance(text, str):
            raise ValueError(f"Row {i + 1}: text must be a non-null string")
        site = site_name(url)
        if site:
            site_documents += 1
            site_counts[site] = site_counts.get(site, 0) + 1
        matches = find_site_boilerplate(text, url)
        fixed = fix_site_boilerplate(text, url)
        texts.append(fixed)
        if matches:
            changed_counts[site] = changed_counts.get(site, 0) + 1
            records.append({"index": i, "row": i + 1, "doc_id": row["doc_id"],
                            "disease": "C1", "site": site, "original_characters": len(text),
                            "cleaned_characters": len(fixed),
                            "removed_characters": len(text) - len(fixed), "matches": matches})
    index = table.schema.get_field_index("text")
    cleaned = table.set_column(index, table.schema.field(index),
                               pa.array(texts, type=table.schema.field(index).type))
    report = {"medicine": "C1 site boilerplate (Vartha Bharati / News18)", "documents": table.num_rows,
              "site_documents": site_documents, "changed_documents": len(records),
              "dropped_documents": 0,
              "site_documents_by_site": site_counts, "changed_documents_by_site": changed_counts,
              "removed_characters": sum(r["removed_characters"] for r in records),
              "gold_harm_test": "NOT RUN", "changes": records}
    return cleaned, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pack", type=Path)
    mode.add_argument("--gold", type=Path, help="report gold harm; URLs required")
    parser.add_argument("--output", type=Path, help="new cleaned Parquet; input is preserved")
    parser.add_argument("--report", type=Path, help="new JSON manifest, offsets/counts only")
    args = parser.parse_args()
    if args.gold and (args.output or args.report):
        parser.error("--gold reports harm only; use --pack for output/report")
    if args.report and not args.output:
        parser.error("--report requires --output")
    import pyarrow.parquet as pq

    if args.gold:
        print(json.dumps(harm_test(pq.read_table(args.gold).to_pylist()), indent=2))
        return
    paths = [path for path in (args.output, args.report) if path is not None]
    if len({path.resolve() for path in paths}) != len(paths):
        parser.error("Output and report must be different paths")
    for path in paths:
        if path.resolve() == args.pack.resolve() or path.exists():
            parser.error(f"Refusing to replace an existing file: {path}")
    cleaned, report = clean_table(pq.read_table(args.pack))
    report["input"] = str(args.pack)
    report["output"] = str(args.output) if args.output else None
    if args.output:
        with args.output.open("xb") as stream:
            pq.write_table(cleaned, stream)
    if args.report:
        with args.report.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
