"""C1/C5 website-navigation medicine. Import for inspection; CLI reports gold harm only."""
import argparse
import json
import re
import unicodedata

LINE_ENDINGS = "\r\n\v\f\x1c\x1d\x1e\x85\u2028\u2029"
ENGLISH_BULLET = re.compile(r"[ \t]*-[ \t]+[A-Za-z].*")
AGE_SUFFIX = re.compile(r"(?<!\d)\d+[ \t]+days?[ \t]+ago[ \t]*$", re.IGNORECASE)
HOME_PREFIX = re.compile(r"\s*(?P<label>ಮುಖಪುಟ)(?=$|[\s/|»›:>])")
TRAFFIC_SLOGAN = "ಜೀವ ರಕ್ಷಣೆಗಾಗಿ ಸಂಚಾರ ನಿಯಮ ಪಾಲಿಸಿ"
SOCIAL_FOLLOW = re.compile(r"[ \t]*Please[ \t]+follow[ \t]+and[ \t]+like[ \t]+us[ \t]*:?[ \t]*", re.IGNORECASE)
MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Sept(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
DAY = r"(?:0?[1-9]|[12][0-9]|3[01])"
CLOCK_24 = r"(?:[01]?[0-9]|2[0-3]):[0-5][0-9](?::[0-5][0-9])?"
CLOCK_12 = r"(?:0?[1-9]|1[0-2]):[0-5][0-9](?::[0-5][0-9])?[ \t]+(?:AM|PM)"
CLOCK = rf"(?:{CLOCK_12}|{CLOCK_24})"
ZONE = r"(?:[A-Z]{2,5}|[+-](?:[01][0-9]|2[0-3]):?[0-5][0-9])"
BYLINE_ZONE = rf"(?:{ZONE}|\[[ \t]*{ZONE}[ \t]*\])"
PUBLICATION_MARKER = r"(?:First[ \t]+Published|Last[ \t]+(?:Modified|Updated)|Published|Updated)"
BYLINE_TIMESTAMP = re.compile(
    rf"[ \t]*(?:{PUBLICATION_MARKER}(?:[ \t]*:[ \t]*|[ \t]+))?(?:[^,\r\n]{{1,120}},[ \t]*)?"
    rf"{MONTH}\.?[ \t]+{DAY},[ \t]*[0-9]{{4}},[ \t]*{CLOCK}[ \t]+{BYLINE_ZONE}[ \t]*",
    re.IGNORECASE,
)
UPDATE_TIMESTAMP = re.compile(
    rf"[ \t]*{PUBLICATION_MARKER}[ \t]*:?[ \t]+"
    rf"(?:[^,\r\n()]+,[ \t]*)?\d{{1,2}}[ \t]+[^\d\r\n()]+[ \t]+\d{{4}}[ \t]*"
    rf"\([ \t]*{CLOCK}[ \t]+{ZONE}[ \t]*\)[ \t]*",
    re.IGNORECASE,
)
KANNADA_WEEKDAY = r"(?:ಭಾನುವಾರ|ಸೋಮವಾರ|ಮಂಗಳವಾರ|ಬುಧವಾರ|ಗುರುವಾರ|ಶುಕ್ರವಾರ|ಶನಿವಾರ)"
KANNADA_TIMESTAMP = re.compile(
    rf"[ \t]*(?:{KANNADA_WEEKDAY},[ \t]*)?\d{{1,2}}[ \t]+[\u0C80-\u0CFF]+[ \t]+\d{{4}}[ \t]*"
    rf"\([ \t]*{CLOCK}[ \t]+{ZONE}[ \t]*\)[ \t]*",
    re.IGNORECASE,
)


def pipe_navigation_matches(line):
    """Recognize complete navigation-label lines ending in a pipe and real LF.

    Only whitespace may follow the last pipe before LF/CRLF. Inline related
    links, unpiped trailing text, and EOF without LF are not this C1 pattern.
    This checks syntax, not a city dictionary; Indic marks remain in labels.
    """
    if not line.endswith("\n"):
        return []
    body = line.rstrip(LINE_ENDINGS)
    if not body.rstrip().endswith("|"):
        return []
    matches, cursor = [], 0
    while True:
        pipe = body.find("|", cursor)
        if pipe < 0:
            break
        segment = body[cursor:pipe]
        label = segment.strip()
        if (not label or unicodedata.category(label[0])[0] not in "LN"
                or not any(unicodedata.category(ch).startswith("L") for ch in label)
                or any(not (unicodedata.category(ch)[0] in "LMN" or ch.isspace()
                            or ch in "-'’.,()/\u200c\u200d") for ch in label)):
            return []
        start = cursor + len(segment) - len(segment.lstrip())
        matches.append({"start": start, "end": pipe + 1, "detail": "pipe-terminated city/navigation label"})
        cursor = pipe + 1
    return matches if not body[cursor:].strip() else []


def find_c1_blocks(text):
    """Match navigation, widget labels, relative ages and publication timestamps.

    All offsets are zero-based original Unicode code-point offsets. Blank lines
    may separate entries. A nonblank, nonmatching line ends the block. Unheaded
    English-led bullets match only at the first nonblank line of the document.
    Trending, Title and lines ending in N day(s) ago also match elsewhere. A bare '-'
    joins widget entries only when another recognized widget line follows it.
    Publication timestamps match complete byline/date/time/timezone lines
    (including an English weekday and bracketed timezone), or
    marked update lines with a localized date and parenthesized time/timezone.
    Standalone Kannada dates with parenthesized time/timezone also match, with
    an optional Kannada weekday; a publication/update marker is not required.
    A leading ಮುಖಪುಟ navigation label matches only at the first nonblank line.
    Pipe-label lines require a final pipe followed only by whitespace and LF/CRLF.
    Don't Miss! may introduce a list without Just In and also matches alone.
    Headers are C1; English-led category/teaser bullets are C5.
    Inline related-link text is preserved. The traffic-safety slogan and
    'Please follow and like us:' social prompt are matched as complete lines.
    """
    lines = text.splitlines(keepends=True)
    starts, offset = [], 0
    for line in lines:
        starts.append(offset)
        offset += len(line)
    bodies = [line.rstrip(LINE_ENDINGS) for line in lines]
    first = next((j for j, body in enumerate(bodies) if body.strip()), len(lines))
    blocks, i = [], 0
    navigation_first = first
    pipe_rows, whole_pipe_rows = set(), set()
    for j, body in enumerate(bodies):
        matches = pipe_navigation_matches(lines[j])
        if matches:
            pipe_rows.add(j)
            whole_pipe_rows.add(j)
            blocks.append({"start": starts[j], "end": starts[j] + len(lines[j]), "matches": [
                {**match, "start": starts[j] + match["start"], "end": starts[j] + match["end"]}
                for match in matches
            ]})
            if j == first:
                navigation_first = next((k for k in range(j + 1, len(lines)) if bodies[k].strip()), len(lines))
    home = HOME_PREFIX.match(bodies[first]) if first < len(lines) and first not in pipe_rows else None
    if home:
        whole_line = not bodies[first][home.end("label"):].strip()
        end = starts[first] + (len(lines[first]) if whole_line else home.end("label"))
        blocks.append({"start": starts[first], "end": end, "matches": [{
            "start": starts[first] + home.start("label"), "end": starts[first] + home.end("label"),
            "detail": "homepage navigation label",
        }]})
        if whole_line:
            navigation_first = next((j for j in range(first + 1, len(lines)) if bodies[j].strip()), len(lines))
    while navigation_first in whole_pipe_rows:
        navigation_first = next((j for j in range(navigation_first + 1, len(lines)) if bodies[j].strip()), len(lines))
    while i < len(lines):
        if i in pipe_rows:
            i += 1
            continue
        second = None
        if bodies[i].strip().casefold() in {"don't miss!", "don’t miss!"}:
            second = i
            cursor = i + 1
        elif bodies[i].strip().casefold() == "just in":
            second = i + 1
            while second < len(lines) and not bodies[second].strip():
                second += 1
            if second == len(lines) or bodies[second].strip().casefold() not in {"don't miss!", "don’t miss!"}:
                i += 1
                continue
            cursor = second + 1
        elif i == navigation_first and ENGLISH_BULLET.fullmatch(bodies[i]):
            cursor = i
        else:
            i += 1
            continue
        categories = []
        while cursor < len(lines):
            if not bodies[cursor].strip():
                cursor += 1
                continue
            if not ENGLISH_BULLET.fullmatch(bodies[cursor]):
                break
            categories.append(cursor)
            cursor += 1
        if not categories:
            i += 1
            continue
        matches = [] if second is None else [
            {"start": starts[i], "end": starts[second] + len(bodies[second]), "detail": "navigation header"}
        ]
        matches.extend({"start": starts[j], "end": starts[j] + len(bodies[j]),
                        "detail": "navigation category link"} for j in categories)
        last = categories[-1]
        blocks.append({"start": starts[i], "end": starts[last] + len(lines[last]), "matches": matches})
        i = cursor
    def widget_kind(body):
        if body.strip().casefold() in {"don't miss!", "don’t miss!"}:
            return "navigation header"
        if SOCIAL_FOLLOW.fullmatch(body):
            return "social-follow prompt"
        if body.strip().strip("\"'‘’“”") == TRAFFIC_SLOGAN:
            return "traffic-safety slogan"
        if body.strip().casefold() == "trending":
            return "trending widget heading"
        if body.strip().casefold() == "title":
            return "website title label"
        if AGE_SUFFIX.search(body):
            return "topic or relative-age metadata"
        if (BYLINE_TIMESTAMP.fullmatch(body) or UPDATE_TIMESTAMP.fullmatch(body)
                or KANNADA_TIMESTAMP.fullmatch(body)):
            return "publication or update timestamp"
        return None

    navigation_blocks = tuple(blocks)
    i = 0
    while i < len(lines):
        if not widget_kind(bodies[i]) or any(b["start"] <= starts[i] < b["end"] for b in navigation_blocks):
            i += 1
            continue
        start, last, matches = i, i, []
        while i < len(lines):
            body = bodies[i]
            kind = widget_kind(body)
            if not body.strip():
                i += 1
                continue
            if body.strip() == "-":
                next_line = i + 1
                while next_line < len(lines) and not bodies[next_line].strip():
                    next_line += 1
                if next_line < len(lines) and widget_kind(bodies[next_line]):
                    kind = "widget separator"
            if not kind or any(b["start"] <= starts[i] < b["end"] for b in navigation_blocks):
                break
            matches.append({"start": starts[i], "end": starts[i] + len(body), "detail": kind})
            last = i
            i += 1
        blocks.append({"start": starts[start], "end": starts[last] + len(lines[last]), "matches": matches})
    return sorted(blocks, key=lambda block: block["start"])


def find_c1_matches(text):
    return [match for block in find_c1_blocks(text) for match in block["matches"]
            if match["detail"] != "navigation category link"]


def find_c5_matches(text):
    """Category-led teaser bullets in the same structurally recognized blocks."""
    return [match for block in find_c1_blocks(text) for match in block["matches"]
            if match["detail"] == "navigation category link"]


def c1_evidence(text, matches, redact=False):
    """Single-line evidence; header whitespace is collapsed for readability.

    Set redact=True for F1/E3 documents or overlapping sensitive matches.
    Exact source ranges remain in matches; offsets always refer to the source.
    """
    entries = []
    for match in matches:
        value = match["detail"] if redact else json.dumps(
            " ".join(text[match["start"]:match["end"]].split()), ensure_ascii=False
        )
        entries.append(f'C1: {value} at offset {match["start"]}')
    return " | ".join(entries)


def fix_c1_navigation(text):
    """Remove complete matched blocks; preserve all text outside them exactly."""
    pieces, previous = [], 0
    for block in find_c1_blocks(text):
        pieces.append(text[previous:block["start"]])
        previous = block["end"]
    pieces.append(text[previous:])
    return "".join(pieces)


def harm_test(gold_rows):
    """Count every changed gold document as harm, even if the edit looks useful."""
    total = changed = 0
    for row in gold_rows:
        text = row["text"]
        if not isinstance(text, str):
            raise ValueError("Every gold document must have a string text field")
        total += 1
        changed += fix_c1_navigation(text) != text
    if not total:
        raise ValueError("The gold set must not be empty")
    # This medicine fixes text and never drops a document, including empty output.
    return {"gold_documents": total, "changed_documents": changed, "dropped_documents": 0,
            "changed_or_dropped_documents": changed, "harm_percent": 100 * changed / total,
            "passes_harm_test": changed * 100 <= total}


def main():
    parser = argparse.ArgumentParser(description="Read a gold Parquet and report C1 harm counts; writes no dataset.")
    parser.add_argument("--gold", required=True, help="Kannada gold set marked clean by two readers")
    args = parser.parse_args()
    import pyarrow.parquet as pq
    print(json.dumps(harm_test(pq.read_table(args.gold, columns=["text"]).to_pylist()), indent=2))


if __name__ == "__main__":
    main()
