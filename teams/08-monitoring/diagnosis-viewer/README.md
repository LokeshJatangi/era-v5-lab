# Diagnosis pack viewer

A local viewer for the week 1 data diagnosis (`diagnosis/DISEASES.md`). It shows each document of your pack with
hidden characters made visible, lets you label it, and exports `labels.csv` in the template format.

```bash
pip install pyarrow
python teams/08-monitoring/diagnosis-viewer/review_server.py --pack <pack_id>.parquet
# open http://127.0.0.1:8765/
```

Options:

| Option | Meaning |
|---|---|
| `--labels labels.csv` | start from an existing label sheet; each row shows as the "starting label", which you confirm or change |
| `--reviews file.json` | where your labels are saved (default: `<pack_id>.reviews.json` next to the pack) |
| `--port N` | default 8765 |
| `--row N` | open 1-based row N, overriding the saved browser cursor for this startup |
| `--start N` | legacy 0-based starting index; mutually exclusive with `--row` |
| `--audit` | open whole-document audit diagnostics on load |

The viewer carries over the diagnostic approach from `diagnosis/tools/view_pack_2.py`:
unchanged original text, separate audit hints, Unicode ranges, and explicit row navigation.
`doc_id` and non-null string `text` are required. `source`, `lang_label`, and `url` are shown
when present; older packs without these metadata columns are still accepted. Empty packs,
missing required columns, and null/non-string text fail at startup with an explanatory error.

## What it shows

- **Visible characters** is the default. Every space is `⟦SPACE⟧`, every tab `⟦TAB⟧`, and every newline
  `⟦LF⟧` followed by a visual line break. CRLF is `⟦CR⟧⟦LF⟧`. Leading/trailing spaces, blank lines,
  final newlines, Unicode separators, controls, formatting characters and default-ignorable characters are exposed.
  Ordinary Kannada vowel signs remain part of their words. An unfamiliar/unassigned character gets an explicit marker.
- Each displayed line starts with `@offset`. Offsets and character counts use **zero-based Unicode code points**,
  matching Python and `view_pack_2.py`, even after emoji. They are not byte offsets, UTF-16 indices or grapheme counts.
  **Row / Open row** uses 1-based row numbers; metadata also shows the 0-based index. Jumping rows keeps local drafts.
- **Original text** inserts no markers, line numbers or evidence highlights. Use it to compare Indic shaping,
  because visible markers can interrupt conjuncts. Both modes use the unchanged source string.
- ZWJ and ZWNJ have neutral markers and are **not diseases in Indic text** (A1 note).
- A vowel sign or other combining mark at the start or after whitespace shows with a dotted circle.
  Kannada/Devanagari G1 context candidates after another script also receive this display aid;
  inspect source code points and context before labeling. Font shaping alone does not establish G1/G2.
- **Show all characters** or `h` opens the complete inventory: offset, Python character representation,
  `U+XXXX`, Unicode name, and category (such as `Cc` or `Zs`), for **every**
  character including ASCII, spaces, newlines and punctuation. There is no 300-row or 2,000-character cutoff.
  Control aliases are provided where available; unnamed controls, private-use and unassigned code points are identified explicitly.
- **Start offset / End (excluded) / Show range** displays every character in the original `[start, end)` range.
  Emoji count as one code point. **Show all** restores the full inventory. Invalid ranges show an error;
  inspection controls do not alter text or labels.
- **Whole-document audit** groups hidden/control/special characters by code point, with counts and first offsets,
  including occurrences beyond 2,000 characters. It excludes ordinary spaces and LF from this summary;
  both remain fully visible in the inventory. ZWJ/ZWNJ are diagnostic entries, not disease assignments.
  It also flags contiguous numeric tokens mixing ASCII, Kannada, or Devanagari digits (e.g. `೧0೭`, `१0७`).
  Separate numbers such as `1 ೨` and single-script digit tokens do not trigger this hint. Mixed digits alone
  do not establish G4 or justify converting digits.
- Text quoted in the evidence of the starting label is highlighted, and each `offset N` it cites is marked `▸`.
- The disease checkboxes come from `diagnosis/DISEASES.md`; hover a code for its name.
- Switching text modes or opening the inventory does not reset your unsaved label fields.

## Candidate checks

The sidebar lists candidate disease codes, occurrence counts, the check's method, cautions and source offsets.
Expand a code and use **Jump [start, end)** to highlight an occurrence in Visible characters mode. This does not
select disease checkboxes, fill evidence, change your verdict or save anything. The end offset is excluded.
H1 also identifies the other documents by pack index and `doc_id`.

These are review signals, not confirmed diagnoses or quality scores. A document with no candidates still needs
full-document reading. **Coverage and manual-review checks** lists the remaining codes and the evidence needed
to evaluate them. Names and checkboxes continue to come from `DISEASES.md`; its rules are unchanged.

| Code | Implemented check | Important limitation |
|---|---|---|
| A1 | U+200B, U+FEFF, U+00AD, U+202A–U+202E and U+2066–U+2069 | ZWJ/ZWNJ are excluded; not every visible marker is a disease. |
| A2 | U+0000–U+001F except TAB/LF, plus U+007F–U+009F | CR is included by the specification, including in CRLF; choose any action manually. |
| A3 | Common mojibake patterns, including Kannada-looking `à²…`/`à³…` sequences | A heuristic, not a complete encoding diagnosis; encoding examples can match. |
| A4 | Every U+FFFD occurrence | Cannot recover the original lost bytes. |
| A5 | Original ranges changed by NFC | Requires visual/meaning review under the rule; canonical differences alone do not establish damage. |
| A6 | Mixed Latin/Kannada words, Latin before a detached Kannada sign, or the reader's `ಅಽಕಾರಿ` form and attached Kannada suffixes | URLs, code, names and loanwords need context. `ಽ` is Kannada avagraha; other uses of avagraha are not automatically flagged. |
| B1 | Named and numeric HTML entity syntax | Technical examples can intentionally contain escapes. |
| B2 | Tag, comment and processing-instruction syntax | Literal markup can be valid; recognized ghost tokens are listed under B3 instead. |
| B3 | Special-token-like `<\|name\|>` syntax, `[INST]`/`[/INST]`, `<s>`/`</s>`, `<think>`/`</think>` and line-start `### Assistant/User/System:` headings | Read context, including literal examples; the list is not exhaustive. |
| B4 | Simple `{{ ... }}` and `${ ... }` expressions on one line | Nested/multiline templates are not parsed; ordinary mentions of `undefined` or `NaN` are not flagged. |
| B5 | Unclosed Markdown fence, LaTeX environment/command argument, or display delimiter | Structural hints; excerpts and literal syntax can be intentional. |
| C1 | Leading `ಮುಖಪುಟ`; city-pipe labels/breadcrumbs; traffic-safety slogan; navigation/widgets; relative ages; timestamps | Pipe syntax is structural, not a city lookup. Legitimate lists, tables, headings, quotations, datelines and date references can match; confirm context. |
| C2 | Repeated lines, exact sentence/line fragments anywhere in the document, and social attributions | Inline passage checks require at least 40 code points and four words. Two occurrences suffice; nested findings are suppressed. Exact passages preserve internal whitespace and joiners. Attribution dates may differ. Confirm context. |
| C5 | English-led navigation teasers, plus runs of two or more hashtags on one line | `#word`, `# word` and adjacent `#one#two` forms are supported, including Kannada. Headers are C1; teaser/tag entries are C5. Normal headings and isolated hashtags are not tag lists. Confirm context. |
| E3 | Private-key headers and credential-like assignments with values of at least eight characters | Can match placeholders and miss other formats or shorter secrets. Type and position only. |
| F1 | ASCII email-like tokens, contiguous 10-digit phone candidates starting with any digit, and Indian mobile formats with optional `+91` and spaces/hyphens | Leading-zero sequences are included. Overlapping mobile matches are counted once. Identifiers, public contacts and ordinary numbers can match; confirm context and private ownership. |
| G1 | Detached Kannada/Devanagari mark plus the reader's `ಕಾರಂ ತ`, `ಕರ್ನಾ ಟಕದ`, `ಸ ರ್ಧೆ`, `ಕೋಣೆ ಗಳ` examples | Evidence captures the surrounding word and its starting offset. Other full-letter splits require manual selection and fluent review. |
| G2 | Reader-supplied `ಹಾಲ್ನಲ್ಲಿ`, `ಡೌನ್ಲೋಡ್`, `ಲವ್ಸ್ಟೋರಿ`, `ಫೋಟೋಶೂಟ್ನಲ್ಲಿ`, `ಡಿಸ್ಪ್ಲೇ` forms and attached Kannada suffixes | A review list, not a general lost-joiner detector. Source/orthographic confirmation is still needed. |
| H1 | Exactly equal original text across pack documents | No trimming or normalization. Similar or canonically equivalent text is not treated as exact. |

Each pattern is only a candidate even where character presence or exact text equality is certain. D4/D5 need a
fluent reader; G2/G3/G4 generally need source or cleaning evidence; F2/H3 need reference material. The remaining
structural, language, code and near-duplicate rules have manual guidance rather than speculative flags.

The canonical disease catalogue is unchanged. At the reader's request, local A7/A8/A9 spacing labels are
consolidated under G1, including the two saved A7 reviews. Old browser drafts map those codes to G1 too.
This local review convention includes word splits beyond the catalogue's narrower matra/virama example;
it does not establish an upstream cause or justify automatically changing ordinary word boundaries.
Valid joined ordinals such as `10ನೇ` still need contextual judgment.

Each candidate occurrence has **Add CODE**, which checks the code and appends just that occurrence to the
browser draft. G1/G2/A6 use the original word and zero-based starting offset, for example
`G2: ಡೌನ್ಲೋಡ್ at offset 158`. No action adds hex. Existing hex is preserved except when F1/E3 requires it empty.
The group-level **Append CODE evidence** button still adds all occurrences. Neither action submits a label.

For an unrecognized example, click the word in Visible characters or Original text and click
**Mark G1**, **Mark G2**, **Mark A6**, **Mark D4**, or **Mark C1** in the sticky word toolbar. A known split-word candidate is picked as
a whole, including its internal space. You can also select an exact phrase. Leading/trailing whitespace is excluded;
spaces inside the word are kept. Offsets come from the unchanged source, not marker text or UTF-16 indices.
Markdown preview is for reading only; switch to Original text to select source evidence.
For D4, select the problematic word or phrase and click **Mark D4**. It adds `D4: <selected text> at offset N`
and checks D4 without adding hex or submitting a review. Translation quality remains the reader's judgment.
Manual selections record the actual selected source words and starting offset, even if an unrelated
phone/email candidate exists elsewhere in the document. Values overlapping an F1/E3 candidate remain
omitted. If F1/E3 is selected but no sensitive positions are known, source values remain masked.

**Open ID** finds a `doc_id` directly, including `903f40f262239bdd` for the `process` example at offset 523.
**Current labels.csv row** shows a live, quoted preview. Candidate highlights can be toggled without changing
labels. Markdown preview escapes source HTML, permits only HTTP(S) links, and loads no remote resources.

For C1 findings, **Append C1 evidence** explicitly adds the C1 checkbox and offset-based quotes to the current
browser draft, preserving existing evidence and other codes. An empty/clean verdict becomes `fix`; existing
`fix`/`drop` stays selected. It does not submit a review. Repeating the action does not duplicate the same entries.
For a navigation header plus category teasers, **Add C1 + C5 evidence** adds both codes in one click. C1 is
used for the header and C5 for each teaser/link line; individual Add C1/Add C5 buttons remain available.
For example, an LF-separated header and first category produce:

```text
C1: "Just In Don't Miss!" at offset 0 | C5: "- News ಕರ್ನಾಟಕದಲ್ಲಿ 573 ಕೊರೊನಾ ಸೋಂಕಿತರು ಪತ್ತೆ" at offset 20
```

Header whitespace is collapsed in the display quote; all offsets/ranges refer to the original text. If F1/E3 is
selected or detected, the action appends generic types and offsets instead of source quotes. The reusable repair,
test details and pending gold-set harm test are documented in
`diagnosis/submissions/ind-kn-fw2/LokeshJatangi/medicine.md`. The viewer detects candidates and adds evidence only;
it never runs the repair on the pack.

The final submission keeps executable Python snippets directly in `medicine.md`, with no separate medicine
module. Those proposed repairs are narrower than this viewer's candidate checks; ambiguous candidates are
not automatically repaired. Existing tests load the snippets from the Markdown. Gold harm validation is pending.

`Don't Miss!` also matches without `Just In`, including when it appears alone. In the reader's row 177,
`doc_id=d78b35287b746574`, the header is at offset 0 and the first News teaser starts at offset 12.
The combined action changes an empty/clean verdict to fix in the draft; it does not silently relabel saved reviews.

C5 also proposes each tag in a hashtag run such as `#BJP4Belagavi #BJP4Maski #BJP4Basavakalyana`.
Spaces after `#` are optional, and tags may be adjacent without spaces. Digits/underscores inside a tag and
Kannada letters/marks are supported. Two tags on the same line are required, so an ordinary `# Heading`
or an isolated hashtag does not establish a list. **Add C5** captures one tag and offset; **Append C5 evidence**
captures all candidates. Neither adds hex or submits a review.

The C1 rule also flags standalone `Trending` and `Title` lines (including `Title⟦LF⟧`), `ರಾಜಕೀಯ7 days ago`, and `ರಾಜಕೀಯ6 days ago`. The numeric age can use ASCII or
Kannada digits and must be followed by `day ago` or `days ago` at the line end (trailing spaces are allowed).
A standalone `-` between recognized widget lines is included; an unrelated bare hyphen is preserved. The
medicine removes only the matched blocks/lines, and its gold harm result remains pending.
The topic is unrestricted: `ಅಂತರಂಗ5 days ago`, `ದಿನದ ಸುದ್ದಿ5 days ago`, `ಲೈಫ್ ಸ್ಟೈಲ್4 days ago`,
`ಕ್ರೀಡೆ4 days ago` and ` ಭಾವ ಭೈರಾಗಿ5 days ago` all use the same suffix rule. A space between the topic and
number is optional; topic names can contain spaces, and leading/trailing spaces remain part of the source range.

C1 also flags complete publication/update timestamp lines, including:

```text
Team Udayavani, Feb 11, 2021, 3:27 PM IST
Last Modified ಶನಿವಾರ, 5 ಸೆಪ್ಟಂಬರ್ 2020 (10:08 IST)
First Published Jan 20, 2021, 2:58 PM IST
Updated: Thursday, June 10, 2021, 20:15 [IST]
ಬುಧವಾರ, 7 ಏಪ್ರಿಲ್ 2021 (11:15 IST)
```

Standalone Kannada date/time lines also match without a Published/Updated marker, with an optional Kannada
weekday, a day/month/year and a parenthesized time/timezone. `IST` by itself or in ordinary prose is not C1.
English-date formats support optional First Published/Published/Updated/Last Modified markers and bylines,
an optional weekday, English month name, day/year, 12- or 24-hour clock and a bare or bracketed timezone.
Publication markers accept a colon with or without a following space. Localized dates use one of those markers
and a parenthesized time/timezone. The whole line must match. Ordinary year/date mentions and narrative sentences are preserved.
Use **Append C1 evidence** to add the original line and offset to your local draft.

The leading `ಮುಖಪುಟ` homepage label is also C1 at the first nonblank document line. A standalone label line
is removed by the medicine; an inline breadcrumb matches only the label token. Later mentions and longer
words such as `ಮುಖಪುಟದ` are preserved. English navigation bullets immediately after a standalone homepage
label remain eligible for the top-of-document navigation rule.

C1 also includes pipe-terminated city/navigation labels at line starts, such as `ಬೆಂಗಳೂರು|`, `ಮೈಸೂರು|`,
`New Delhi|`, repeated `ಬೆಂಗಳೂರು| ಬೆಂಗಳೂರು|` labels and `ಮುಖಪುಟ | ಕರ್ನಾಟಕ | ಬೆಂಗಳೂರು |` breadcrumbs.
Unicode letters and combining marks are supported; there is no fixed city-name list. This is a structural
navigation signal, not proof that a label names a city. Pipe-delimited tables, code or meaningful datelines can
be false positives. The **whole label line must end in `|` followed only by whitespace and an actual LF/CRLF**.
The medicine removes that complete matching line. Inline related links such as `ಇದನ್ನೂ ಓದಿ | ಲೇಖನದ ಶೀರ್ಷಿಕೆ`
are preserved, as are `ಬೆಂಗಳೂರು| article text` and a final `ಬೆಂಗಳೂರು|` with no LF. Unpiped city mentions remain ordinary content.

The exact standalone slogan **ಜೀವ ರಕ್ಷಣೆಗಾಗಿ ಸಂಚಾರ ನಿಯಮ ಪಾಲಿಸಿ** is also C1. A line containing just the
phrase, optionally enclosed in quotation marks, is flagged. A longer sentence discussing the phrase is preserved.
Both rules use **Append C1 evidence** and retain original code-point offsets. A legitimate headline identical to
the slogan is a possible false positive for the gold harm test.

The standalone social prompt **Please follow and like us:** is C1 too. Case differences, horizontal
whitespace and an omitted colon are accepted. Longer sentences quoting or discussing the phrase are
preserved. Use **Add C1** to capture the prompt and its original offset without adding hex.

The **Vartha Bharati donation/support footer** is a site-specific C1 candidate. Both exact lines beginning
`‘ವಾರ್ತಾ ಭಾರತಿ’ ನಿಮಗೆ ಆಪ್ತವೇ ?` and ending `ಬೆಂಬಲಿಸಲು ಇಲ್ಲಿ ಕ್ಲಿಕ್ ಮಾಡಿ` must occur as a complete trailing
block, and the document URL must have host `varthabharati.in` or one of its subdomains. LF/CRLF and optional
trailing whitespace are supported; article mentions, partial appeals, other sites and look-alike domains are
preserved. Use **Append C1 evidence** to add the original range to the draft. The viewer never edits pack text.

`c1_site_boilerplate.py` removes the site-specific Vartha Bharati / News18 blocks, without applying the broader navigation heuristics. It can
report matches without output, or produce a **new** cleaned copy plus an offset-only manifest:

```bash
python3 teams/08-monitoring/diagnosis-viewer/c1_site_boilerplate.py --pack ind-kn-fw2.parquet
python3 teams/08-monitoring/diagnosis-viewer/c1_site_boilerplate.py --pack ind-kn-fw2.parquet --output ind-kn-fw2.c1-sites.parquet --report ind-kn-fw2.c1-sites.changes.json
python3 teams/08-monitoring/diagnosis-viewer/c1_site_boilerplate.py --gold /absolute/path/to/kannada_gold_with_urls.parquet
```

Existing output files are refused. All document IDs, row order, metadata and non-text columns are retained;
all characters outside the matched footer remain exact. Gold evaluation requires URL provenance and counts
every changed document as harm (≤1% passes). **The gold harm test has not been run**. The separately generated
cleaned diagnosis copy is a review artifact, not a measured passing gold result. See the medicine sheet for
the eight real source matches and original offsets, including index 146 / row 147 at `[1588, 1708)`.

For URLs with host **kannada.news18.com** and path `/news` or `/news/…`, the cleaner also removes complete
`news18-kannada Updated:` lines, a supported publication timestamp immediately following that line, and
standalone `India` lines. It preserves the following headline/body and inline mentions such as `India won`.
A timestamp alone is not removed by this site medicine; the viewer can still show it under the previously
implemented generic timestamp candidate rule. Identical C1 ranges are displayed/evidenced once. A genuine
one-word `India` heading on this site is a possible false positive and must count as gold harm.

The generated local copy `ind-kn-fw2.c1-sites.parquet` keeps all 500 documents. Its manifest
`ind-kn-fw2.c1-sites.changes.json` records 10 changed documents: 8 Vartha Bharati footers and 2 News18
metadata blocks, removing 1,073 code points in total. One other News18 document has no requested markers
and is unchanged. The source pack, review JSON, and saved label sheet have not been edited.

**Append C2 evidence**, **Append F1 evidence**, and **Append G1 evidence** are available on their candidate cards:

- C2 adds each repeated line's original content offset and repeat count, quoting up to 80 source code points per occurrence.
  Two occurrences suffice, including copies differing only in leading/trailing whitespace. Blank lines are ignored;
  different internal spacing, joiners, wrapped lines and paraphrases are not merged by this check.
  It also searches exact sentences and line fragments anywhere in the document, requiring at least 40 code
  points and four whitespace-separated words for this additional check. Repeats can start within a paragraph;
  nested ranges already covered by a larger repetition or line finding are not added again.
  In `0f52e8c63e977510` (row 414), the 249-character passage starts at 23 and 7915; the second is mid-paragraph.
  The reader's `c69e1a6483bd6ac2` example repeats its full 125-character opening line at offsets 0 and 3385;
  two occurrences now suffice to propose C2 for both ranges.
  Social attribution lines such as `— Parveen Kaswan (@ParveenKaswan)` also group with dated variants ending
  in `July 19, 2021` or `July 20, 2021`. Comparison uses the same author and handle, with cosmetic whitespace/case
  differences ignored; each candidate still includes its original date. In `205edeba4371d2c0` (row 490), the
  two dated attributions start at offsets 1049 and 1749. This is a review signal, not proof of unwanted duplication.
- F1 adds only the detected type and offset, never the email/phone value. It clears `hex` as required by the label rules.
- G1 adds the surrounding original word and starting offset, including a split before a vowel sign or virama.
  G2 and A6 use the same word-and-offset format. No hex is added.

All actions preserve existing evidence, add the corresponding checkbox, keep `fix`/`drop` or change an
empty/clean verdict to `fix`, and update the browser draft without submitting it. Repeating an action does not
duplicate identical entries. C2 source quotes are omitted whenever F1/E3 is selected or detected in the document.

Findings contain **no matched source values or snippets**, even for non-sensitive codes, since ranges can overlap
personal data or secrets. For F1/E3, write only type and original offset in evidence and leave `hex` empty. The
original document and its character inventory remain available locally for your authorized review.

## A5: finding NFC candidates in Kannada

Open **NFC / NFKC comparison**. The NFC section compares the original text with
`unicodedata.normalize("NFC", text)`. Changed ranges include context, before/after text, Unicode names and offsets.
Ranges are `[start, end)`; original offsets belong in your evidence. Preview offsets belong to the normalized string
and can differ because normalization changes the number of code points. Nearby edits may be grouped into one range.

For example, Kannada `ಕೊ` can be represented as:

```text
Before: U+0C95 KANNADA LETTER KA
        U+0CC6 KANNADA VOWEL SIGN E
        U+0CC2 KANNADA VOWEL SIGN UU
NFC:    U+0C95 KANNADA LETTER KA
        U+0CCA KANNADA VOWEL SIGN O
```

Similarly, `U+0C95 U+0CC6 U+0CC2 U+0CD5` becomes `U+0C95 U+0CCB` (`ಕೋ`). These are canonical
equivalents and should normally have the same appearance and meaning. A difference in code points is a review
candidate, not automatic proof of visual or semantic damage. Under the A5 rule in `DISEASES.md`, record any observed
change in appearance or meaning, its original offset, and both code-point sequences. Compare with Original text
and the NFC preview; the display font can also affect appearance.

## G4: earlier over-normalization

The NFKC section previews applying NFKC **now**; it cannot establish what happened before this pack was produced.
The **Compatibility changes beyond NFC** section compares the NFC baseline to NFKC, so ordinary canonical changes
are not confused with compatibility folding. Its before-offsets refer to the NFC baseline, not the source document.

NFKC can turn `①` (`U+2460`) or `１` (`U+FF11`) into `1` (`U+0031`), losing distinctions. But Kannada digits
`೦೧೨೩೪೫೬೭೮೯` (`U+0CE6`–`U+0CEF`) remain unchanged under **both NFC and NFKC**. Changing them to ASCII
`0123456789` requires a separate digit mapping. The G4 rule lists both kinds of earlier cleaning damage; it does
not mean NFKC converts Kannada digits. ASCII digits alone are not evidence of G4.

To confirm G4, use pre-cleaning source text or cleaning history showing the lost distinction. The current pack
has no paired originals, so absence of NFKC changes cannot establish absence of earlier damage. No labels are
selected automatically, and no preview modifies the document or saved evidence.

References: [Unicode normalization](https://www.unicode.org/reports/tr15/) and
[Unicode character data](https://www.unicode.org/Public/UCD/latest/ucd/UnicodeData.txt).

## Inspection endpoint

`GET /inspect?i=N` returns inspection for one zero-based document index: code-point length, a complete `characters`
inventory (`offset`, `code_point`, `name`, `category`, `marker`), Python's Unicode data version, and `nfc`, `nfkc`,
and `compatibility` comparisons. Each comparison supplies `changed`, preview `text`, and changed ranges with
original/baseline and normalized offsets plus before/after character inventories. Offsets inside each range's
character inventory are relative to that range; add `start` or `normalized_start` for absolute offsets.
Invalid indices return 400; out-of-range indices return 404. `/data.json` keeps source text and labels without
expanding all documents into inventories. The browser retains only the current inspection and ignores stale requests.

Inspection also returns `findings`, `checked_codes` and `manual_checks`. Each finding contains `code`, `kind`,
`summary`, `caution`, `count` and `matches` (`start`, `end`, generic `detail`). H1 additionally includes
`related_documents` (`i`, `doc_id`); its occurrence count is one document-level match and the summary gives the
number of other identical documents. `checked_codes` describes available checks, not completed human review.
The exact-duplicate index is built once when the server loads the pack; all other findings are calculated for
the requested document. Standalone `inspect_text()` calls without pack context report H1 as a manual check.
`/data.json` also supplies `pack_key`, a stable hash of the pack's resolved local path, for browser draft and
cursor namespacing. Different directories with the same pack filename get different keys.

## Keys

`j` / `k` next and previous · `c` select clean · `s` save your label · `h` code-point list.
Press `c` to select the clean verdict and keep it in the browser draft, then `s` to submit it. Selecting clean
does not submit, navigate, clear evidence or deselect disease codes. D3/H3 may accompany clean; other selected
codes must be removed before a clean label can be saved. **Select clean (c)** provides the same action by mouse.
**Confirm starting label** remains a separate button. Shortcuts are ignored while typing in form fields, using
Ctrl/Command/Alt combinations, composing text, or holding a repeating key.
Filters: not reviewed, changed against the starting label, starting verdict, a disease code, or a text search.

## Validation with synthetic documents

Run from the repository root and share the complete output:

```bash
python3 -m unittest discover -s teams/08-monitoring/diagnosis-viewer -p 'test_*.py' -v
```

The suite uses temporary synthetic Parquet/review files and a local server on an automatically assigned port.
Frontend checks run the actual viewer JavaScript with a minimal DOM using Node.js, when installed. They do not
verify browser layout or Kannada font shaping; a skipped frontend check is reported explicitly.

Create a separate browser demo:

```bash
python3 teams/08-monitoring/diagnosis-viewer/test_review_server.py --make-demo /tmp/kannada-viewer-demo
python3 teams/08-monitoring/diagnosis-viewer/review_server.py --pack /tmp/kannada-viewer-demo/synthetic.parquet --port 8766
```

Open `http://127.0.0.1:8766/` and inspect the sixteen synthetic documents:

1. Check leading/trailing spaces, `CR`/`LF`, a blank line, and the final newline; compare Original text.
2. Check the Kannada NFC examples, unchanged Kannada digits, separate NFKC changes, and neutral ZWJ/ZWNJ markers.
3. Check the emoji occupies offset 0, `ಮ` is at offset 3, and HTML/chat markers display as text. In the browser
   console, `window.viewerInjected` should be `undefined`. Check controls and invisible characters remain marked.
4. Open the complete inventory and scroll to its final `LINE FEED` entry, beyond 40,000 characters.
5. Confirm H1 identifies document 0 as an exact duplicate of document 4, and vice versa.
6. In document 5 click **Add C1 + C5 evidence**. Confirm C1 header offset 0, C5 first bullet offset 20,
   both checkboxes, a `fix` verdict and a local draft. Existing evidence/codes must remain, repeat clicks must not
   duplicate entries, and the reviewed count must stay unchanged until Save.
7. In document 6, append G1 and C2 evidence. The detached mark is at offset 2 after an emoji and newline;
   G1 adds the source fragment and offset, leaves hex unchanged, and C2 adds three occurrence offsets and the repeat count.
8. In document 7, append F1 evidence and confirm only type/offset are copied and hex is empty. Appending C2/G1
   afterward must keep hex empty and omit source quotes.
9. In document 8, append C1 evidence for `Trending`, both topic/age lines, their intervening `-` separator, and `Title`.
10. In document 9, append C1 evidence for both publication/update timestamps, preserving the following article title.
11. In document 10, append C1 evidence for the leading `ಮುಖಪುಟ` label and First Published timestamp.
12. In document 11, append C1 evidence for all pipe-terminated breadcrumb/city labels and the Kannada slogan.
13. In document 12 (row 13), append C1 evidence for the site-specific donation footer. The source text remains
    unchanged, the article body is preserved, and the action writes only a local draft until you save.
14. In document 13 (row 14), verify the News18 publisher label, following timestamp, and standalone India line
    appear as three C1 matches. Appending evidence must include each offset once and preserve existing text.
15. In document 14 (row 15), click Add G2 beside just `ಡೌನ್ಲೋಡ್`. Only that occurrence should be added, with
    its source offset and no hex. Add G1 beside `ವಣ ್ಸುವಾಗ` and A6 beside the `process` fragment. Repeat clicks
    must not duplicate evidence. Click a different word and use Mark G1/G2; also try selecting a phrase and compare offsets in the inventory.
16. In document 15 (row 16), compare both RA joiner orders and ZWNJ in Original text with a Kannada font.
    In Markdown preview, source HTML must remain escaped and the unsafe link must not become clickable.

Type an unsaved note, switch display modes and toggle the inventory, and confirm the note remains. Navigate rapidly
between documents and confirm the text and comparisons match the selected document. Save a synthetic label and
export it; confirm the seven template columns. Report browser results alongside terminal output.

Also expand candidate findings in the sidebar. Jump to an A2 occurrence in document 2 (the emoji starts at offset 0)
and an A5 occurrence in document 1. Confirm the target is highlighted, the code-point offset agrees with the
inventory, and your unsaved evidence, hex, note and selected labels remain unchanged. Inspect the manual guidance
for G2/G3/G4 and D4/D5. A candidate-free document must still request full reading and manual checks.

Check browser drafts as well: enter evidence, hex, a note and label selections in one row, move to another row,
enter a different draft, and return to the first row. Refresh and confirm both rows' edits are restored. Confirm
the ✎ markers and **Browser draft saved locally — not submitted** status. Save a draft and verify its marker
disappears, other rows' drafts remain, and export contains only saved/starting labels. On another synthetic row,
use **Discard local draft** and confirm the saved/starting label returns. If a save is pending while you type or
navigate away, the newer edits and the selected row must remain intact when its response arrives.

After those checks, open the Kannada pack with its existing startup options and inspect the beginning, middle and
end of a long document. Adding `--port 8766` lets you use the same address after stopping the synthetic server.

## Saving and export

Evidence, hex, notes, read status, verdict and disease selections are stored automatically as **browser-local
drafts**, per pack path and `doc_id`. Draft text retains its whitespace exactly. Input changes are captured
immediately and flushed before row switches, filter navigation and page exit. Returning to a row or reloading
restores its draft ahead of the server's saved/starting label. Rows with drafts show ✎, and the form reports whether
the draft is stored locally. **Discard local draft** restores the saved/starting fields for just that row.

Drafts use this browser profile's `localStorage`; use the same hostname and port to resume them. Clearing site
data removes drafts, and moving the pack to a different path uses a different namespace. If storage is blocked
or full, drafts remain in memory for navigation within the current tab and the form warns that they will not
survive closing/reloading. Unreadable stored drafts are reported rather than silently deleted.

Browser drafts are not submitted reviews and do not count as reviewed or enter exports. **Save my label** writes
to the server. A successful save clears the matching draft; a failed save retains it. Edits made during a save
request remain as a newer draft, and a response for an older row does not navigate the current row. Confirming a
starting label also preserves any different unsaved edits rather than silently discarding them.

Every save writes the reviews file at once, so you can stop at any time. **Export labels.csv** gives one row per
document: your saved label, or else the starting label. Copy it to
`diagnosis/submissions/<pack_id>/<your-github-handle>/labels.csv`.

## Rules it does not enforce for you

- The server binds to `127.0.0.1` only. Do not change that, and do not commit the pack or the reviews file.
- For F1 and E3, write only the type and the offset (`phone number at offset 2432`). Never the value.
- A `clean` verdict requires reading the whole document. In this review workflow, D3 and H3 may be recorded with
  `clean`, individually or together. The form blocks any other disease code with `clean` and requires at least
  one code for `fix` or `drop`.
