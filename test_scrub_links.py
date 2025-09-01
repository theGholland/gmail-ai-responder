import unittest

from runner import scrub_links


class ScrubLinksTests(unittest.TestCase):
    def test_link_reduced_to_domain(self):
        self.assertEqual(
            scrub_links("https://linkedin.com/long/path?query=123"),
            "linkedin.com",
        )

    def test_links_inside_text(self):
        text = (
            "Visit https://linkedin.com/long/path?query=123 and http://example.org/foo."
        )
        expected = "Visit linkedin.com and example.org."
        self.assertEqual(scrub_links(text), expected)


if __name__ == "__main__":
    unittest.main()
