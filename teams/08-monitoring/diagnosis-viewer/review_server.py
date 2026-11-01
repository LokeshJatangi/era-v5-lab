"""Local viewer for the week 1 data diagnosis: read a pack, confirm or edit labels, export labels.csv.

Usage:
    pip install pyarrow
    python review_server.py --pack <pack_id>.parquet [--labels my_labels.csv] [--port 8765]
    then open http://127.0.0.1:8765/

The server binds to 127.0.0.1 only, so the pack never leaves your machine. Each review is saved to
<pack_id>.reviews.json next to the pack (override with --reviews). /export.csv returns the label sheet:
your reviews, then the rows of --labels that you have not reviewed yet.
"""
import argparse, csv, difflib, hashlib, io, json, os, re, threading, unicodedata
from collections import Counter
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlsplit

import pyarrow.parquet as pq
from disease_checks import candidate_report, detached_mark_candidates, exact_duplicate_groups

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
COLS = ["doc_id", "read", "verdict", "diseases", "evidence", "hex", "note"]
LOCK = threading.Lock()

# unicodedata.name() omits controls; these are their Unicode control aliases.
CONTROL_NAMES = dict(enumerate((
    "NULL|START OF HEADING|START OF TEXT|END OF TEXT|END OF TRANSMISSION|ENQUIRY|"
    "ACKNOWLEDGE|BELL|BACKSPACE|CHARACTER TABULATION|LINE FEED|LINE TABULATION|"
    "FORM FEED|CARRIAGE RETURN|SHIFT OUT|SHIFT IN|DATA LINK ESCAPE|DEVICE CONTROL ONE|"
    "DEVICE CONTROL TWO|DEVICE CONTROL THREE|DEVICE CONTROL FOUR|NEGATIVE ACKNOWLEDGE|"
    "SYNCHRONOUS IDLE|END OF TRANSMISSION BLOCK|CANCEL|END OF MEDIUM|SUBSTITUTE|"
    "ESCAPE|INFORMATION SEPARATOR FOUR|INFORMATION SEPARATOR THREE|"
    "INFORMATION SEPARATOR TWO|INFORMATION SEPARATOR ONE"
).split("|")))
CONTROL_NAMES[0x7F] = "DELETE"
# C1 aliases from Unicode NameAliases.txt. U+0080, U+0081 and U+0099
# have only historical "figment" aliases, so leave those explicitly unnamed.
CONTROL_NAMES.update({
    0x82: "BREAK PERMITTED HERE", 0x83: "NO BREAK HERE", 0x84: "INDEX",
    0x85: "NEXT LINE", 0x86: "START OF SELECTED AREA", 0x87: "END OF SELECTED AREA",
    0x88: "CHARACTER TABULATION SET", 0x89: "CHARACTER TABULATION WITH JUSTIFICATION",
    0x8A: "LINE TABULATION SET", 0x8B: "PARTIAL LINE FORWARD", 0x8C: "PARTIAL LINE BACKWARD",
    0x8D: "REVERSE LINE FEED", 0x8E: "SINGLE SHIFT TWO", 0x8F: "SINGLE SHIFT THREE",
    0x90: "DEVICE CONTROL STRING", 0x91: "PRIVATE USE ONE", 0x92: "PRIVATE USE TWO",
    0x93: "SET TRANSMIT STATE", 0x94: "CANCEL CHARACTER", 0x95: "MESSAGE WAITING",
    0x96: "START OF GUARDED AREA", 0x97: "END OF GUARDED AREA", 0x98: "START OF STRING",
    0x9A: "SINGLE CHARACTER INTRODUCER", 0x9B: "CONTROL SEQUENCE INTRODUCER",
    0x9C: "STRING TERMINATOR", 0x9D: "OPERATING SYSTEM COMMAND",
    0x9E: "PRIVACY MESSAGE", 0x9F: "APPLICATION PROGRAM COMMAND",
})
SHORT_MARKERS = {
    " ": "SPACE", "\t": "TAB", "\n": "LF", "\r": "CR", "\x85": "NEL",
    "\u00a0": "NBSP", "\u200b": "ZWSP", "\u200c": "ZWNJ", "\u200d": "ZWJ",
    "\ufeff": "BOM", "\u00ad": "SHY", "\ufffd": "U+FFFD",
    "\u202a": "LRE", "\u202b": "RLE", "\u202c": "PDF", "\u202d": "LRO",
    "\u202e": "RLO", "\u2066": "LRI", "\u2067": "RLI", "\u2068": "FSI",
    "\u2069": "PDI", "\u200e": "LRM", "\u200f": "RLM",
}
# Default_Ignorable_Code_Point ranges, including reserved tag/variation-selector
# code points. Do not mark ordinary Indic vowel signs as invisible characters.
DEFAULT_IGNORABLE = (
    (0x00AD, 0x00AD), (0x034F, 0x034F), (0x061C, 0x061C), (0x115F, 0x1160),
    (0x17B4, 0x17B5), (0x180B, 0x180F), (0x200B, 0x200F), (0x202A, 0x202E),
    (0x2060, 0x206F), (0x3164, 0x3164), (0xFE00, 0xFE0F), (0xFEFF, 0xFEFF),
    (0xFFA0, 0xFFA0), (0xFFF0, 0xFFF8), (0x1BCA0, 0x1BCA3),
    (0x1D173, 0x1D17A), (0xE0000, 0xE0FFF),
)


def character_info(ch):
    cp = ord(ch)
    code = f"U+{cp:04X}"
    category = unicodedata.category(ch)
    fallback = {"Cc": "CONTROL", "Cn": "UNASSIGNED", "Cs": "SURROGATE",
                "Co": "PRIVATE USE"}.get(category, "UNNAMED CHARACTER")
    name = unicodedata.name(ch, CONTROL_NAMES.get(cp, f"{fallback} {code}"))
    marker = SHORT_MARKERS.get(ch, "")
    if not marker and (ch.isspace() or category[0] in "CZ" or cp == 0x2800
                       or any(lo <= cp <= hi for lo, hi in DEFAULT_IGNORABLE)):
        marker = name
    return {"code_point": code, "name": name, "category": category, "marker": marker,
            "representation": repr(ch)}


def character_inventory(text):
    return [{"offset": i, **character_info(ch)} for i, ch in enumerate(text)]


def visible_text(text):
    """Single-line, explicit representation for comparison snippets."""
    return "".join(f"⟦{m}⟧" if (m := character_info(ch)["marker"]) else ch for ch in text)


def audit_summary(text, characters):
    """Whole-document hints, separate from diagnoses and unchanged source text.

    Like view_pack_2, LF/ordinary spaces stay in the complete inventory rather
    than the hidden-character summary. Also retain this viewer's broader
    default-ignorable coverage. Mixed numeric scripts do not establish G4.
    """
    hidden = [row for ch, row in zip(text, characters)
              if ch != "\n" and ((row["marker"] and not ch.isspace())
                  or row["category"] in {"Cc", "Cf", "Zl", "Zp"}
                  or ord(ch) in {0x00A0, 0xFFFD})]
    counts = Counter(row["code_point"] for row in hidden)
    first = {row["code_point"]: row for row in reversed(hidden)}
    mixed = []
    for match in re.finditer(r"[0-9೦-೯०-९]+", text):
        scripts = sorted({"ASCII" if "0" <= ch <= "9" else
                          "Kannada" if "೦" <= ch <= "೯" else "Devanagari"
                          for ch in match.group()})
        if len(scripts) > 1:
            mixed.append({"start": match.start(), "end": match.end(),
                          "scripts": scripts, "detail": "Mixed " + "/".join(scripts) + " digit token; inspect context, not proof of G4"})
    return {"hidden_characters": [{**first[cp], "count": count} for cp, count in counts.items()],
            "g1_candidates": detached_mark_candidates(text), "mixed_digits": mixed}


def load_pack(path):
    """Validate required review fields while accepting older packs' metadata."""
    names = pq.read_schema(path).names
    missing = [key for key in ("doc_id", "text") if key not in names]
    if missing:
        raise ValueError("Pack missing required columns: " + ", ".join(missing))
    docs = pq.read_table(path, columns=[key for key in
                         ("doc_id", "text", "url", "source", "lang_label") if key in names]).to_pylist()
    if not docs:
        raise ValueError("Pack contains no rows")
    for i, doc in enumerate(docs):
        if not isinstance(doc["text"], str):
            raise ValueError(f"Row {i + 1}: text must be a non-null string")
    return docs


def normalization_comparison(original, normalized):
    """Describe changed ranges using code-point offsets in both strings.

    Trim equal edges before alignment. SequenceMatcher's popularity heuristic
    stays enabled for long, repetitive documents; ranges may group nearby edits.
    """
    changes = []
    if original != normalized:
        start = 0
        while start < min(len(original), len(normalized)) and original[start] == normalized[start]:
            start += 1
        old_end, new_end = len(original), len(normalized)
        while old_end > start and new_end > start and original[old_end - 1] == normalized[new_end - 1]:
            old_end -= 1
            new_end -= 1
        matcher = difflib.SequenceMatcher(None, original[start:old_end], normalized[start:new_end])
        for tag, a, b, c, d in matcher.get_opcodes():
            if tag == "equal":
                continue
            a, b, c, d = a + start, b + start, c + start, d + start
            before, after = original[a:b], normalized[c:d]
            changes.append({
                "start": a, "end": b, "normalized_start": c, "normalized_end": d,
                "before": before, "after": after,
                "before_visible": visible_text(before), "after_visible": visible_text(after),
                "context": visible_text(original[max(0, a - 20):min(len(original), b + 20)]),
                "before_characters": character_inventory(before),
                "after_characters": character_inventory(after),
            })
    return {"changed": original != normalized, "text": normalized, "changes": changes}


def inspect_text(text, duplicate_documents=None, url=None):
    nfc = unicodedata.normalize("NFC", text)
    nfkc = unicodedata.normalize("NFKC", text)
    nfc_comparison = normalization_comparison(text, nfc)
    characters = character_inventory(text)
    return {
        "unicode_version": unicodedata.unidata_version,
        "length": len(text), "characters": characters,
        "audit": audit_summary(text, characters),
        "nfc": nfc_comparison,
        "nfkc": normalization_comparison(text, nfkc),
        "compatibility": normalization_comparison(nfc, nfkc),
        **candidate_report(text, nfc_comparison["changes"], duplicate_documents, url=url),
    }


def disease_codes(path):
    """Read the codes and names from the tables in diagnosis/DISEASES.md."""
    codes = {}
    for line in open(path, encoding="utf-8"):
        p = [x.strip() for x in line.split("|")]
        if len(p) > 3 and re.fullmatch(r"[A-H]\d", p[1]):
            codes[p[1]] = p[2]
    return codes


def pack_identity(path):
    """Stable local namespace, including when different directories share a basename."""
    return hashlib.sha256(os.fsencode(os.path.realpath(path))).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", required=True)
    ap.add_argument("--labels", help="an existing label sheet (labels.csv) to start from")
    ap.add_argument("--reviews", help="where to save reviews (default: <pack>.reviews.json)")
    ap.add_argument("--diseases", default=os.path.join(REPO, "diagnosis", "DISEASES.md"))
    ap.add_argument("--port", type=int, default=8765)
    row_group = ap.add_mutually_exclusive_group()
    row_group.add_argument("--row", type=int, help="open this 1-based row (overrides browser cursor)")
    row_group.add_argument("--start", type=int, help="open this 0-based row index (legacy)")
    ap.add_argument("--audit", action="store_true", help="open whole-document audit diagnostics")
    a = ap.parse_args()

    try:
        docs = load_pack(a.pack)
    except (ValueError, TypeError) as exc:
        ap.error(str(exc))
    initial_index = a.row - 1 if a.row is not None else a.start
    if initial_index is not None and not 0 <= initial_index < len(docs):
        ap.error(f"--row must be 1..{len(docs)}; --start must be 0..{len(docs) - 1}")
    duplicate_groups = exact_duplicate_groups(docs)
    labels = {r["doc_id"]: r for r in csv.DictReader(open(a.labels, encoding="utf-8"))} if a.labels else {}
    reviews_path = a.reviews or re.sub(r"\.parquet$", "", a.pack) + ".reviews.json"
    data = json.dumps({
        "pack": os.path.basename(a.pack),
        "pack_key": pack_identity(a.pack),
        "codes": disease_codes(a.diseases),
        "initial_index": initial_index, "audit_open": a.audit,
        "docs": [{"i": i, "doc_id": d["doc_id"], "url": d.get("url") or "", "text": d["text"],
                  "source": d.get("source"), "lang_label": d.get("lang_label"),
                  "label": labels.get(d["doc_id"])} for i, d in enumerate(docs)],
    }, ensure_ascii=False).encode()

    def load():
        try:
            return json.load(open(reviews_path, encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kw):
            super().__init__(*args, directory=HERE, **kw)

        def do_GET(self):
            request = urlsplit(self.path)
            if request.path == "/inspect":
                values = parse_qs(request.query).get("i", [])
                if len(values) != 1 or not re.fullmatch(r"[0-9]+", values[0]):
                    return self.send_error(400, "Expected one document index: /inspect?i=N")
                try:
                    index = int(values[0])
                except ValueError:
                    return self.send_error(400, "Invalid document index")
                if index >= len(docs):
                    return self.send_error(404, "Document index out of range")
                related = [{"i": j, "doc_id": docs[j]["doc_id"]}
                           for j in duplicate_groups.get(index, ()) if j != index]
                result = {"i": index, "doc_id": docs[index]["doc_id"],
                          **inspect_text(docs[index]["text"], related, url=docs[index].get("url"))}
                return self.send(json.dumps(result, ensure_ascii=True).encode(), "application/json")
            if self.path == "/":
                self.path = "/viewer.html"
            elif self.path == "/data.json":
                return self.send(data, "application/json")
            elif self.path == "/reviews":
                return self.send(json.dumps(load(), ensure_ascii=False).encode(), "application/json")
            elif self.path == "/export.csv":
                rev, buf = load(), io.StringIO()
                w = csv.writer(buf); w.writerow(COLS)
                for d in docs:
                    r = rev.get(d["doc_id"]) or labels.get(d["doc_id"])
                    if r:
                        w.writerow([str(r.get(c, "")).replace("\n", " ") for c in COLS])
                return self.send(buf.getvalue().encode(), "text/csv; charset=utf-8")
            elif self.path != "/viewer.html":
                return self.send_error(404)
            return super().do_GET()

        def do_POST(self):
            if self.path != "/save":
                return self.send_error(404)
            r = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            with LOCK:
                rev = load(); rev[r["doc_id"]] = r
                tmp = reviews_path + ".tmp"
                json.dump(rev, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                os.replace(tmp, reviews_path)
            self.send(json.dumps({"reviewed": len(rev)}).encode(), "application/json")

        def send(self, body, ctype):
            self.send_response(200)
            self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"{len(docs)} documents, {len(labels)} labels, reviews -> {reviews_path}")
    print(f"open http://127.0.0.1:{server.server_address[1]}/", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
