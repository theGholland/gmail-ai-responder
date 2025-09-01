import unittest

from runner import scrub_formatting


class ScrubFormattingTests(unittest.TestCase):
    def test_html_tags_removed(self):
        self.assertEqual(scrub_formatting("Hello <b>World</b>"), "Hello World")

    def test_collapse_blank_lines(self):
        text = "Line1\n\n\nLine2"
        expected = "Line1\n\nLine2"
        self.assertEqual(scrub_formatting(text), expected)

    def test_preserve_email_addresses(self):
        text = "Contact <john@doe.com> for info"
        self.assertIn("john@doe.com", scrub_formatting(text))


if __name__ == "__main__":
    unittest.main()

