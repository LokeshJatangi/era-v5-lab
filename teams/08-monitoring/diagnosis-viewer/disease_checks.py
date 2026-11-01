"""Local candidate signals for DISEASES.md; never assign labels or clean text.

No matched source values or excerpts are included in findings. This also keeps
F1/E3 suggestions safe to use as type-and-offset evidence.
"""
from collections import defaultdict
import re
import unicodedata
from c1_navigation import DAY, MONTH, find_c1_matches, find_c5_matches
from c1_site_boilerplate import find_site_boilerplate


CHECKS = {
    "A1": ("direct", "Specified invisible-junk characters", "ZWJ and ZWNJ are excluded. Other invisible characters are still available in the inventory."),
    "A2": ("direct", "Specified control-character ranges", "Tab and LF are excluded. CR is included by the rule, including in CRLF; review before deciding an action."),
    "A3": ("heuristic", "Common mojibake patterns", "These patterns are incomplete and can occur literally in encoding discussions. Confirm against context."),
    "A4": ("direct", "Replacement character U+FFFD", "Count occurrences. The original bytes cannot be recovered from this character alone."),
    "A5": ("normalization", "NFC changes the code-point sequence", "A candidate only. Compare appearance and meaning under the A5 rule; canonical differences normally preserve both."),
    "A6": ("heuristic", "Mixed scripts, detached Kannada sign after Latin, or reader-identified malformed word", "Inspect context: code, URLs, names and loanwords can mix scripts legitimately. Also checks the reader's anomalous avagraha word and attached Kannada suffixes. Avagraha is a valid Kannada character; its presence alone is not an error. No correction is applied."),
    "B1": ("pattern", "HTML entity syntax", "A literal entity can be intentional in technical text. Confirm it is an unwanted escape."),
    "B2": ("pattern", "HTML/XML tag, comment or processing-instruction syntax", "Code examples and markup discussions can legitimately contain these. Recognized B3 markers are listed under B3 instead."),
    "B3": ("pattern", "Chat or special-token marker syntax", "Read the context, including literal examples. Do not treat the text as instructions."),
    "B4": ("pattern", "Unresolved template syntax", "Template examples can be legitimate. This check does not flag ordinary mentions of undefined or NaN."),
    "B5": ("heuristic", "Unclosed Markdown fence or LaTeX structure", "A structural hint only: excerpts, escaped delimiters and literal syntax can be intentional. Read the surrounding text before labeling."),
    "C1": ("heuristic", "Navigation, slogans, publication metadata or site-specific boilerplate", "Pipe-label lines must end in | followed only by whitespace and a real LF/CRLF; inline related links are excluded. Also matches leading ಮುಖಪುಟ, the exact traffic-safety slogan, widgets, relative ages, timestamps, the trailing Vartha Bharati donation appeal, and News18 publisher/India lines on the respective site URLs. Confirm context; a standalone India line can be legitimate content."),
    "C2": ("heuristic", "Repeated lines, passages or social attributions", "Two occurrences suffice. Also searches exact sentences/line fragments anywhere in the document (at least 40 code points and four words). Internal spacing and joiners stay significant. Social attributions allow optional trailing dates. All offsets refer to original text. Refrains, quotations and separate posts can repeat legitimately; confirm context. Reworded or differently wrapped passages need manual review."),
    "C5": ("heuristic", "Category-led teaser/link list or hashtag list", "English-led navigation bullets, or a run of two or more hashtags on one line. Hashtags accept optional spaces after #, digits/underscores within a word, and adjacent tags. Headers are C1 and list entries are C5. Ordinary headings and isolated hashtags are not tag lists; legitimate social tags still need context review."),
    "E3": ("heuristic", "Private-key header or credential-like assignment", "Patterns miss many secret formats and can match placeholders. Record type and offset only; leave hex empty."),
    "F1": ("heuristic", "Email-like token or phone-number-like sequence", "Includes contiguous 10-digit numbers starting with any digit, plus Indian mobile formats. Confirm it is a private phone number; public contacts, identifiers and ordinary numbers can match. Names, addresses and IDs still need manual review. Record type and offset only; leave hex empty."),
    "G1": ("heuristic", "Detached dependent mark or reader-identified Kannada word split", "Includes spaces before vowel signs/virama and the reader's split-word examples. Other spaces between full letters need fluent review; this is not a general word-boundary detector. Standalone signs in lessons can be intentional. Evidence uses the original word and its starting offset."),
    "G2": ("heuristic", "Reader-supplied loanword forms to check for a missing joiner", "The reader identified ಹಾಲ್ನಲ್ಲಿ, ಡೌನ್ಲೋಡ್, ಲವ್ಸ್ಟೋರಿ, ಫೋಟೋಶೂಟ್ನಲ್ಲಿ and ಡಿಸ್ಪ್ಲೇ as review examples. These forms and attached Kannada suffixes are candidates, not proof of loss. Absence of ZWJ/ZWNJ alone proves nothing. Compare source or confirm orthography before labeling; never insert joiners automatically."),
    "H1": ("exact", "Identical source text elsewhere in this pack", "Compared without trimming or normalization. Confirm document identities and choose a verdict manually."),
}

MANUAL_CHECKS = {
    "C3": "Read the ending and any code blocks for abrupt cuts. Missing final punctuation alone does not establish truncation.",
    "C4": "Look for unrelated titles, authors or topics joined without a boundary; distinguish deliberate collections and quotations.",
    "D1": "Compare the language label with the full document. Script alone does not establish language.",
    "D2": "Read Latin-script passages to identify romanised Kannada; English words alone do not establish D2.",
    "D3": "Identify natural language mixing in sentences. Label the mixing without treating it as automatic damage.",
    "D4": "A fluent reader must assess meaning and grammar, using a source translation if available. If you cannot judge it, mark the read partial.",
    "D5": "A fluent reader must judge whether the phrasing is natural. If you cannot judge it, mark the read partial.",
    "E1": "For code packs, inspect unusually long lines and generator notices; length alone does not establish generated or minified code.",
    "E2": "For code packs, inspect base64, arrays and embedded assets; distinguish necessary program data from an unwanted blob.",
    "E4": "For code packs, compare licence headers across files; repeated licence terms can be legitimate.",
    "E5": "For code packs, inspect encoding problems specifically inside strings or comments; A3 flags are only general hints.",
    "E6": "For code packs, compare the content type with the code label; prose in a Kannada prose pack is not E6.",
    "F2": "Requires a known benchmark reference and a verifiable match; familiar question wording alone is insufficient.",
    "F3": "Assess content against the project's training policy and context; this version does not use keyword-based harmful-content judgments.",
    "G3": "Requires source text or cleaning/quality logs showing that good Indic content was dropped; this pack alone cannot establish it.",
    "G4": "Requires source text or cleaning history showing lost distinctions. The NFKC preview is hypothetical; ASCII digits alone are insufficient.",
    "H2": "Compare similar documents manually; no near-duplicate search is included in the precise-check scope.",
    "H3": "Requires another source or language document and a content comparison; this version does not search external corpora. H3 may be recorded with clean, alone or together with D3.",
}


def _legacy_byte_char(value):
    try:
        return bytes([value]).decode("cp1252")
    except UnicodeDecodeError:
        return chr(value)


LEGACY_BYTES = {_legacy_byte_char(value): value for value in range(0x80, 0x100)}
LEGACY_BYTES.update({chr(value): value for value in range(0x80, 0x100)})
CONTINUATION = "[" + re.escape("".join(sorted({ch for ch, value in LEGACY_BYTES.items() if value < 0xC0}))) + "]"
MOJIBAKE = re.compile(rf"(?:[\u00c2-\u00df]{CONTINUATION}|[\u00e0-\u00ef]{CONTINUATION}{{2}}|[\u00f0-\u00f4]{CONTINUATION}{{3}})+")


def mojibake_candidates(text):
    for match in MOJIBAKE.finditer(text):
        try:
            bytes(LEGACY_BYTES.get(ch, ord(ch)) for ch in match.group()).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            continue
        yield match


ENTITY = re.compile(r"&(?:[A-Za-z][A-Za-z0-9]{1,31}|#[0-9]{1,7}|#[xX][0-9A-Fa-f]{1,6});")
TAG = re.compile(r"<!--[\s\S]*?-->|<\?[\s\S]*?\?>|</?[A-Za-z][A-Za-z0-9:_-]*(?:\s+[^<>]*?)?\s*/?>")
CHAT = re.compile(r"<\|[A-Za-z0-9_. -]{1,80}\|>|\[/?INST\]|<</?SYS>>|</?s>|</?think(?:ing)?>|<(?:bos|eos|unk|pad|mask|start_of_turn|end_of_turn)>|\[(?:CLS|SEP|MASK|PAD|UNK)\]|^[ \t]*#{1,4}[ \t]*(?:Assistant|User|Human|System|Instruction|Response)[ \t]*:|^[ \t]*(?:Human|Assistant)[ \t]*:", re.MULTILINE | re.IGNORECASE)
TEMPLATE = re.compile(r"\{\{[^{}\r\n]{1,200}\}\}|\$\{[^{}\r\n]{1,200}\}")
EMAIL = re.compile(r"(?<![\w@])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w@])")
MOBILE = re.compile(r"(?<![\w+])(?:\+91[ -]?)?[6-9](?:[ -]?[0-9]){9}(?![\w-])")
CONTIGUOUS_PHONE = re.compile(r"(?<![\w+])[0-9]{10}(?![\w-])")
SOCIAL_ATTRIBUTION = re.compile(
    rf"[—–-][ \t]+(?P<name>[^@()\r\n]{{1,120}}?)[ \t]*"
    rf"\(@(?P<handle>[A-Za-z0-9_]{{1,50}})\)"
    rf"(?:[ \t]+{MONTH}\.?[ \t]+{DAY},[ \t]+[0-9]{{4}})?",
    re.IGNORECASE,
)
PRIVATE_KEY = re.compile(r"-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----")
CREDENTIAL = re.compile(r"\b(?:api[_-]?key|secret|password|(?:access[_-]?|auth[_-]?)?token)\b[\"']?\s*[:=]\s*[\"']?[^\s\"'<>]{8,}", re.IGNORECASE)

# Match the updated view_pack_2.py's Devanagari context rule, with Kannada
# marks selected by Unicode category/name so independent letters are excluded.
DEVANAGARI_DEPENDENT_MARKS = (
    set(range(0x093A, 0x0950)) | set(range(0x0951, 0x0958))
    | set(range(0x0962, 0x0964))
)

# Narrow, reader-supplied patterns. Ordinary Kannada word boundaries and native
# consonant clusters are deliberately not inferred to be damaged.
WORD_EDGE = r"[\w\u0C80-\u0CFF\u200c\u200d]"
READER_A6_WORD = re.compile(rf"(?<!{WORD_EDGE})ಅಽಕಾರಿ[\u0C80-\u0CFF]*(?!{WORD_EDGE})")
G1_SPLITS = re.compile(
    rf"(?<!{WORD_EDGE})(?:ಕಾರಂ[ \t]+ತ|ಕರ್ನಾ[ \t]+ಟಕದ|ಸ[ \t]+ರ್ಧೆ|ಕೋಣೆ[ \t]+ಗಳ)(?!{WORD_EDGE})"
)
G2_LOANWORDS = re.compile(
    rf"(?<!{WORD_EDGE})(?:ಹಾಲ್ನಲ್ಲಿ|ಡೌನ್ಲೋಡ್|ಲವ್ಸ್ಟೋರಿ|ಫೋಟೋಶೂಟ್ನಲ್ಲಿ|ಡಿಸ್ಪ್ಲೇ)[\u0C80-\u0CFF]*(?!{WORD_EDGE})"
)


def word_character(ch):
    return ch in "\u200c\u200d" or unicodedata.category(ch)[0] in "LM"


def hashtag_list_candidates(text):
    """Find tag-list runs, preserving source offsets and Indic marks/joiners.

    Require two tags so a normal '# Heading' is not a keyword-list finding.
    A tag starts with a letter; numeric HTML entities and issue numbers are not
    tags. Do not start a run inside a word, escape sequence or URL fragment.
    """
    offset = 0
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n\v\f\x1c\x1d\x1e\x85\u2028\u2029")
        run = []
        for match in re.finditer(r"#[ \t]*", body):
            start, end = match.start(), match.end()
            if (start and body[start - 1] in "#&\\") or end == len(body):
                continue
            if not unicodedata.category(body[end]).startswith("L"):
                continue
            while end < len(body) and (word_character(body[end])
                    or unicodedata.category(body[end]).startswith("N") or body[end] == "_"):
                end += 1
            separator = body[run[-1][1]:start] if run else None
            if run and all(ch.isspace() or ch in ",;|" for ch in separator):
                run.append((start, end))
            else:
                if len(run) >= 2:
                    for left, right in run:
                        yield offset + left, offset + right
                run = []
                if not start or not (word_character(body[start - 1])
                        or body[start - 1].isalnum() or body[start - 1] in "_/=?:.%"):
                    run.append((start, end))
        if len(run) >= 2:
            for left, right in run:
                yield offset + left, offset + right
        offset += len(line)


def surrounding_word(text, start, end):
    """Expand a mark to its token, including a preceding split token on one line."""
    left, right = start, end
    while left and word_character(text[left - 1]):
        left -= 1
    while right < len(text) and word_character(text[right]):
        right += 1
    if left == start and left and text[left - 1] in " \t":
        gap = left
        while gap and text[gap - 1] in " \t":
            gap -= 1
        # Do not borrow the preceding line or an unrelated Latin token for G1.
        if gap and "\u0900" <= text[gap - 1] <= "\u0cff":
            left = gap
            while left and word_character(text[left - 1]):
                left -= 1
    return left, right


def g1_word_candidates(text):
    ranges = {}
    for match in detached_mark_candidates(text):
        span = surrounding_word(text, match["start"], match["end"])
        ranges[span] = "possibly split word containing a detached dependent mark"
    for match in G1_SPLITS.finditer(text):
        ranges[(match.start(), match.end())] = "reader-identified possible space inside a Kannada word"
    return [{"start": start, "end": end, "detail": detail}
            for (start, end), detail in sorted(ranges.items())]


def mixed_script_candidates(text):
    ranges = set()
    start = None
    for i in range(len(text) + 1):
        if i < len(text) and word_character(text[i]):
            if start is None:
                start = i
        elif start is not None:
            scripts = {unicodedata.name(ch, "").split(" ")[0] for ch in text[start:i]}
            if "KANNADA" in scripts and "LATIN" in scripts:
                ranges.add((start, i))
            start = None
    # A space between a Latin word and a dependent sign is corruption worth
    # inspecting too, even though the space separates the script runs.
    for match in re.finditer(r"[A-Za-z]+[ \t]+(?P<mark>[\u0C80-\u0CFF])", text):
        if unicodedata.category(match["mark"]).startswith("M"):
            end = match.end()
            while end < len(text) and word_character(text[end]):
                end += 1
            ranges.add((match.start(), end))
    return sorted(ranges)


def repeated_passage_candidates(text, covered_ranges=()):
    """Search substantial source sentences/lines as exact substrings anywhere.

    A repeat need not start at a newline or sentence boundary in its other
    occurrence. Longest fragments go first to avoid nested evidence, and ranges
    already reported by line/attribution checks are not added again. This does
    not normalize whitespace, joiners, case or source characters.
    """
    fragments = {line.strip() for line in text.splitlines()}
    fragments.update(match.group().strip() for match in
                     re.finditer(r"[^.!?।॥\r\n]+(?:[.!?।॥]+|(?=[\r\n]|$))", text))
    fragments = [fragment for fragment in fragments if len(fragment) >= 40
                 and len(fragment.split()) >= 4]
    covered = list(covered_ranges)
    for fragment in sorted(fragments, key=lambda value: (-len(value), value)):
        occurrences, cursor = [], 0
        while True:
            start = text.find(fragment, cursor)
            if start < 0:
                break
            end = start + len(fragment)
            # Do not identify a matching suffix/prefix inside a larger word.
            left_ok = not (start and word_character(fragment[0]) and word_character(text[start - 1]))
            right_ok = not (end < len(text) and word_character(fragment[-1]) and word_character(text[end]))
            if left_ok and right_ok:
                occurrences.append((start, end))
            cursor = end
        if len(occurrences) < 2:
            continue
        for start, end in occurrences:
            if not any(left <= start and end <= right for left, right in covered):
                yield start, end, len(occurrences)
                covered.append((start, end))


def broken_structure_candidates(text):
    fence = None
    for match in re.finditer(r"(?m)^[ \t]*(?P<fence>`{3,}|~{3,})(?P<tail>[^\r\n]*)", text):
        marker = match["fence"]
        if fence is None:
            fence = (marker[0], len(marker), match.start("fence"), match.end("fence"))
        elif marker[0] == fence[0] and len(marker) >= fence[1] and not match["tail"].strip():
            fence = None
    if fence:
        yield fence[2], fence[3], "unclosed Markdown code fence"
    stack = []
    for match in re.finditer(r"\\(?P<kind>begin|end)\{(?P<env>[^}\r\n]{1,80})\}", text):
        if match["kind"] == "begin":
            stack.append(match)
        elif stack and stack[-1]["env"] == match["env"]:
            stack.pop()
        else:
            yield match.start(), match.end(), "unmatched LaTeX environment end"
    for match in stack:
        yield match.start(), match.end(), "unclosed LaTeX environment"
    for match in re.finditer(r"\\[A-Za-z]+[ \t]*\{", text):
        depth, i = 1, match.end()
        while i < len(text) and depth:
            if text[i] == "\\":
                i += 2
                continue
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        if depth:
            yield match.start(), match.end(), "unclosed LaTeX command argument"
    displays = list(re.finditer(r"(?<!\\)\$\$", text))
    if len(displays) % 2:
        match = displays[-1]
        yield match.start(), match.end(), "unpaired LaTeX display delimiter"


def detached_mark_candidates(text):
    matches = []
    for i, ch in enumerate(text):
        cp = ord(ch)
        if (unicodedata.category(ch).startswith("M")
                and unicodedata.name(ch, "").startswith("KANNADA")):
            script, low, high = "Kannada", 0x0C80, 0x0CFF
        elif cp in DEVANAGARI_DEPENDENT_MARKS:
            script, low, high = "Devanagari", 0x0900, 0x097F
        else:
            continue
        prev = text[i - 1] if i else None
        if prev in {"\u200c", "\u200d"}:
            continue
        if prev is None or prev.isspace() or not low <= ord(prev) <= high:
            context = "START OF TEXT" if prev is None else f"U+{ord(prev):04X} {unicodedata.name(prev, 'UNNAMED')}"
            matches.append({"start": i, "end": i + 1,
                            "detail": f"possibly detached {script} mark U+{cp:04X}; predecessor {context}"})
    return matches


def exact_duplicate_groups(docs):
    """Index identical raw text without copying or normalizing it."""
    groups = defaultdict(list)
    for i, doc in enumerate(docs):
        groups[doc["text"]].append(i)
    return {i: tuple(indices) for indices in groups.values() if len(indices) > 1 for i in indices}


def candidate_report(text, nfc_changes, duplicate_documents=None, url=None):
    found = defaultdict(list)

    def add(code, start, end, detail):
        found[code].append({"start": start, "end": end, "detail": detail})

    for i, ch in enumerate(text):
        cp = ord(ch)
        if cp in {0x200B, 0xFEFF, 0x00AD} or 0x202A <= cp <= 0x202E or 0x2066 <= cp <= 0x2069:
            add("A1", i, i + 1, f"U+{cp:04X} {unicodedata.name(ch, 'UNNAMED')}")
        if (cp < 32 and ch not in "\t\n") or 0x7F <= cp <= 0x9F:
            add("A2", i, i + 1, f"control U+{cp:04X}")
        if cp == 0xFFFD:
            add("A4", i, i + 1, "replacement character U+FFFD")

    for match in g1_word_candidates(text):
        add("G1", match["start"], match["end"], match["detail"])
    for match in G2_LOANWORDS.finditer(text):
        add("G2", match.start(), match.end(), "reader-supplied loanword form; check missing joiner")
    for start, end in mixed_script_candidates(text):
        add("A6", start, end, "mixed-script word or Latin text before a detached Kannada sign")
    for match in READER_A6_WORD.finditer(text):
        add("A6", match.start(), match.end(), "reader-identified malformed Kannada word containing avagraha")
    for start, end, detail in broken_structure_candidates(text):
        add("B5", start, end, detail)
    for match in mojibake_candidates(text):
        add("A3", match.start(), match.end(), "possible UTF-8 decoded as a legacy encoding; verify source")

    for change in nfc_changes:
        add("A5", change["start"], change["end"], "NFC changes this original range; compare in the normalization panel")

    seen_c1 = set()
    for match in find_site_boilerplate(text, url) + find_c1_matches(text):
        span = (match["start"], match["end"])
        if span not in seen_c1:
            add("C1", *span, match["detail"])
            seen_c1.add(span)
    teaser_matches = find_c5_matches(text)
    for match in teaser_matches:
        add("C5", match["start"], match["end"], match["detail"])
    for start, end in hashtag_list_candidates(text):
        if not any(match["start"] <= start and end <= match["end"] for match in teaser_matches):
            add("C5", start, end, "hashtag keyword/tag-list entry")

    mobile_ranges = [(match.start(), match.end()) for match in MOBILE.finditer(text)]
    for start, end in mobile_ranges:
        add("F1", start, end, "Indian-mobile-number-like token")
    for match in CONTIGUOUS_PHONE.finditer(text):
        if not any(start <= match.start() and match.end() <= end for start, end in mobile_ranges):
            add("F1", match.start(), match.end(), "phone-number-like digit sequence")

    chat_ranges = [(m.start(), m.end()) for m in CHAT.finditer(text)]
    for start, end in chat_ranges:
        add("B3", start, end, "chat-marker-like syntax")
    for match in TAG.finditer(text):
        if not any(start <= match.start() and match.end() <= end for start, end in chat_ranges):
            add("B2", match.start(), match.end(), "markup-like syntax")

    for code, pattern, detail in [
        ("B1", ENTITY, "HTML-entity-like syntax"),
        ("B4", TEMPLATE, "unresolved-template-like syntax"),
        ("E3", PRIVATE_KEY, "private-key header"),
        ("E3", CREDENTIAL, "credential-like assignment"),
        ("F1", EMAIL, "email-like token"),
    ]:
        for match in pattern.finditer(text):
            # Never put match.group() into findings, even for non-sensitive
            # rules: their source ranges can overlap personal data or secrets.
            add(code, match.start(), match.end(), detail)

    lines, offset = defaultdict(list), 0
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n\v\f\x1c\x1d\x1e\x85\u2028\u2029")
        content = body.strip()
        if content:
            start = offset + len(body) - len(body.lstrip())
            attribution = SOCIAL_ATTRIBUTION.fullmatch(content)
            key = ("social-attribution", " ".join(attribution["name"].split()).casefold(),
                   attribution["handle"].casefold()) if attribution else ("exact", content)
            lines[key].append((start, start + len(content)))
        offset += len(line)
    for key, occurrences in lines.items():
        if len(occurrences) >= 2:
            detail = (f"same author/handle attribution occurs {len(occurrences)} times (optional trailing dates ignored)"
                      if key[0] == "social-attribution" else
                      f"line content occurs {len(occurrences)} times (ignoring outer whitespace)")
            for start, end in occurrences:
                add("C2", start, end, detail)

    covered = [(match["start"], match["end"]) for match in found.get("C2", [])]
    for start, end, count in repeated_passage_candidates(text, covered):
        add("C2", start, end, f"exact passage occurs {count} times (independent of line starts)")

    if duplicate_documents:
        add("H1", 0, len(text), f"identical text in {len(duplicate_documents)} other pack document(s)")

    findings = []
    for code in sorted(found):
        kind, summary, caution = CHECKS[code]
        matches = sorted(found[code], key=lambda m: (m["start"], m["end"]))
        finding = {"code": code, "kind": kind, "summary": summary, "caution": caution,
                   "count": len(matches), "matches": matches}
        if code == "H1":
            finding["related_documents"] = duplicate_documents
        findings.append(finding)

    manual = [{"code": code, "reason": reason} for code, reason in sorted(MANUAL_CHECKS.items())]
    checked = sorted(CHECKS)
    if duplicate_documents is None:
        checked.remove("H1")
        manual.append({"code": "H1", "reason": "Exact-duplicate checking requires the pack's other documents."})
    return {"findings": findings, "checked_codes": checked, "manual_checks": sorted(manual, key=lambda m: m["code"])}
