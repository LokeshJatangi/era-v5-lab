"""Synthetic tests only: never read or modify the real pack/reviews."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import pyarrow as pa
import pyarrow.parquet as pq

import c1_site_boilerplate as medicine
import review_server as server
from test_c1_navigation import load_medicine_snippets


URL = "https://m.varthabharati.in/article/2021_04_07/285999"
BODY = "😀 ಕನ್ನಡ ಲೇಖನ. ಕ್\u200dಕ ಕ್\u200cಕ  \r\n"
NEWS18_URL = "https://kannada.news18.com/news/sports/synthetic.html"
NEWS18_SAMPLE = "news18-kannada Updated:\nFebruary 14, 2021, 6:22 PM IST\nIndia\n"


class VarthaBharatiMedicineTests(unittest.TestCase):
    def test_exact_footer_offsets_repair_and_idempotence(self):
        self.assertEqual(len(medicine.FOOTER), 120)
        text = BODY + medicine.FOOTER
        matches = medicine.find_varthabharati_footer(text, URL)
        self.assertEqual(matches, [{"start": len(BODY), "end": len(text),
                                   "detail": "Vartha Bharati donation/support footer"}])
        self.assertEqual(medicine.fix_varthabharati_footer(text, URL), BODY)
        self.assertEqual(medicine.fix_varthabharati_footer(BODY, URL), BODY)

    def test_lf_crlf_and_whitespace_outside_removal_preserved(self):
        for newline in ("\n", "\r\n"):
            footer = newline.join(medicine.FOOTER_LINES)
            for suffix in ("", "\n", " \t\r\n"):
                text = BODY + footer + suffix
                self.assertEqual(medicine.fix_varthabharati_footer(text, URL), BODY + suffix)

    def test_host_guard_and_article_text_negatives(self):
        for url in ("https://varthabharati.in/article/1", URL,
                    "https://www.varthabharati.in/article/1", "https://M.VARTHABHARATI.IN/article/1"):
            self.assertEqual(medicine.fix_varthabharati_footer(BODY + medicine.FOOTER, url), BODY)
        for url in (None, "", "varthabharati.in/article/1", "https://example.invalid/varthabharati.in",
                    "https://notvarthabharati.in/", "https://varthabharati.in.example.invalid/",
                    "https://varthabharati.in@example.invalid/", "ftp://varthabharati.in/", "http://[bad"):
            text = BODY + medicine.FOOTER
            self.assertEqual(medicine.fix_varthabharati_footer(text, url), text, url)
        for text in (BODY + medicine.FOOTER + "\nಲೇಖನ ಮುಂದುವರಿಯುತ್ತದೆ.",
                     BODY + "ಉಲ್ಲೇಖ: " + medicine.FOOTER,
                     BODY + medicine.FOOTER_LINES[0], BODY + medicine.FOOTER_LINES[1],
                     BODY + medicine.FOOTER.replace("ಆಪ್ತವೇ", "ಬಗ್ಗೆ")):
            self.assertEqual(medicine.fix_varthabharati_footer(text, URL), text)

    def test_table_keeps_rows_ids_metadata_and_other_sites(self):
        rows = [{"doc_id": "site", "url": URL, "text": BODY + medicine.FOOTER, "meta": {"key": "keep"}},
                {"doc_id": "other", "url": "https://example.invalid/", "text": BODY + medicine.FOOTER,
                 "meta": {"key": "also keep"}}]
        table = pa.Table.from_pylist(rows).replace_schema_metadata({b"test": b"preserve"})
        cleaned, report = medicine.clean_table(table)
        expected = [{**rows[0], "text": BODY}, rows[1]]
        self.assertEqual(cleaned.to_pylist(), expected)
        self.assertTrue(cleaned.schema.equals(table.schema, check_metadata=True))
        self.assertEqual(report["changed_documents"], 1)
        self.assertEqual(report["site_documents"], 1)
        self.assertEqual(report["removed_characters"], 120)
        self.assertEqual(report["dropped_documents"], 0)
        self.assertEqual(report["gold_harm_test"], "NOT RUN")
        again, second = medicine.clean_table(cleaned)
        self.assertTrue(again.equals(cleaned))
        self.assertEqual(second["changed_documents"], 0)

    def test_viewer_candidate_and_evidence_use_url_and_original_offsets(self):
        text = BODY + medicine.FOOTER
        result = server.inspect_text(text, url=URL)
        c1 = next(f for f in result["findings"] if f["code"] == "C1")
        self.assertEqual(c1["matches"], medicine.find_varthabharati_footer(text, URL))
        self.assertEqual(c1["count"], 1)
        self.assertNotIn("C1", {f["code"] for f in server.inspect_text(text)["findings"]})
        self.assertNotIn("diseases", result)

    def test_harm_boundary_and_missing_provenance(self):
        clean = {"text": BODY, "url": URL}
        affected = {"text": BODY + medicine.FOOTER, "url": URL}
        for count, passes in ((1, True), (2, False)):
            result = medicine.harm_test([affected] * count + [clean] * (100 - count))
            self.assertEqual(result["changed_documents"], count)
            self.assertEqual(result["passes_harm_test"], passes)
            self.assertEqual(result["dropped_documents"], 0)
        for rows in ([], [{"text": BODY}], [{"text": BODY, "url": ""}], [{"text": None, "url": URL}]):
            with self.assertRaises(ValueError):
                medicine.harm_test(rows)

    def test_cli_refuses_overwrite_and_new_output_preserves_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pack, output, report = (root / name for name in ("input.parquet", "clean.parquet", "changes.json"))
            pq.write_table(pa.Table.from_pylist([{"doc_id": "one", "url": URL, "text": BODY + medicine.FOOTER}]), pack)
            original_bytes = pack.read_bytes()
            command = [sys.executable, str(Path(medicine.__file__)), "--pack", str(pack)]
            result = subprocess.run(command + ["--output", str(output), "--report", str(report)],
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(pq.read_table(output)["text"].to_pylist(), [BODY])
            self.assertEqual(pack.read_bytes(), original_bytes)
            for target in (pack, output):
                result = subprocess.run(command + ["--output", str(target)],
                                        capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 2)
                self.assertIn("Refusing to replace", result.stderr)
            self.assertEqual(pack.read_bytes(), original_bytes)


class News18MedicineTests(unittest.TestCase):
    def test_final_sheet_c1_snippet_scopes_footer_by_host(self):
        fix = load_medicine_snippets()["medicine_c1"]
        text = BODY + medicine.FOOTER
        self.assertEqual(fix(text, URL), BODY)
        for url in [None, "https://varthabharati.in.example.invalid/article", "https://example.invalid/article"]:
            self.assertEqual(fix(text, url), text)
        self.assertEqual(fix(NEWS18_SAMPLE + BODY, NEWS18_URL), "India\n" + BODY)

    def test_exact_reported_lines_offsets_and_repair(self):
        text = "😀\n" + NEWS18_SAMPLE + BODY
        matches = medicine.find_news18_boilerplate(text, NEWS18_URL)
        self.assertEqual([text[m["start"]:m["end"]] for m in matches],
                         ["news18-kannada Updated:", "February 14, 2021, 6:22 PM IST", "India"])
        self.assertEqual(matches[0]["start"], 2)
        self.assertEqual(medicine.fix_site_boilerplate(text, NEWS18_URL), "😀\n" + BODY)
        self.assertEqual(medicine.fix_site_boilerplate("😀\n" + BODY, NEWS18_URL), "😀\n" + BODY)
        c1 = next(f for f in server.inspect_text(text, url=NEWS18_URL)["findings"] if f["code"] == "C1")
        self.assertEqual(c1["count"], 3)  # Timestamp also matches generic C1; count it once.
        self.assertEqual(c1["matches"], matches)

    def test_isolated_header_or_india_preserves_following_body(self):
        for prefix in ("news18-kannada Updated:\n", "India\n", "  India  \r\n"):
            self.assertEqual(medicine.fix_site_boilerplate(prefix + BODY, NEWS18_URL), BODY)
        self.assertEqual(medicine.fix_site_boilerplate("India", NEWS18_URL), "")
        date = "February 14, 2021, 6:22 PM IST\n"
        self.assertEqual(medicine.fix_site_boilerplate(date + BODY, NEWS18_URL), date + BODY)
        bad_date = "February 14, 2021, 25:99 PM IST\n"
        self.assertEqual(medicine.fix_site_boilerplate("news18-kannada Updated:\n" + bad_date + BODY, NEWS18_URL), bad_date + BODY)

    def test_site_path_and_complete_line_guards(self):
        for url in (URL, None, "https://news18.com/news/", "https://kannada.news18.com/newsroom/",
                    "https://kannada.news18.com/", "https://kannada.news18.com.example.invalid/news/"):
            text = NEWS18_SAMPLE + BODY
            self.assertEqual(medicine.fix_site_boilerplate(text, url), text)
        for line in ("India won the match.", "The country India", "India Today", "‘India’", "news18-kannada Updated: extra text"):
            text = line + "\n" + BODY
            self.assertEqual(medicine.fix_site_boilerplate(text, NEWS18_URL), text)
        crlf = "  " + NEWS18_SAMPLE.replace("\n", "\r\n")
        self.assertEqual(medicine.fix_site_boilerplate(crlf + BODY, NEWS18_URL), BODY)

    def test_combined_cleaner_keeps_unmatched_site_document(self):
        rows = [{"doc_id": "footer", "text": BODY + medicine.FOOTER, "url": URL},
                {"doc_id": "news18", "text": NEWS18_SAMPLE + BODY, "url": NEWS18_URL},
                {"doc_id": "news18-body", "text": BODY, "url": NEWS18_URL}]
        cleaned, report = medicine.clean_table(pa.Table.from_pylist(rows))
        self.assertEqual(cleaned["text"].to_pylist(), [BODY, BODY, BODY])
        self.assertEqual(report["changed_documents"], 2)
        self.assertEqual(report["site_documents_by_site"], {"varthabharati": 1, "news18-kannada": 2})
        self.assertEqual(report["changed_documents_by_site"], {"varthabharati": 1, "news18-kannada": 1})
        gold = [{"text": NEWS18_SAMPLE + BODY, "url": NEWS18_URL}] + [{"text": BODY, "url": NEWS18_URL}] * 99
        self.assertTrue(medicine.harm_test(gold)["passes_harm_test"])


if __name__ == "__main__":
    unittest.main()
