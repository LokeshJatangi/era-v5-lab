"""Synthetic checks only; no real pack text or reviews are read or modified.

Run: python3 -m unittest discover -s teams/08-monitoring/diagnosis-viewer -p 'test_*.py' -v
Demo: python3 teams/08-monitoring/diagnosis-viewer/test_review_server.py --make-demo /tmp/kannada-viewer-demo
"""
import csv
import io
import importlib.util
import json
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pyarrow as pa
import pyarrow.parquet as pq

import review_server as server
from disease_checks import CHECKS, MANUAL_CHECKS
from c1_site_boilerplate import FOOTER


HERE = Path(__file__).resolve().parent
SAMPLES = [
    "  ಕನ್ನಡ\tಪಠ್ಯ  \r\n\nಕೊನೆ  \n",
    "NFC: \u0c95\u0cc6\u0cc2 / \u0c95\u0cc6\u0cc2\u0cd5\n"
    "Digits: ೦೧೨೩೪೫೬೭೮೯; compatibility: ① １\n"
    "Joiners: ಕ್\u200dಕ ಕ್\u200cಕ\n",
    "😀ಕ\nಮ <script>window.viewerInjected=true</script> <|im_start|>\n"
    "\x00\x7f\x85\u00a0\u200b\ufeff\u00ad\u202e\u2069\u034f\ufe0f\u2028\u2029\ufffd",
    "ಕನ್ನಡ " * 8000 + "\nEND  \n",
]
# A fifth demo document has byte-for-byte identical source text for H1.
SAMPLES.append(SAMPLES[0])
SAMPLES.append("Just In\nDon't Miss!\n- News ಕರ್ನಾಟಕದಲ್ಲಿ 573 ಕೊರೊನಾ ಸೋಂಕಿತರು ಪತ್ತೆ\n- Finance ಬಜೆಟ್ 2021\nಕನ್ನಡ ಮೂಲ ಲೇಖನ\n")
SAMPLES.append("😀\n\u0cbf\n" + "ಮಾದರಿ ಸಾಲು\n" * 3)
SAMPLES.append(SAMPLES[6] + "synthetic-contact" + "@" + "example.invalid\n")
SAMPLES.append("Trending\nರಾಜಕೀಯ7 days ago\n-\nರಾಜಕೀಯ6 days ago\nTitle\nಕನ್ನಡ ಮೂಲ ಲೇಖನ\n")
SAMPLES.append("Team Udayavani, Feb 11, 2021, 3:27 PM IST\nLast Modified ಶನಿವಾರ, 5 ಸೆಪ್ಟಂಬರ್ 2020 (10:08 IST)\nಕನ್ನಡ ಲೇಖನದ ಶೀರ್ಷಿಕೆ\nಮೂಲ ಲೇಖನ\n")
SAMPLES.append("ಮುಖಪುಟ\nFirst Published Jan 20, 2021, 2:58 PM IST\nಲೇಖನದ ಶೀರ್ಷಿಕೆ\nಮೂಲ ಪಠ್ಯ\n")
SAMPLES.append("ಮುಖಪುಟ | ಕರ್ನಾಟಕ | ಬೆಂಗಳೂರು |\nಮೈಸೂರು| ಮೈಸೂರು|\nಜೀವ ರಕ್ಷಣೆಗಾಗಿ ಸಂಚಾರ ನಿಯಮ ಪಾಲಿಸಿ\nಲೇಖನದ ಶೀರ್ಷಿಕೆ\nಮೂಲ ಪಠ್ಯ\n")
SAMPLES.append("😀\nಕನ್ನಡ ಮೂಲ ಲೇಖನ.\n" + FOOTER)
SAMPLES.append("news18-kannada Updated:\nFebruary 14, 2021, 6:22 PM IST\nIndia\nಕನ್ನಡ ಮೂಲ ಲೇಖನ.\n")
SAMPLES.append("😀\nವಣ ್ಸುವಾಗ ಕಾರಂ ತ ಕರ್ನಾ ಟಕದ ಸ ರ್ಧೆ ಕೋಣೆ ಗಳ\nಹಾಲ್ನಲ್ಲಿ ಡೌನ್ಲೋಡ್ ಲವ್ಸ್ಟೋರಿ ಫೋಟೋಶೂಟ್ನಲ್ಲಿ ಡಿಸ್ಪ್ಲೇ\nprocess ಾಯಾಚಿತ್ರದೊಂದಿಗೆ\n")
SAMPLES.append("ರ\u200d್ಕ ರ್\u200dಕ ಒನ್\u200cಪ್ಲಸ್\n# Preview\n<script>window.viewerInjected=true</script>\n[unsafe](javascript:alert)\n")
SAMPLE_URLS = {12: "https://m.varthabharati.in/article/2021_04_07/285999",
               13: "https://kannada.news18.com/news/sports/synthetic.html"}


def write_demo(directory):
    directory.mkdir(parents=True, exist_ok=True)
    pack = directory / "synthetic.parquet"
    docs = [{"doc_id": f"synthetic-{i}", "text": text, "source": "synthetic",
             "lang_label": "kn", "url": SAMPLE_URLS.get(i, "")} for i, text in enumerate(SAMPLES)]
    pq.write_table(pa.Table.from_pylist(docs), pack)
    return pack


class CharacterTests(unittest.TestCase):
    def test_every_character_and_final_whitespace(self):
        text = SAMPLES[0]
        rows = server.character_inventory(text)
        self.assertEqual(len(rows), len(text))
        self.assertEqual([r["offset"] for r in rows], list(range(len(text))))
        self.assertEqual(rows[-1]["name"], "LINE FEED")
        self.assertEqual(rows[-2]["name"], "SPACE")
        self.assertEqual("".join(chr(int(r["code_point"][2:], 16)) for r in rows), text)
        self.assertTrue(all(r["marker"] for c, r in zip(text, rows) if c.isspace()))
        self.assertIn("⟦CR⟧⟦LF⟧⟦LF⟧", server.visible_text(text))
        self.assertTrue(server.visible_text(text).endswith("⟦SPACE⟧⟦SPACE⟧⟦LF⟧"))

    def test_controls_and_default_ignorables_have_markers(self):
        text = "\x00\x7f\x80\x85\u00a0\u200b\ufeff\u00ad\u202e\u2069\u034f\ufe0f\U000e0100\u2800"
        self.assertTrue(all(r["marker"] for r in server.character_inventory(text)))
        self.assertEqual(server.character_info("\t")["name"], "CHARACTER TABULATION")
        self.assertEqual(server.character_info("\r")["name"], "CARRIAGE RETURN")
        self.assertEqual(server.character_info("\x9b")["name"], "CONTROL SEQUENCE INTRODUCER")
        self.assertEqual(server.character_info("\u0cbf")["marker"], "")

    def test_joiners_are_exposed_without_disease_assignment(self):
        result = server.inspect_text("ಕ್\u200dಕ ಕ್\u200cಕ")
        self.assertEqual(server.character_info("\u200d")["marker"], "ZWJ")
        self.assertEqual(server.character_info("\u200c")["marker"], "ZWNJ")
        self.assertNotIn("diseases", result)
        self.assertFalse(result["nfc"]["changed"])

    def test_astral_character_offsets(self):
        result = server.inspect_text("😀ಕ\nಮ")
        self.assertEqual(result["length"], 4)
        self.assertEqual(result["characters"][0]["code_point"], "U+1F600")
        self.assertEqual(result["characters"][3]["name"], "KANNADA LETTER MA")
        self.assertEqual(result["characters"][3]["offset"], 3)

    def test_inventory_representation_and_category(self):
        text = "😀\n\t ಕಿ  "
        rows = server.character_inventory(text)
        self.assertEqual([row["representation"] for row in rows], [repr(ch) for ch in text])
        self.assertEqual(rows[1]["category"], "Cc")
        self.assertEqual(rows[-1]["category"], "Zs")

    def test_long_inventory_is_complete(self):
        result = server.inspect_text(SAMPLES[3])
        self.assertGreater(result["length"], 40000)
        self.assertEqual(result["characters"][-1]["offset"], len(SAMPLES[3]) - 1)
        self.assertEqual(result["characters"][-1]["name"], "LINE FEED")

    def test_empty_document(self):
        result = server.inspect_text("")
        self.assertEqual(result["characters"], [])
        self.assertFalse(result["nfc"]["changed"])


class UpdatedPackViewerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("reference_view_pack", Path(server.REPO) / "diagnosis/tools/view_pack_2.py")
        cls.reference = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.reference)

    def test_devanagari_g1_matches_reference_and_kannada_is_supported(self):
        text = "😀ि क ि कs् क्\u200dष क्\u200cष किं कಿ ಕs್ ಕ್\u200dಕ ಕ್\u200cಕ ಕಿ"
        result = server.inspect_text(text)
        matches = result["audit"]["g1_candidates"]
        reference_offsets = [offset for offset, _, _ in self.reference.g1_candidates(text)]
        devanagari_offsets = [m["start"] for m in matches if "Devanagari" in m["detail"]]
        self.assertEqual(devanagari_offsets, reference_offsets)
        self.assertTrue(any("Kannada" in m["detail"] for m in matches))
        finding = next(f for f in result["findings"] if f["code"] == "G1")
        self.assertTrue(all(any(word["start"] <= mark["start"] < word["end"]
                                for word in finding["matches"]) for mark in matches))
        for good in ["ಕಿ", "ಕಿಂ", "किं", "ಕ್\u200dಕ", "ಕ್\u200cಕ", "क्\u200dष", "क्\u200cष"]:
            self.assertEqual(server.inspect_text(good)["audit"]["g1_candidates"], [], good)

    def test_hidden_counts_complete_and_joiners_only_diagnostics(self):
        text = "😀\n " + "ಕ" * 2501 + "\u200d\u200d\u200c\t\u00a0\u2028\x07\ufffd"
        result = server.inspect_text(text)
        hidden = {r["code_point"]: r for r in result["audit"]["hidden_characters"]}
        for offset, ch in self.reference.hidden_characters(text):
            self.assertEqual(hidden[f"U+{ord(ch):04X}"]["offset"], text.index(ch))
        self.assertEqual(hidden["U+200D"]["count"], 2)
        self.assertEqual(hidden["U+200D"]["offset"], 2504)
        self.assertEqual(hidden["U+0007"]["name"], "BELL")
        self.assertNotIn("U+000A", hidden)
        self.assertNotIn("U+0020", hidden)
        joiners = server.inspect_text("ಕ್\u200dಕ ಕ್\u200cಕ")
        self.assertEqual(joiners["findings"], [])

    def test_mixed_digits_use_original_offsets_without_g4_assignment(self):
        text = "😀 ೧0೭ १0७ ೦೧೨ 012 १२३ 1 ೨ ೧२"
        result = server.inspect_text(text)
        mixed = result["audit"]["mixed_digits"]
        self.assertEqual([(m["start"], m["end"]) for m in mixed], [(2, 5), (6, 9), (26, 28)])
        self.assertEqual([m["scripts"] for m in mixed], [["ASCII", "Kannada"], ["ASCII", "Devanagari"], ["Devanagari", "Kannada"]])
        self.assertNotIn("G4", {f["code"] for f in result["findings"]})
        self.assertEqual(result["nfc"]["text"], text)
        self.assertEqual(result["nfkc"]["text"], text)

    def test_kannada_nfc_detects_composition_even_with_zero_combining_class(self):
        result = server.inspect_text("😀 \u0c95\u0cc6\u0cc2 \u0c95\u0cc6\u0cc2\u0cd5")
        self.assertTrue(result["nfc"]["changed"])
        self.assertEqual(result["nfc"]["text"], "😀 ಕೊ ಕೋ")

    def test_pack_metadata_optional_and_invalid_text_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            pack = Path(directory) / "fixture.parquet"
            for rows in [[{"doc_id": "one", "text": "ಕನ್ನಡ"}],
                         [{"doc_id": "one", "text": "ಕನ್ನಡ", "source": "synthetic", "lang_label": "kn"}]]:
                pq.write_table(pa.Table.from_pylist(rows), pack)
                self.assertEqual(server.load_pack(pack), rows)
            for rows in [[{"doc_id": "one", "text": None}], [{"doc_id": "one", "text": 123}], [{"doc_id": "one"}]]:
                pq.write_table(pa.Table.from_pylist(rows), pack)
                with self.assertRaises(ValueError):
                    server.load_pack(pack)

class NormalizationTests(unittest.TestCase):
    def assert_comparison(self, before, after):
        result = server.normalization_comparison(before, after)
        rebuilt, previous = [], 0
        for change in result["changes"]:
            a, b = change["start"], change["end"]
            c, d = change["normalized_start"], change["normalized_end"]
            self.assertEqual(before[a:b], change["before"])
            self.assertEqual(after[c:d], change["after"])
            rebuilt.extend([before[previous:a], change["after"]])
            previous = b
        rebuilt.append(before[previous:])
        self.assertEqual("".join(rebuilt), after)
        return result

    def test_kannada_o_and_oo(self):
        for before, after in [("\u0c95\u0cc6\u0cc2", "\u0c95\u0cca"),
                              ("\u0c95\u0cc6\u0cc2\u0cd5", "\u0c95\u0ccb")]:
            result = server.inspect_text(before)
            self.assertEqual(result["nfc"]["text"], after)
            self.assertTrue(result["nfc"]["changed"])
            self.assertFalse(result["compatibility"]["changed"])
            self.assert_comparison(before, after)

    def test_kannada_digits_stay_unchanged(self):
        text = "೦೧೨೩೪೫೬೭೮೯"
        result = server.inspect_text(text)
        for key in ["nfc", "nfkc", "compatibility"]:
            self.assertEqual(result[key]["text"], text)
            self.assertFalse(result[key]["changed"])

    def test_compatibility_changes_separate_from_nfc(self):
        text = "😀 \u0c95\u0cc6\u0cc2 ① １"
        result = server.inspect_text(text)
        self.assertEqual(result["nfc"]["text"], "😀 ಕೊ ① １")
        self.assertEqual(result["nfkc"]["text"], "😀 ಕೊ 1 1")
        self.assertEqual(result["nfc"]["changes"][0]["start"], 3)
        self.assertTrue(result["compatibility"]["changed"])
        for key, baseline in [("nfc", text), ("nfkc", text),
                              ("compatibility", result["nfc"]["text"])]:
            self.assert_comparison(baseline, result[key]["text"])

    def test_insertions_deletions_and_multiple_ranges(self):
        for before, after in [("", "a"), ("a", ""), ("abc def ghi", "axc def gzi"),
                              ("ಕ" * 2000 + "①" + "ಮ" * 2000, "ಕ" * 2000 + "1" + "ಮ" * 2000)]:
            self.assert_comparison(before, after)


class CandidateTests(unittest.TestCase):
    def findings(self, text, **kwargs):
        return {f["code"]: f for f in server.inspect_text(text, **kwargs)["findings"]}

    def test_coverage_matches_disease_specification(self):
        codes = server.disease_codes(Path(server.REPO) / "diagnosis" / "DISEASES.md")
        self.assertEqual(set(CHECKS) | set(MANUAL_CHECKS), set(codes))
        self.assertFalse(set(CHECKS) & set(MANUAL_CHECKS))

    def test_character_rules_and_exact_offsets_after_emoji(self):
        text = "😀\u200b\ufeff\u00ad\u202e\u2069\x00\r\x7f\x9f\ufffd\ufffd"
        found = self.findings(text)
        self.assertEqual(found["A1"]["count"], 5)
        self.assertEqual([m["start"] for m in found["A1"]["matches"]], [1, 2, 3, 4, 5])
        self.assertEqual(found["A2"]["count"], 4)
        self.assertEqual(found["A4"]["count"], 2)
        self.assertEqual(found["A4"]["matches"][-1]["start"], len(text) - 1)

    def test_joiners_tabs_and_lf_are_not_character_diseases(self):
        found = self.findings("ಕನ್ನಡ ಕ್\u200dಕ ಕ್\u200cಕ\t\n")
        self.assertNotIn("A1", found)
        self.assertNotIn("A2", found)
        self.assertNotIn("G1", found)
        self.assertNotIn("G2", found)

    def test_mojibake_is_a_cautious_hint(self):
        found = self.findings("Ã¤ â€™ à²•")
        self.assertEqual(found["A3"]["count"], 3)
        self.assertEqual(found["A3"]["kind"], "heuristic")
        self.assertNotIn("A3", self.findings("ಶುದ್ಧ ಕನ್ನಡ ಪಠ್ಯ"))

    def test_nfc_changes_are_candidates_not_g4(self):
        found = self.findings("😀 \u0c95\u0cc6\u0cc2 123 ①")
        self.assertEqual(found["A5"]["kind"], "normalization")
        self.assertEqual(found["A5"]["matches"][0]["start"], 3)
        self.assertNotIn("G4", found)
        self.assertNotIn("A5", self.findings("ಕೊ ೦೧೨೩೪೫೬೭೮೯"))

    def test_markup_templates_and_ghost_tokens(self):
        text = '<div>&amp; &#x0C95;</div> {{ variable }} ${item}\n<|im_start|>[INST]<s><think>\n### Assistant:'
        found = self.findings(text)
        self.assertEqual(found["B1"]["count"], 2)
        self.assertEqual(found["B2"]["count"], 2)
        self.assertEqual(found["B3"]["count"], 5)
        self.assertEqual(found["B4"]["count"], 2)
        for match in found["B2"]["matches"]:
            self.assertIn(text[match["start"]:match["end"]], ["<div>", "</div>"])
        ordinary = self.findings("x < y and y > z; undefined and NaN are terms.")
        self.assertNotIn("B2", ordinary)
        self.assertNotIn("B4", ordinary)

    def test_repeated_line_content_and_original_offsets(self):
        found = self.findings("😀\nrepeat\nrepeat\nrepeat\n\n\n\n")
        self.assertEqual(found["C2"]["count"], 3)
        self.assertEqual([m["start"] for m in found["C2"]["matches"]], [2, 9, 16])
        self.assertEqual(self.findings("repeat\nrepeat\n")["C2"]["count"], 2)
        text = "😀\r\n  ಮರುಕಳಿಸಿದ ಸಾಲು  \r\n\tಮರುಕಳಿಸಿದ ಸಾಲು\t\r\n"
        matches = self.findings(text)["C2"]["matches"]
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0]["start"], 5)
        self.assertEqual(matches[1]["start"], text.index("ಮರುಕಳಿಸಿದ ಸಾಲು", 6))
        self.assertEqual([text[m["start"]:m["end"]] for m in matches], ["ಮರುಕಳಿಸಿದ ಸಾಲು"] * 2)
        for text in ["repeat\n", "\n\n\n\n", "  \n\t\n", "ಕನ್ನಡ ಪದ\nಕನ್ನಡ  ಪದ\n",
                     "ಒನ್\u200cಪ್ಲಸ್\nಒನ್ಪ್ಲಸ್\n"]:
            self.assertNotIn("C2", self.findings(text))

    def test_c2_social_attribution_groups_optional_different_dates(self):
        attribution = "— Parveen Kaswan (@ParveenKaswan)"
        lines = [attribution, attribution + " July 19, 2021", attribution + " July 20, 2021"]
        text = ("😀\r\n" + lines[0] + "\r\nಮೊದಲ ಲೇಖನದ ವಿಷಯ.\r\n" + lines[1]
                + "\r\nಎರಡನೆಯ ಲೇಖನದ ವಿಷಯ.\r\n" + lines[2])
        matches = self.findings(text)["C2"]["matches"]
        self.assertEqual(len(matches), 3)
        self.assertEqual(matches[0]["start"], 3)
        self.assertEqual([text[m["start"]:m["end"]] for m in matches], lines)
        self.assertTrue(all("optional trailing dates ignored" in m["detail"] for m in matches))
        self.assertNotIn("Parveen", json.dumps(matches))
        # The two dated source lines in 205edeba4371d2c0 start at these offsets.
        first, second = lines[1:]
        text = "😀\n" + " " * (1049 - 2) + first + "\n" + "x" * (1749 - 1049 - len(first) - 2) + "\n" + second
        matches = self.findings(text)["C2"]["matches"]
        self.assertEqual([m["start"] for m in matches], [1049, 1749])
        self.assertEqual([text[m["start"]:m["end"]] for m in matches], [first, second])
        self.assertNotIn("C2", self.findings(first))
        for other in [second.replace("@ParveenKaswan", "@AnotherHandle"),
                      second.replace("Parveen Kaswan", "Another Author"),
                      second + " is part of a narrative sentence."]:
            self.assertNotIn("C2", self.findings(first + "\n" + other))

    def test_c2_passage_repeats_inside_a_paragraph_at_reported_offsets(self):
        # 0f52e8c63e977510: the second occurrence starts within a longer line.
        passage = ("ಎಲ್ಲ ಶೋಷಣೆಗಳೂ ಸುಳ್ಳುಗಳೂ ಅಗತ್ಯಸೇವೆಯೇ ಆಗುತ್ತಿರುವಾಗ, ‘ಅಗತ್ಯ’ಗಳು ಹೀಗಿರುವಾಗ "
                   "ಎಲ್ಲ ಹಿಂಸೆಗಳನ್ನೂ ತಾಳಿಕೊಳ್ಳುವುದೇ ಪ್ರಜೆಗಳ ಹಣೆಬರಹವಾಗುವುದು ಮತ್ತು ಕೋವಿಡ್-19ಕ್ಕಿಂತಲೂ "
                   "ಹೆಚ್ಚು ಅಪಾಯವನ್ನು ತಂದೊಡ್ಡಬಲ್ಲ ಈ ನಿವಾರಣೋಪಾಯಗಳನ್ನು ಸಹಿಸುವ ಶಕ್ತಿಕೊಡು ತಂದೆ ಎಂದು "
                   "ಪ್ರಾರ್ಥಿಸುವುದು ಅನಿವಾರ್ಯ.")
        prefix = "ಬಡ ಪ್ರಜೆಗಳ ಬೇಸರಿನ ಬೇಗೆ\n"
        text = prefix + passage + " ಬೇರೆ ವಿಷಯ.\n"
        text += "x" * (7915 - len(text) - len(" ಮತ್ತೊಂದು ವಾಕ್ಯ. ")) + " ಮತ್ತೊಂದು ವಾಕ್ಯ. " + passage
        matches = self.findings(text)["C2"]["matches"]
        self.assertEqual([m["start"] for m in matches], [23, 7915])
        self.assertEqual([text[m["start"]:m["end"]] for m in matches], [passage, passage])
        self.assertNotIn("ಎಲ್ಲ ಶೋಷಣೆಗಳೂ", json.dumps(matches, ensure_ascii=False))

    def test_c2_inline_passages_keep_offsets_joiners_and_avoid_nested_matches(self):
        passage = "A substantial repeated sentence has enough words to be useful."
        text = "😀 " + passage + "\nDifferent text. " + passage
        matches = self.findings(text)["C2"]["matches"]
        self.assertEqual([m["start"] for m in matches], [2, text.rfind(passage)])
        self.assertEqual(len(matches), 2)
        # Existing full-line matches must not also become passage findings.
        self.assertEqual(self.findings(passage + "\n" + passage)["C2"]["count"], 2)
        altered = passage.replace("repeated", "re\u200cpeated")
        self.assertNotIn("C2", self.findings(passage + "\nDifferent text. " + altered))
        self.assertNotIn("C2", self.findings("short phrase\nAn inline short phrase"))

    def test_reported_c2_repeated_intro_at_document_end(self):
        # c69e1a6483bd6ac2 repeats this complete line, not just the headline.
        line = "ಚಿಕ್ಕಮಗಳೂರು : ಆತ್ಮೋದ್ಧಾರಕ್ಕೆ ಸೇವೆ ಸಹಕಾರಿ ಎಂದು ಶ್ರೀಸತ್ಯಸಾಯಿ ಸೇವಾಸಂಸ್ಥೆಗಳ ಕರ್ನಾಟಕ ಉತ್ತರಘಟಕದ ಅಧ್ಯಕ್ಷ ಮಂಗಳೂರಿನ ಪದ್ಮನಾಭಪೈ ನುಡಿದರು."
        text = line + "\n" + "x" * (3385 - len(line) - 2) + "\n" + line
        matches = self.findings(text)["C2"]["matches"]
        self.assertEqual([m["start"] for m in matches], [0, 3385])
        self.assertEqual([text[m["start"]:m["end"]] for m in matches], [line, line])

    def test_c1_navigation_candidates_use_original_offsets_without_snippets(self):
        found = self.findings(SAMPLES[5])
        self.assertEqual(found["C1"]["count"], 1)
        self.assertEqual(found["C5"]["count"], 2)
        self.assertEqual(found["C5"]["matches"][0]["start"], 20)
        self.assertNotIn("573", json.dumps(found, ensure_ascii=False))
        self.assertNotIn("C1", self.findings("English article body\nಕನ್ನಡ ಪಠ್ಯ"))
        self.assertIn("C5", self.findings("- News ಸುದ್ದಿ\nಕನ್ನಡ ಲೇಖನ"))

    def test_dont_miss_alone_is_c1_and_following_teasers_are_c5(self):
        text = "Don't Miss!\n- News ಸರ್ಕಾರದಿಂದ 84 ಸಾವಿರ ರೆಮಿಡಿಸ್ವಿರ್ ಖರೀದಿ: ಸುಧಾಕರ್\n- Sports ಐಪಿಎಲ್ 2021: ಪಂಜಾಬ್ vs ಚೆನ್ನೈ\nಲೇಖನ\n"
        found = self.findings(text)
        self.assertEqual(found["C1"]["matches"], [{"start": 0, "end": 11, "detail": "navigation header"}])
        self.assertEqual(found["C5"]["count"], 2)
        self.assertEqual(found["C5"]["matches"][0]["start"], 12)

    def test_c5_hashtag_lists_with_and_without_spaces(self):
        tags = ["BJP4Belagavi", "BJP4Maski", "BJP4Basavakalyana"]
        for prefix, separator in [("#", " "), ("# ", " "), ("#", ""), ("# ", ""), ("#", ", ")]:
            spellings = [prefix + tag for tag in tags]
            text = "😀\r\n" + separator.join(spellings) + "\r\nಲೇಖನ\n"
            matches = self.findings(text)["C5"]["matches"]
            self.assertEqual([text[m["start"]:m["end"]] for m in matches], spellings)
            self.assertEqual(matches[0]["start"], 3)
            self.assertNotIn("BJP", json.dumps(matches))
        text = "😀 #ಕನ್ನಡ # ಕರ್ನಾಟಕ2026"
        matches = self.findings(text)["C5"]["matches"]
        self.assertEqual([text[m["start"]:m["end"]] for m in matches], ["#ಕನ್ನಡ", "# ಕರ್ನಾಟಕ2026"])
        self.assertEqual(self.findings("- News #one #two\n")["C5"]["count"], 1)
        for text in ["# Heading", "## Heading", "#single", "#123 #456", "&#123; &#456;",
                     "C#code C#example", "https://example.invalid/#one#two"]:
            self.assertNotIn("C5", self.findings(text), text)

    def test_c1_publication_timestamp_candidates(self):
        found = self.findings(SAMPLES[9])
        self.assertEqual(found["C1"]["count"], 2)
        self.assertEqual(found["C1"]["matches"][0]["start"], 0)
        self.assertEqual(found["C1"]["matches"][1]["start"], len(SAMPLES[9].splitlines(keepends=True)[0]))
        self.assertTrue(all(m["detail"] == "publication or update timestamp" for m in found["C1"]["matches"]))

    def test_c1_updated_weekday_timestamp_with_bracketed_timezone(self):
        line = "Updated: Thursday, June 10, 2021, 20:15 [IST]"
        matches = self.findings("😀\n" + line + "\nಲೇಖನ\n")["C1"]["matches"]
        self.assertEqual(matches, [{"start": 2, "end": 2 + len(line),
                                    "detail": "publication or update timestamp"}])

    def test_c1_social_follow_prompt(self):
        line = "Please follow and like us:"
        matches = self.findings("😀\n" + line + "\nಲೇಖನ\n")["C1"]["matches"]
        self.assertEqual(matches, [{"start": 2, "end": 2 + len(line),
                                    "detail": "social-follow prompt"}])

    def test_c1_standalone_kannada_timestamp_without_publication_marker(self):
        line = "ಬುಧವಾರ, 7 ಏಪ್ರಿಲ್ 2021 (11:15 IST)"
        text = "😀\n" + line + "\r\nಲೇಖನದ ವಿಷಯ.\r\n"
        matches = self.findings(text)["C1"]["matches"]
        self.assertEqual(matches, [{"start": 2, "end": 2 + len(line),
                                    "detail": "publication or update timestamp"}])
        for prose in ["IST", "ಸಭೆಯ ಸಮಯ IST ಪ್ರಕಾರ ನೀಡಲಾಗಿದೆ.",
                      line + " ರಂದು ಸಭೆ ನಡೆಯಿತು.", "ಸಭೆ " + line]:
            self.assertNotIn("C1", self.findings(prose), prose)

    def test_c1_homepage_and_first_published_candidates(self):
        found = self.findings(SAMPLES[10])["C1"]
        self.assertEqual(found["count"], 2)
        self.assertEqual(found["matches"][0]["detail"], "homepage navigation label")
        self.assertEqual(found["matches"][1]["detail"], "publication or update timestamp")
        self.assertEqual(found["matches"][1]["start"], len("ಮುಖಪುಟ\n"))

    def test_c1_city_pipe_and_slogan_candidates(self):
        found = self.findings(SAMPLES[11])["C1"]
        self.assertEqual(found["count"], 6)
        self.assertEqual(found["matches"][-1]["detail"], "traffic-safety slogan")
        self.assertTrue(all(m["detail"] == "pipe-terminated city/navigation label" for m in found["matches"][:-1]))
        related = "ಇದನ್ನೂ ಓದಿ | ಕ್ರಾಂತಿಕಾರಿ ರೈತ ಹೋರಾಟದ ಸ್ಫೂರ್ತಿಯ ಚಿಲುಮೆ `ಅಜಿತ್ ಸಿಂಗ್‘\n"
        self.assertNotIn("C1", self.findings(related))
        self.assertNotIn("C1", self.findings("ಬೆಂಗಳೂರು|"))

    def test_detached_kannada_marks_need_context(self):
        found = self.findings("\u0cbf ಕ \u0ccd")
        self.assertEqual(found["G1"]["count"], 2)
        self.assertEqual(found["G1"]["kind"], "heuristic")
        self.assertNotIn("G1", self.findings("ಕನ್ನಡ ಕಿ"))

    def test_reader_g1_examples_use_whole_words_and_original_offsets(self):
        for word, offset in [("ಕಾರಂ ತ", 29), ("ವಣ ್ಸುವಾಗ", 13962),
                             ("ಕರ್ನಾ ಟಕದ", 1445), ("ಸ ರ್ಧೆ", 1112), ("ಕೋಣೆ ಗಳ", 137)]:
            text = "😀" + " " * (offset - 1) + word
            matches = self.findings(text)["G1"]["matches"]
            self.assertIn((offset, offset + len(word)), [(m["start"], m["end"]) for m in matches])
            self.assertEqual(text[offset:offset + len(word)], word)
        self.assertNotIn("G1", self.findings("ಕನ್ನಡ ಭಾಷೆ ಸಾಮಾನ್ಯ ಪದಗಳು"))

    def test_g2_uses_reader_forms_not_arbitrary_conjuncts(self):
        for word, offset in [("ಹಾಲ್ನಲ್ಲಿ", 193), ("ಡೌನ್ಲೋಡ್", 158),
                             ("ಲವ್ಸ್ಟೋರಿ", 342), ("ಡಿಸ್ಪ್ಲೇ", 833), ("ಫೋಟೋಶೂಟ್ನಲ್ಲಿ", 727)]:
            text = "😀" + " " * (offset - 1) + word
            finding = self.findings(text)["G2"]
            self.assertEqual([(m["start"], m["end"]) for m in finding["matches"]],
                             [(offset, offset + len(word))])
            self.assertEqual(finding["kind"], "heuristic")
        for text in ["ಕನ್ನಡ", "ರ್ಕ", "ಡೌನ್\u200cಲೋಡ್", "ಲವ್\u200cಸ್ಟೋರಿ", "ರ\u200d್ಕ", "ರ್\u200dಕ"]:
            self.assertNotIn("G2", self.findings(text))

    def test_a6_reader_identified_avagraha_word(self):
        for word in ["ಅಽಕಾರಿ", "ಅಽಕಾರಿಗಳು"]:
            text = "😀 " + word + "."
            matches = self.findings(text)["A6"]["matches"]
            self.assertEqual(len(matches), 1)
            self.assertEqual((matches[0]["start"], matches[0]["end"]), (2, 2 + len(word)))
            self.assertEqual(text[matches[0]["start"]:matches[0]["end"]], word)
            self.assertNotIn("A1", self.findings(text))
        for text in ["ಅಧಿಕಾರಿ", "ಽ", "ಸೋಽಹಂ"]:
            self.assertNotIn("A6", self.findings(text), text)

    def test_a6_latin_before_dependent_sign(self):
        text = " " * 523 + "process ಾಯಾಚಿತ್ರದೊಂದಿಗೆ"
        match = self.findings(text)["A6"]["matches"][0]
        self.assertEqual(match["start"], 523)
        self.assertEqual(text[match["start"]:match["end"]], "process ಾಯಾಚಿತ್ರದೊಂದಿಗೆ")
        self.assertNotIn("A6", self.findings("process ಚಿತ್ರ ಕನ್ನಡ ಭಾಷೆ"))
        self.assertIn("A6", self.findings("ಕs್"))

    def test_joiner_order_is_preserved_in_inventory_and_normalization(self):
        sequences = ["ಒನ್\u200cಪ್ಲಸ್", "ರ\u200d್ಕ", "ರ್\u200dಕ"]
        for text in sequences:
            inspection = server.inspect_text(text)
            self.assertEqual([row["code_point"] for row in inspection["characters"]],
                             [f"U+{ord(ch):04X}" for ch in text])
            self.assertEqual(inspection["nfc"]["text"], text)
            self.assertEqual(inspection["nfkc"]["text"], text)

    def test_broader_ghost_markers_and_broken_structures(self):
        for text in ["<<SYS>>", "<thinking>", "[MASK]", "<start_of_turn>", "Human: hello"]:
            self.assertIn("B3", self.findings(text))
        for text in ["```python\nprint(1)\n", "\\frac{1", "\\begin{align}x", "$$x"]:
            self.assertIn("B5", self.findings(text))
        for text in ["```\nprint(1)\n```", "\\frac{1}{2}", "\\begin{align}x\\end{align}", "$$x$$"]:
            self.assertNotIn("B5", self.findings(text))

    def test_f1_contiguous_phone_candidate_accepts_leading_zero(self):
        number = "0022330000"
        matches = self.findings("😀 " + number + ".")["F1"]["matches"]
        self.assertEqual(matches, [{"start": 2, "end": 12,
                                    "detail": "phone-number-like digit sequence"}])
        self.assertNotIn(number, json.dumps(matches))
        for number in ["1234567890", "9000000000", "+91 9000000000", "+919000000000"]:
            self.assertEqual(self.findings(number)["F1"]["count"], 1, number)
        for text in ["002233000", "00223300000", "2021", "reference0022330000"]:
            self.assertNotIn("F1", self.findings(text), text)

    def test_sensitive_findings_never_contain_matched_values(self):
        email = "synthetic-reviewer" + "@" + "example.invalid"
        secret = "synthetic-" + "placeholder-value"
        phone = "9" + "0" * 9
        text = "😀 {{ " + email + " }}\npassword = '" + secret + "'\n" + phone + "\n-----BEGIN PRIVATE KEY-----"
        found = self.findings(text)
        self.assertEqual(found["F1"]["count"], 2)
        self.assertEqual(found["E3"]["count"], 2)
        serialized = json.dumps(found, ensure_ascii=False)
        for value in [email, secret, phone]:
            self.assertNotIn(value, serialized)
        self.assertEqual(set(found["F1"]["matches"][0]), {"start", "end", "detail"})
        self.assertIn("leave hex empty", found["F1"]["caution"])
        for text in ["123", "9" * 9, "9" * 11, "reference" + phone, "password = short"]:
            checked = self.findings(text)
            self.assertNotIn("F1", checked)
            self.assertNotIn("E3", checked)

    def test_raw_exact_duplicates_and_no_normalized_match(self):
        docs = [{"text": s} for s in ["same", "same ", "same", "\u0c95\u0cc6\u0cc2", "ಕೊ"]]
        groups = server.exact_duplicate_groups(docs)
        self.assertEqual(groups, {0: (0, 2), 2: (0, 2)})
        related = [{"i": 2, "doc_id": "synthetic-duplicate"}]
        found = self.findings("same", duplicate_documents=related)
        self.assertEqual(found["H1"]["related_documents"], related)
        self.assertEqual(found["H1"]["kind"], "exact")
        self.assertNotIn("H1", self.findings("same", duplicate_documents=[]))

    def test_manual_guidance_and_no_false_clean_claim(self):
        result = server.inspect_text("ಕನ್ನಡ ಪಠ್ಯ", duplicate_documents=[])
        self.assertEqual(result["findings"], [])
        self.assertEqual(set(result["checked_codes"]), set(CHECKS))
        self.assertEqual({m["code"] for m in result["manual_checks"]}, set(MANUAL_CHECKS))
        self.assertNotIn("verdict", result)
        self.assertNotIn("diseases", result)
        self.assertIn("H1", {m["code"] for m in server.inspect_text("text")["manual_checks"]})


class EndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="kannada-viewer-test-")
        cls.addClassCleanup(cls.temp.cleanup)
        root = Path(cls.temp.name)
        pack = write_demo(root)
        labels = root / "labels.csv"
        with labels.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=server.COLS)
            writer.writeheader()
            writer.writerow({"doc_id": "synthetic-1", "read": "full", "verdict": "fix",
                             "diseases": "A5", "evidence": "synthetic starting evidence"})
        cls.reviews = root / "reviews.json"
        cls.process = subprocess.Popen(
            [sys.executable, str(HERE / "review_server.py"), "--pack", str(pack),
             "--labels", str(labels), "--reviews", str(cls.reviews), "--port", "0", "--row", "2", "--audit"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        cls.addClassCleanup(cls.stop_server)
        lines = queue.Queue()

        def read_output():
            for line in cls.process.stdout:
                lines.put(line.strip())

        threading.Thread(target=read_output, daemon=True).start()
        for _ in range(4):
            try:
                line = lines.get(timeout=15)
            except queue.Empty:
                raise RuntimeError("Synthetic test server did not start within 15 seconds")
            if line.startswith("open http://"):
                cls.base = line.removeprefix("open ").rstrip("/")
                return
        raise RuntimeError("Missing synthetic test server address")

    @classmethod
    def stop_server(cls):
        cls.process.terminate()
        try:
            cls.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.process.kill()
            cls.process.wait(timeout=5)
        cls.process.stdout.close()
        cls.process.stderr.close()

    def get(self, path):
        with urlopen(self.base + path, timeout=15) as response:
            return response.read()

    def test_lazy_inspection_and_unchanged_source(self):
        data = json.loads(self.get("/data.json"))
        self.assertEqual(len(data["pack_key"]), 64)
        self.assertNotIn("characters", data["docs"][0])
        self.assertEqual(data["docs"][0]["text"], SAMPLES[0])
        self.assertEqual(data["docs"][0]["source"], "synthetic")
        self.assertEqual(data["docs"][0]["lang_label"], "kn")
        self.assertEqual(data["initial_index"], 1)
        self.assertTrue(data["audit_open"])
        result = json.loads(self.get("/inspect?i=3"))
        self.assertEqual(result["doc_id"], "synthetic-3")
        self.assertEqual(len(result["characters"]), len(SAMPLES[3]))
        self.assertEqual(json.loads(self.get("/data.json")), data)
        first = json.loads(self.get("/inspect?i=0"))
        duplicate = next(f for f in first["findings"] if f["code"] == "H1")
        self.assertEqual(duplicate["related_documents"], [{"i": 4, "doc_id": "synthetic-4"}])
        self.assertIn("H1", first["checked_codes"])

    def test_invalid_inspection_indices(self):
        for query, status in [("", 400), ("?i=-1", 400), ("?i=abc", 400),
                              ("?i=0&i=1", 400), (f"?i={len(SAMPLES)}", 404)]:
            with self.subTest(query=query), self.assertRaises(HTTPError) as error:
                self.get("/inspect" + query)
            self.assertEqual(error.exception.code, status)
            error.exception.close()

    def test_varthabharati_candidate_uses_document_url(self):
        result = json.loads(self.get("/inspect?i=12"))
        c1 = next(f for f in result["findings"] if f["code"] == "C1")
        start = len(SAMPLES[12]) - len(FOOTER)
        self.assertEqual(c1["matches"], [{"start": start, "end": len(SAMPLES[12]),
                                         "detail": "Vartha Bharati donation/support footer"}])
        original = json.loads(self.get("/data.json"))["docs"][12]
        self.assertEqual(original["text"], SAMPLES[12])
        self.assertEqual(original["url"], SAMPLE_URLS[12])

    def test_news18_candidate_uses_document_url_and_no_duplicate_timestamp(self):
        result = json.loads(self.get("/inspect?i=13"))
        c1 = next(f for f in result["findings"] if f["code"] == "C1")
        self.assertEqual(c1["count"], 3)
        self.assertEqual([SAMPLES[13][m["start"]:m["end"]] for m in c1["matches"]],
                         ["news18-kannada Updated:", "February 14, 2021, 6:22 PM IST", "India"])

    def test_invalid_starting_rows_fail_before_serving(self):
        with tempfile.TemporaryDirectory() as directory:
            pack = write_demo(Path(directory))
            for option, value in [("--row", "0"), ("--row", str(len(SAMPLES) + 1)),
                                  ("--start", "-1"), ("--start", str(len(SAMPLES)))]:
                with self.subTest(option=option, value=value):
                    process = subprocess.run([sys.executable, str(HERE / "review_server.py"),
                                              "--pack", str(pack), option, value],
                                             capture_output=True, text=True, timeout=15)
                    self.assertEqual(process.returncode, 2, process.stdout + process.stderr)
                    self.assertIn("--row must be", process.stderr)

    def test_review_save_and_export_keep_schema_and_text(self):
        row = dict(zip(server.COLS, ["synthetic-0", "full", "fix", "A1", "offset 2", "U+200B", "synthetic note"]))
        request = Request(self.base + "/save", data=json.dumps(row).encode(),
                          headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=15) as response:
            self.assertEqual(json.load(response)["reviewed"], 1)
        self.assertEqual(json.loads(self.get("/reviews"))["synthetic-0"], row)
        self.assertEqual(json.loads(self.reviews.read_text())["synthetic-0"], row)
        reader = csv.DictReader(io.StringIO(self.get("/export.csv").decode()))
        self.assertEqual(reader.fieldnames, server.COLS)
        rows = list(reader)
        self.assertEqual(rows[0], row)
        self.assertEqual(rows[1]["doc_id"], "synthetic-1")
        self.assertEqual(json.loads(self.get("/data.json"))["docs"][0]["text"], SAMPLES[0])


class FrontendTests(unittest.TestCase):
    def run_frontend_script(self, name):
        fixture = [{"text": s, "inspection": {"i": i, **server.inspect_text(s, url=SAMPLE_URLS.get(i))}}
                   for i, s in enumerate(SAMPLES)]
        result = subprocess.run(["node", str(HERE / name)],
                                input=json.dumps(fixture), capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for frontend checks")
    def test_frontend_rendering(self):
        self.run_frontend_script("test_viewer.js")

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for frontend checks")
    def test_frontend_browser_drafts(self):
        self.run_frontend_script("test_drafts.js")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--make-demo":
        print(write_demo(Path(sys.argv[2])))
    else:
        unittest.main()
