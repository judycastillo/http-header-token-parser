import unittest

from http_header_token_parser import Token, HeaderValue, parse_header_value


class TestParseHeaderValue(unittest.TestCase):
    def test_empty(self):
        hv = parse_header_value("")
        self.assertEqual(hv.elements, [])
        self.assertIsNone(hv.first())
        self.assertEqual(hv.tokens(), [])

    def test_whitespace_only(self):
        hv = parse_header_value("   \t  ")
        self.assertEqual(hv.elements, [])

    def test_single_token(self):
        hv = parse_header_value("gzip")
        self.assertEqual(len(hv), 1)
        self.assertEqual(hv.elements[0], Token("gzip", False))
        self.assertEqual(hv.first(), "gzip")

    def test_multiple_tokens(self):
        hv = parse_header_value("gzip deflate br")
        self.assertEqual(hv.tokens(), ["gzip", "deflate", "br"])
        self.assertEqual([t.is_quoted for t in hv], [False, False, False])

    def test_multiple_spaces_between(self):
        hv = parse_header_value("gzip   deflate")
        self.assertEqual(hv.tokens(), ["gzip", "deflate"])

    def test_tab_between_tokens(self):
        hv = parse_header_value("gzip\tdeflate")
        self.assertEqual(hv.tokens(), ["gzip", "deflate"])

    def test_empty_quoted_string(self):
        hv = parse_header_value('""')
        self.assertEqual(hv.elements, [Token("", True)])

    def test_quoted_string(self):
        hv = parse_header_value('"text/html"')
        self.assertEqual(hv.elements, [Token("text/html", True)])

    def test_quoted_string_with_spaces(self):
        hv = parse_header_value('"keep alive"')
        self.assertEqual(hv.elements, [Token("keep alive", True)])

    def test_escape_in_quoted_string(self):
        hv = parse_header_value(r'"a\\b"')
        self.assertEqual(hv.elements[0].value, "a\\b")
        self.assertTrue(hv.elements[0].is_quoted)

    def test_escape_quote(self):
        hv = parse_header_value(r'"say \"hi\""')
        self.assertEqual(hv.elements[0].value, 'say "hi"')

    def test_mixed_token_and_quoted(self):
        hv = parse_header_value('gzip "identity;q=0" br')
        self.assertEqual(hv.tokens(), ["gzip", "identity;q=0", "br"])
        self.assertEqual([t.is_quoted for t in hv], [False, True, False])

    def test_iter(self):
        hv = parse_header_value("gzip br")
        self.assertEqual([t.value for t in hv], ["gzip", "br"])

    def test_obs_fold_crlf(self):
        hv = parse_header_value("gzip\r\n deflate")
        self.assertEqual(hv.tokens(), ["gzip", "deflate"])

    def test_obs_fold_multiple_spaces(self):
        hv = parse_header_value("gzip\r\n   deflate")
        self.assertEqual(hv.tokens(), ["gzip", "deflate"])

    def test_obs_fold_tab(self):
        hv = parse_header_value("gzip\r\n\tdeflate")
        self.assertEqual(hv.tokens(), ["gzip", "deflate"])

    def test_token_with_all_tchars(self):
        hv = parse_header_value("!#$%&'*+-.^_`|~")
        self.assertEqual(hv.elements[0].value, "!#$%&'*+-.^_`|~")
        self.assertFalse(hv.elements[0].is_quoted)

    def test_bare_cr_raises(self):
        with self.assertRaises(ValueError):
            parse_header_value("gzip\rdeflate")

    def test_bare_lf_raises(self):
        with self.assertRaises(ValueError):
            parse_header_value("gzip\ndeflate")

    def test_unterminated_quote_raises(self):
        with self.assertRaises(ValueError):
            parse_header_value('"unterminated')

    def test_dangling_backslash_raises(self):
        with self.assertRaises(ValueError):
            parse_header_value('"end with \\')

    def test_comma_in_token_raises(self):
        with self.assertRaises(ValueError):
            parse_header_value("gzip,deflate")

    def test_non_str_raises(self):
        with self.assertRaises(TypeError):
            parse_header_value(b"gzip")

    def test_token_dataclass_is_frozen(self):
        t = Token("gzip", False)
        with self.assertRaises(Exception):
            t.value = "deflate"


if __name__ == "__main__":
    unittest.main()
