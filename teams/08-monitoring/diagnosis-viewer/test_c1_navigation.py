"""Synthetic behavior tests for the executable C1 medicine and its documentation."""
from pathlib import Path
import re
import unittest

import c1_navigation as medicine


def load_medicine_snippets():
    path = Path(__file__).resolve().parents[3] / "diagnosis/submissions/ind-kn-fw2/LokeshJatangi/medicine.md"
    blocks = re.findall(r"^```python\n(.*?)^```", path.read_text(), re.M | re.S)
    if not blocks:
        raise AssertionError("medicine.md contains no executable Python snippets")
    namespace = {"__name__": "medicine_snippets"}
    exec(compile("\n\n".join(blocks), str(path), "exec"), namespace)
    return namespace


SAMPLE = (
    "Just In\nDon't Miss!\n"
    "- News ಕರ್ನಾಟಕದಲ್ಲಿ 573 ಕೊರೊನಾ ಸೋಂಕಿತರು ಪತ್ತೆ\n"
    "- Finance ಬಜೆಟ್ 2021: ಐ.ಟಿ. ಫೈಲಿಂಗ್ ನಲ್ಲಿ PAN ಕಾರ್ಡ್ ಗೆ ಏಕಿಷ್ಟು ಮಹತ್ವ\n"
    "- Sports ಐಪಿಎಲ್ 2021\n"
    "- Automobiles ಸ್ಕೋಡಾ\n"
    "- Lifestyle ವಾರ ಭವಿಷ್ಯ\n"
    "- Education NIT Recruitment 2021\n"
    "- Technology ಒನ್ಪ್ಲಸ್\n"
    "- Travel ರೈಲುಗಳ ಪಟ್ಟಿ\n"
)


class C1MedicineTests(unittest.TestCase):
    def test_sample_evidence_and_original_offsets(self):
        matches = medicine.find_c1_matches(SAMPLE)
        self.assertEqual(len(matches), 1)
        self.assertEqual((matches[0]["start"], matches[0]["end"]), (0, 19))
        teasers = medicine.find_c5_matches(SAMPLE)
        self.assertEqual(len(teasers), 8)
        self.assertEqual(teasers[0]["start"], 20)
        evidence = medicine.c1_evidence(SAMPLE, matches)
        self.assertIn('C1: "Just In Don\'t Miss!" at offset 0', evidence)
        self.assertNotIn("- News", evidence)

    def test_dont_miss_without_just_in_separates_header_and_teasers(self):
        text = SAMPLE.removeprefix("Just In\n")
        self.assertEqual(medicine.find_c1_matches(text), [
            {"start": 0, "end": 11, "detail": "navigation header"}])
        self.assertEqual(len(medicine.find_c5_matches(text)), 8)
        self.assertEqual(medicine.find_c5_matches(text)[0]["start"], 12)
        self.assertEqual(medicine.fix_c1_navigation(text + "ಲೇಖನ\n"), "ಲೇಖನ\n")
        self.assertEqual(medicine.find_c1_matches("Don't Miss!"), [
            {"start": 0, "end": 11, "detail": "navigation header"}])
        self.assertEqual(medicine.find_c5_matches("ಲೇಖನದ ಶೀರ್ಷಿಕೆ\n- News ಸುದ್ದಿ\n"), [])

    def test_repair_keeps_body_and_its_whitespace_exactly(self):
        body = "\nಕನ್ನಡ ಮೂಲ ಲೇಖನ. ಕ್\u200dಕ ಕ್\u200cಕ\nEnglish body text stays.  \n"
        self.assertEqual(medicine.fix_c1_navigation(SAMPLE + body), body)
        fixed = medicine.fix_c1_navigation(SAMPLE + body)
        self.assertEqual(medicine.fix_c1_navigation(fixed), fixed)

    def test_top_hyphen_space_english_letter_blocks(self):
        text = "\n- News ಸುದ್ದಿ\n- Culture ಮಾಹಿತಿ\nಕನ್ನಡ ಲೇಖನ\n- News part of body\n"
        matches = medicine.find_c5_matches(text)
        self.assertEqual([m["start"] for m in matches], [1, 1 + len("- News ಸುದ್ದಿ\n")])
        self.assertEqual(medicine.fix_c1_navigation(text), "\nಕನ್ನಡ ಲೇಖನ\n- News part of body\n")

    def test_nonmatching_body_and_other_lists_are_preserved(self):
        for text in ["English body text\nಕನ್ನಡ ಲೇಖನ\n", "ಶೀರ್ಷಿಕೆ\n- News ಸುದ್ದಿ\n",
                     "- ಕನ್ನಡ ಅಂಶ\n", "-News ಸುದ್ದಿ\n", "– News ಸುದ್ದಿ\n",
                     "Just In\n- News ಸುದ್ದಿ\n"]:
            with self.subTest(text=text):
                self.assertEqual(medicine.find_c1_matches(text), [])
                self.assertEqual(medicine.fix_c1_navigation(text), text)

    def test_trending_topics_age_suffix_and_separator(self):
        widget = "Trending\nರಾಜಕೀಯ7 days ago\n-\nರಾಜಕೀಯ6 days ago\n"
        text = widget + "ಕನ್ನಡ ಮೂಲ ಲೇಖನ\n"
        matches = medicine.find_c1_matches(text)
        self.assertEqual(len(matches), 4)
        self.assertEqual([text[m["start"]:m["end"]] for m in matches],
                         ["Trending", "ರಾಜಕೀಯ7 days ago", "-", "ರಾಜಕೀಯ6 days ago"])
        self.assertEqual(matches[1]["start"], len("Trending\n"))
        self.assertEqual(medicine.fix_c1_navigation(text), "ಕನ್ನಡ ಮೂಲ ಲೇಖನ\n")

    def test_all_reported_topics_with_attached_numeric_age(self):
        widget = (
            "Trending\n-\nಅಂತರಂಗ5 days ago \nದಿನದ ಸುದ್ದಿ5 days ago\n"
            "ಲೈಫ್ ಸ್ಟೈಲ್4 days ago\nಕ್ರೀಡೆ4 days ago\n ಭಾವ ಭೈರಾಗಿ5 days ago\n"
        )
        body = "ಮೂಲ ಲೇಖನದ ಶೀರ್ಷಿಕೆ\nಕನ್ನಡ ಲೇಖನದ ವಿಷಯ.\n"
        matches = medicine.find_c1_matches(widget + body)
        self.assertEqual(len(matches), 7)
        self.assertEqual([(widget + body)[m["start"]:m["end"]] for m in matches], [
            "Trending", "-", "ಅಂತರಂಗ5 days ago ", "ದಿನದ ಸುದ್ದಿ5 days ago",
            "ಲೈಫ್ ಸ್ಟೈಲ್4 days ago", "ಕ್ರೀಡೆ4 days ago", " ಭಾವ ಭೈರಾಗಿ5 days ago",
        ])
        self.assertEqual(matches[2]["start"], 11)
        evidence = medicine.c1_evidence(widget + body, matches)
        self.assertIn('C1: "ಅಂತರಂಗ5 days ago" at offset 11', evidence)
        self.assertIn('C1: "ಭಾವ ಭೈರಾಗಿ5 days ago" at offset ', evidence)
        self.assertEqual(medicine.fix_c1_navigation(widget + body), body)

    def test_age_markers_must_end_the_line_and_have_a_number(self):
        for text in ["ರಾಜಕೀಯ7 days ago ಇನ್ನಷ್ಟು\n", "ರಾಜಕೀಯ days ago\n", "Trending topics\n", "-\n"]:
            self.assertEqual(medicine.find_c1_matches(text), [])
        for text in ["ರಾಜಕೀಯ7 days ago\n", "ರಾಜಕೀಯ೭ days ago\n", "ರಾಜಕೀಯ1 day ago\n", "Trending\n"]:
            self.assertTrue(medicine.find_c1_matches(text))
        self.assertEqual(medicine.fix_c1_navigation("Trending\n-\nಲೇಖನ\n"), "-\nಲೇಖನ\n")

    def test_age_inside_a_navigation_bullet_is_not_double_counted(self):
        text = "- News ರಾಜಕೀಯ7 days ago\nಲೇಖನ\n"
        self.assertEqual(len(medicine.find_c5_matches(text)), 1)
        self.assertEqual(medicine.find_c1_matches(text), [])
        self.assertEqual(medicine.fix_c1_navigation(text), "ಲೇಖನ\n")

    def test_standalone_title_label(self):
        text = "Title\nಕನ್ನಡ ಲೇಖನದ ಶೀರ್ಷಿಕೆ\nಮೂಲ ಲೇಖನ\n"
        matches = medicine.find_c1_matches(text)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0], {"start": 0, "end": 5, "detail": "website title label"})
        self.assertEqual(medicine.fix_c1_navigation(text), "ಕನ್ನಡ ಲೇಖನದ ಶೀರ್ಷಿಕೆ\nಮೂಲ ಲೇಖನ\n")
        for body in ["Title of the article\n", "ಶೀರ್ಷಿಕೆ Title ಒಳಗಿದೆ\n"]:
            self.assertEqual(medicine.find_c1_matches(body), [])

    def test_reported_byline_and_kannada_update_timestamps(self):
        examples = [
            "Team Udayavani, Feb 11, 2021, 3:27 PM IST",
            "Last Modified ಶನಿವಾರ, 5 ಸೆಪ್ಟಂಬರ್ 2020 (10:08 IST)",
            "ಬುಧವಾರ, 7 ಏಪ್ರಿಲ್ 2021 (11:15 IST)",
            "7 ಏಪ್ರಿಲ್ 2021 (11:15 IST)",
        ]
        for line in examples:
            with self.subTest(line=line):
                text = "😀\n" + line + "\r\nಕನ್ನಡ ಲೇಖನದ ಶೀರ್ಷಿಕೆ\r\nಮೂಲ ಲೇಖನ\r\n"
                matches = medicine.find_c1_matches(text)
                self.assertEqual(matches, [{"start": 2, "end": 2 + len(line), "detail": "publication or update timestamp"}])
                self.assertEqual(text[matches[0]["start"]:matches[0]["end"]], line)
                self.assertIn('at offset 2', medicine.c1_evidence(text, matches))
                self.assertEqual(medicine.fix_c1_navigation(text), "😀\nಕನ್ನಡ ಲೇಖನದ ಶೀರ್ಷಿಕೆ\r\nಮೂಲ ಲೇಖನ\r\n")

    def test_first_published_exact_reported_timestamp(self):
        line = "First Published Jan 20, 2021, 2:58 PM IST"
        body = "ಕನ್ನಡ ಲೇಖನದ ಶೀರ್ಷಿಕೆ\nಮೂಲ ಲೇಖನ\n"
        text = line + "\n" + body
        matches = medicine.find_c1_matches(text)
        self.assertEqual(matches, [{"start": 0, "end": len(line), "detail": "publication or update timestamp"}])
        self.assertEqual(medicine.c1_evidence(text, matches), f'C1: "{line}" at offset 0')
        self.assertEqual(medicine.fix_c1_navigation(text), body)
        self.assertEqual(medicine.find_c1_matches("First Published Jan 20, 2021\n"), [])

    def test_updated_weekday_timestamp_with_bracketed_timezone(self):
        line = "Updated: Thursday, June 10, 2021, 20:15 [IST]"
        body = "ಕನ್ನಡ ಲೇಖನ. ಕ್\u200cಕ ಕ್\u200dಕ\r\n"
        text = "😀\r\n" + line + "\r\n" + body
        self.assertEqual(medicine.find_c1_matches(text), [
            {"start": 3, "end": 3 + len(line), "detail": "publication or update timestamp"}])
        self.assertEqual(medicine.fix_c1_navigation(text), "😀\r\n" + body)
        for variant in [line, line.replace("Updated: ", "Updated:"), line.replace("[IST]", "IST")]:
            self.assertEqual(len(medicine.find_c1_matches(variant)), 1, variant)
        for invalid in [line.replace("[IST]", "[IST"), line.replace("[IST]", "IST]"),
                        line.replace("20:15", "25:99"), line + " and the article continues."]:
            self.assertEqual(medicine.find_c1_matches(invalid), [], invalid)

    def test_timestamp_variants_and_plain_dates(self):
        for line in ["February 11, 2021, 15:27 IST", "Desk, Feb 11, 2021, 03:27 PM UTC",
                     "Last Updated: ಶನಿವಾರ, ೫ ಸೆಪ್ಟಂಬರ್ ೨೦೨೦ (10:08 IST)",
                     "Published 5 ಸೆಪ್ಟಂಬರ್ 2020 (10:08:30 +05:30)"]:
            self.assertTrue(medicine.find_c1_matches(line + "\n"), line)
        for line in ["Feb 11, 2021", "3:27 PM IST", "2021", "Last Modified",
                     "Last Modified ಶನಿವಾರ, 5 ಸೆಪ್ಟಂಬರ್ 2020", "The event was on Feb 11, 2021 at 3:27 PM IST.",
                     "Team Udayavani, Feb 11, 2021, 25:99 PM IST",
                     "Team Udayavani, Feb 11, 2021, 3:27 PM IST and the article continues"]:
            self.assertEqual(medicine.find_c1_matches(line + "\n"), [], line)

    def test_homepage_label_at_document_start(self):
        for prefix in ["", "\n  "]:
            text = prefix + "ಮುಖಪುಟ\nಲೇಖನದ ಶೀರ್ಷಿಕೆ\nಮೂಲ ಪಠ್ಯ\n"
            matches = medicine.find_c1_matches(text)
            self.assertEqual(matches, [{"start": len(prefix), "end": len(prefix) + len("ಮುಖಪುಟ"),
                                        "detail": "homepage navigation label"}])
            expected = ("\n" if prefix else "") + "ಲೇಖನದ ಶೀರ್ಷಿಕೆ\nಮೂಲ ಪಠ್ಯ\n"
            self.assertEqual(medicine.fix_c1_navigation(text), expected)
        inline = "ಮುಖಪುಟ / ಕರ್ನಾಟಕ\nಲೇಖನ\n"
        self.assertEqual(medicine.fix_c1_navigation(inline), " / ಕರ್ನಾಟಕ\nಲೇಖನ\n")
        for text in ["ಲೇಖನ\nಮುಖಪುಟ\n", "ಮುಖಪುಟದ ಬಗ್ಗೆ ಲೇಖನ\n"]:
            self.assertEqual(medicine.find_c1_matches(text), [])

    def test_homepage_before_top_navigation_bullets(self):
        text = "ಮುಖಪುಟ\n- News ಸುದ್ದಿ\nಲೇಖನ\n"
        self.assertEqual(len(medicine.find_c1_matches(text)), 1)
        self.assertEqual(len(medicine.find_c5_matches(text)), 1)
        self.assertEqual(medicine.fix_c1_navigation(text), "ಲೇಖನ\n")

    def test_pipe_terminated_city_labels_and_breadcrumbs(self):
        for city in ["ಬೆಂಗಳೂರು", "ಮೈಸೂರು", "ಚೆನ್ನೈ", "New Delhi", "St. Louis"]:
            with self.subTest(city=city):
                label = city + "|"
                text = "😀\n" + label + "\r\nಲೇಖನ\r\n"
                matches = medicine.find_c1_matches(text)
                self.assertEqual(matches, [{"start": 2, "end": 2 + len(label),
                                            "detail": "pipe-terminated city/navigation label"}])
                self.assertEqual(medicine.fix_c1_navigation(text), "😀\nಲೇಖನ\r\n")
        for line, count in [("ಬೆಂಗಳೂರು| ಬೆಂಗಳೂರು|", 2), ("ಮುಖಪುಟ | ಕರ್ನಾಟಕ | ಬೆಂಗಳೂರು |", 3)]:
            matches = medicine.find_c1_matches(line + "\nಲೇಖನ\n")
            self.assertEqual(len(matches), count)
            self.assertEqual(medicine.fix_c1_navigation(line + "\nಲೇಖನ\n"), "ಲೇಖನ\n")
        self.assertEqual(medicine.fix_c1_navigation("ಬೆಂಗಳೂರು| ಮಳೆಯ ವರದಿ\n"), "ಬೆಂಗಳೂರು| ಮಳೆಯ ವರದಿ\n")
        self.assertEqual(medicine.fix_c1_navigation("ಬೆಂಗಳೂರು|\nಮೈಸೂರು|\n- News ಸುದ್ದಿ\nಲೇಖನ\n"), "ಲೇಖನ\n")
        for text in ["ಬೆಂಗಳೂರು: ಮಳೆಯ ವರದಿ\n", "ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಮಳೆ\n", "ಬೆಂಗಳೂರು\n"]:
            self.assertEqual(medicine.find_c1_matches(text), [])

    def test_pipe_requires_lf_after_last_pipe_and_preserves_related_link(self):
        related = "ಇದನ್ನೂ ಓದಿ | ಕ್ರಾಂತಿಕಾರಿ ರೈತ ಹೋರಾಟದ ಸ್ಫೂರ್ತಿಯ ಚಿಲುಮೆ `ಅಜಿತ್ ಸಿಂಗ್‘\n"
        for text in [related, "▸" + related, "ಬೆಂಗಳೂರು| ಮಳೆಯ ವರದಿ\n", "ಬೆಂಗಳೂರು|", "ಬೆಂಗಳೂರು|\u2028"]:
            with self.subTest(text=text):
                self.assertEqual(medicine.find_c1_matches(text), [])
                self.assertEqual(medicine.fix_c1_navigation(text), text)
        for text in ["ಬೆಂಗಳೂರು|\n", "ಬೆಂಗಳೂರು|  \n", "ಬೆಂಗಳೂರು|\r\n", "ಮುಖಪುಟ | ಕರ್ನಾಟಕ | ಬೆಂಗಳೂರು |\n"]:
            self.assertTrue(medicine.find_c1_matches(text))
            self.assertEqual(medicine.fix_c1_navigation(text + "ಲೇಖನ\n"), "ಲೇಖನ\n")

    def test_social_follow_prompt_line_and_original_offsets(self):
        body = "ಲೇಖನದ ವಿಷಯ. ಕ್\u200cಕ ಕ್\u200dಕ\r\n"
        for line in ["Please follow and like us:", " please FOLLOW and like us :  ",
                     "Please follow and like us"]:
            with self.subTest(line=line):
                text = "😀\r\n" + line + "\r\n" + body
                matches = medicine.find_c1_matches(text)
                self.assertEqual(matches, [{"start": 3, "end": 3 + len(line),
                                            "detail": "social-follow prompt"}])
                self.assertIn("at offset 3", medicine.c1_evidence(text, matches))
                self.assertEqual(medicine.fix_c1_navigation(text), "😀\r\n" + body)
        for text in ["The page says Please follow and like us: in its footer.",
                     "Please follow and like us: is an example sentence."]:
            self.assertEqual(medicine.find_c1_matches(text), [])
            self.assertEqual(medicine.fix_c1_navigation(text), text)

    def test_traffic_safety_slogan_line(self):
        for line in [medicine.TRAFFIC_SLOGAN, "'" + medicine.TRAFFIC_SLOGAN + "'",
                     "“" + medicine.TRAFFIC_SLOGAN + "”"]:
            text = line + "\nಮೂಲ ಲೇಖನ\n"
            self.assertEqual(medicine.find_c1_matches(text), [
                {"start": 0, "end": len(line), "detail": "traffic-safety slogan"}
            ])
            self.assertEqual(medicine.fix_c1_navigation(text), "ಮೂಲ ಲೇಖನ\n")
        prose = "ವರದಿಯಲ್ಲಿ " + medicine.TRAFFIC_SLOGAN + " ಎಂದು ತಿಳಿಸಿದರು.\n"
        self.assertEqual(medicine.find_c1_matches(prose), [])
        self.assertEqual(medicine.fix_c1_navigation(prose), prose)

    def test_crlf_offsets_and_astral_prefix(self):
        crlf = SAMPLE.replace("\n", "\r\n")
        self.assertEqual(medicine.find_c5_matches(crlf)[0]["start"], 22)
        self.assertEqual(medicine.fix_c1_navigation(crlf + "ಕನ್ನಡ\r\n"), "ಕನ್ನಡ\r\n")
        prefixed = "😀\n" + SAMPLE + "body\n"
        matches = medicine.find_c1_matches(prefixed)
        self.assertEqual(matches[0]["start"], 2)
        self.assertEqual(medicine.find_c5_matches(prefixed)[0]["start"], 22)
        self.assertEqual(medicine.fix_c1_navigation(prefixed), "😀\nbody\n")

    def test_multiple_blocks_and_no_automatic_document_drop(self):
        self.assertEqual(len(medicine.find_c1_blocks(SAMPLE + "body\n" + SAMPLE)), 2)
        self.assertEqual(medicine.fix_c1_navigation(SAMPLE), "")
        report = medicine.harm_test([{"text": SAMPLE}])
        self.assertEqual(report["changed_documents"], 1)
        self.assertEqual(report["dropped_documents"], 0)
        self.assertFalse(report["passes_harm_test"])

    def test_sensitive_evidence_has_no_values(self):
        evidence = medicine.c1_evidence(SAMPLE, medicine.find_c1_matches(SAMPLE), redact=True)
        self.assertEqual(evidence.split(" | ")[0], "C1: navigation header at offset 0")
        self.assertNotIn("573", evidence)
        self.assertNotIn("Just In", evidence)

    def test_gold_harm_threshold_at_and_above_one_percent(self):
        clean = {"text": "ಕನ್ನಡ ಮೂಲ ಲೇಖನ"}
        for size, changed, expected in [(100, 1, True), (100, 2, False), (200, 2, True), (200, 3, False)]:
            with self.subTest(size=size, changed=changed):
                rows = [clean] * (size - changed) + [{"text": SAMPLE}] * changed
                result = medicine.harm_test(rows)
                self.assertEqual(result["gold_documents"], size)
                self.assertEqual(result["changed_or_dropped_documents"], changed)
                self.assertEqual(result["passes_harm_test"], expected)

    def test_empty_or_invalid_gold_set_cannot_pass(self):
        for rows in [[], [{"text": None}]]:
            with self.assertRaises(ValueError):
                medicine.harm_test(rows)

    def test_medicine_sheet_snippets_define_callable_repairs(self):
        snippets = load_medicine_snippets()
        self.assertEqual(set(snippets["RULES"]), {"C1", "C2", "C5", "G1", "A6", "F1"})
        self.assertTrue(all(callable(function) for function in snippets["RULES"].values()))


class FinalMedicineSnippetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snippets = load_medicine_snippets()

    def test_complete_metadata_lines_and_narrative_preservation(self):
        fix = self.snippets["medicine_c1"]
        body = "ಕನ್ನಡ ಮೂಲ ಲೇಖನ. ಕ್\u200cಕ ಕ್\u200dಕ\r\n"
        for line in ["Updated: Thursday, June 10, 2021, 20:15 [IST]",
                     "First Published Jan 20, 2021, 2:58 PM IST",
                     "ಬುಧವಾರ, 7 ಏಪ್ರಿಲ್ 2021 (11:15 IST)",
                     "Last Modified ಶನಿವಾರ, 5 ಸೆಪ್ಟಂಬರ್ 2020 (10:08 IST)",
                     "Please follow and like us:"]:
            with self.subTest(line=line):
                self.assertEqual(fix("😀\r\n" + line + "\r\n" + body), "😀\r\n" + body)
                prose = "The article quotes " + line + " in its discussion.\n"
                self.assertEqual(fix(prose), prose)
        for text in ["India\n", "Title\n", "ಬೆಂಗಳೂರು|\n", "Updated: June 10, 2021, 25:99 [IST]\n"]:
            self.assertEqual(fix(text), text)
        byline = "Team Udayavani, Feb 11, 2021, 3:27 PM IST\n"
        self.assertEqual(fix(byline, "https://www.udayavani.com/article"), "")
        self.assertEqual(fix(byline, "https://udayavani.com.example.invalid/article"), byline)

    def test_c5_requires_headed_links_or_a_complete_tag_cloud(self):
        fix = self.snippets["medicine_c5"]
        links = "Don't Miss!\n- News ಸುದ್ದಿ\n- Sports ಕ್ರೀಡೆ\nಲೇಖನ\n"
        self.assertEqual(fix(links), "Don't Miss!\nಲೇಖನ\n")
        for tags in ["#BJP4Belagavi #BJP4Maski", "# BJP4Belagavi# BJP4Maski"]:
            self.assertEqual(fix(tags + "\nಲೇಖನ\n"), "ಲೇಖನ\n")
            inline = "ಲೇಖನ " + tags + " ವಿಷಯ\n"
            self.assertEqual(fix(inline), inline)
        for text in ["# Heading\n", "#one\n", "- News ಸುದ್ದಿ\n- Sports ಕ್ರೀಡೆ\n"]:
            self.assertEqual(fix(text), text)

    def test_c2_exact_inline_prose_and_intentional_structures(self):
        fix = self.snippets["medicine_c2"]
        passage = ("This substantial prose sentence contains more than eight distinct words "
                   "and enough characters to qualify for the narrow repetition medicine.")
        text = passage + "\nOther prose. " + passage
        self.assertEqual(fix(text), passage + "\nOther prose. ")
        self.assertEqual(fix(fix(text)), fix(text))
        for protected in ["```\n" + text + "\n```", '"' + passage + '"\n"' + passage + '"',
                          "\n".join(["verse", "refrain", "another", "line", "song", "ending"]) + "\n" + text,
                          "— Parveen Kaswan (@ParveenKaswan) July 19, 2021\n"
                          "— Parveen Kaswan (@ParveenKaswan) July 20, 2021"]:
            self.assertEqual(fix(protected), protected)
        altered = passage.replace("eight", "ei\u200cght")
        self.assertEqual(fix(passage + "\nOther prose. " + altered), passage + "\nOther prose. " + altered)
        for char in ["\u200c", "\u200d", "½"]:
            unit = passage.replace("eight", "ei" + char + "ght")
            repeated = unit + "\n" + unit
            self.assertEqual(fix(repeated), repeated)

    def test_g1_only_explicit_pairs_and_word_boundaries(self):
        fix = self.snippets["medicine_g1"]
        self.assertEqual(fix("ಕೋಣೆ ಗಳ; ಶೀಘ್ರ ದಲ್ಲೇ"), "ಕೋಣೆಗಳ; ಶೀಘ್ರದಲ್ಲೇ")
        for text in ["10ನೇ 19ಮಾರಕ ಸ ರ್ಧೆ ವಣ ್ಸುವಾಗ ಅಽಕಾರಿ ಒನ್ಪ್ಲಸ್", "ಕೋಣೆ ಗಳಿಗೆ",
                     "```ಕೋಣೆ ಗಳ```", "ಕೋಣೆ\u200c ಗಳ"]:
            self.assertEqual(fix(text), text)

    def test_protected_unicode_survives_every_rule(self):
        strings = ["Please follow and like us:\u200c\n", "#one #two\u200d\n", "#one #two½\n",
                   "ಒನ್\u200cಪ್ಲಸ್ ರ\u200d್ಕ ರ್\u200dಕ ೦೧೨೩೪೫೬೭೮೯\n"]
        for fix in [*self.snippets["RULES"].values(), self.snippets["repair_all"]]:
            for text in strings:
                self.assertEqual(fix(text), text)

    def test_a6_only_known_complete_word_replacements(self):
        fix = self.snippets["medicine_a6"]
        self.assertEqual(fix("ಪೆÇಲೀಸ್ ಪೆÇಲೀಸರು ಬ್ಯಾ0ಕ್ ಸಿ0ಡಿಕೇಟ್ ಅಽಕಾರಿ"),
                         "ಪೊಲೀಸ್ ಪೊಲೀಸರು ಬ್ಯಾಂಕ್ ಸಿಂಡಿಕೇಟ್ ಅಧಿಕಾರಿ")
        for text in ["CETಗೆ ಗ್ರಾಪಂ Ç 0 ಽ ಸೋಽಹಂ", "Home ತುವಿನಲ್ಲಿ", "ಅಽಕಾರಿಗಳು",
                     "ಪೆÇಲೀಸ್\u200c", "```ಪೆÇಲೀಸ್```"]:
            self.assertEqual(fix(text), text)

    def test_f1_redacts_confirmed_original_spans_only(self):
        fix = self.snippets["medicine_f1"]
        phone, email = "0" * 10, "synthetic" + "@" + "example.invalid"
        text = "😀 " + phone + " email " + email + "."
        spans = [(2, 12), (text.index(email), text.index(email) + len(email))]
        self.assertEqual(fix(text), text)  # Presence alone is not approval.
        self.assertEqual(fix(text, confirmed_spans=spans), "😀 [REDACTED] email [REDACTED].")
        self.assertEqual(fix(text, confirmed_spans=[(6, 12), (2, 7)]),
                         "😀 [REDACTED] email " + email + ".")
        private_word = "ಒನ್\u200cಪ್ಲಸ್"
        self.assertEqual(fix("😀 " + private_word, confirmed_spans=[(2, 2 + len(private_word))]),
                         "😀 [REDACTED]")
        for spans in [[(-1, 2)], [(2, 2)], [(0, len(text) + 1)], [(True, 2)], [(0.5, 2)]]:
            with self.assertRaises(ValueError):
                fix(text, confirmed_spans=spans)

    def test_f1_applies_before_other_rules_change_offsets(self):
        phone = "0" * 10
        text = "Please follow and like us:\nCall " + phone
        start = text.index(phone)
        self.assertEqual(self.snippets["repair_all"](text, confirmed_spans=[(start, start + 10)]),
                         "Call [REDACTED]")

    def test_combined_order_and_gold_harm_boundary(self):
        text = "Just In\nDon't Miss!\n- News ಸುದ್ದಿ\n- Sports ಕ್ರೀಡೆ\nಕೋಣೆ ಗಳ\n"
        fixed = self.snippets["repair_all"](text)
        self.assertEqual(fixed, "ಕೋಣೆಗಳ\n")
        self.assertEqual(self.snippets["repair_all"](fixed), fixed)
        clean = {"text": "ಕನ್ನಡ ಮೂಲ ಲೇಖನ", "url": "https://example.invalid/article", "confirmed_private_spans": []}
        bad = {**clean, "text": "Please follow and like us:\nಕನ್ನಡ ಮೂಲ ಲೇಖನ"}
        for size, changed, passes in [(100, 1, True), (100, 2, False), (200, 2, True), (200, 3, False)]:
            result = self.snippets["harm_report"]([bad] * changed + [clean] * (size - changed))
            for code in ("C1", "combined"):
                self.assertEqual(result[code]["changed_documents"], changed)
                self.assertEqual(result[code]["dropped_documents"], 0)
                self.assertEqual(result[code]["passes_harm_test"], passes)
        for rows in [[], [{"text": None, "url": clean["url"]}], [{"text": "text"}],
                     [{"text": "text", "url": clean["url"]}]]:
            with self.assertRaises(ValueError):
                self.snippets["harm_report"](rows)

    def test_f1_harm_counts_confirmed_replacements_and_states_its_scope(self):
        clean = {"text": "ಕನ್ನಡ", "url": "https://example.invalid/", "confirmed_private_spans": []}
        redacted = {**clean, "text": "x " + "0" * 10, "confirmed_private_spans": [(2, 12)]}
        result = self.snippets["harm_report"]([redacted] + [clean] * 99)
        for code in ("F1", "combined"):
            self.assertEqual(result[code]["changed_documents"], 1)
            self.assertEqual(result[code]["dropped_documents"], 0)
        self.assertIn("detector not evaluated", result["F1"]["scope"])

    def test_empty_text_result_counts_as_harm_not_a_drop(self):
        self.assertEqual(self.snippets["medicine_c1"]("Don't Miss!"), "")
        result = self.snippets["harm_report"]([{"text": "Don't Miss!", "url": "https://example.invalid/",
                                                 "confirmed_private_spans": []}])
        self.assertEqual(result["C1"]["changed_documents"], 1)
        self.assertEqual(result["C1"]["dropped_documents"], 0)
        self.assertFalse(result["C1"]["passes_harm_test"])


if __name__ == "__main__":
    unittest.main()
