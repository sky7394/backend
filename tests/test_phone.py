import unittest

from app.utils.phone import normalize_iran_mobile


class PhoneUtilsTests(unittest.TestCase):
    def test_normalizes_valid_local_mobile_number(self):
        self.assertEqual(normalize_iran_mobile("09123456789"), "09123456789")

    def test_normalizes_valid_international_plus_98_format(self):
        self.assertEqual(normalize_iran_mobile("+989123456789"), "09123456789")

    def test_normalizes_valid_international_98_format(self):
        self.assertEqual(normalize_iran_mobile("989123456789"), "09123456789")

    def test_normalizes_spaces_and_hyphens(self):
        self.assertEqual(normalize_iran_mobile("+98 912-345-6789"), "09123456789")
        self.assertEqual(normalize_iran_mobile("0912 345 6789"), "09123456789")

    def test_normalization_is_idempotent(self):
        normalized = normalize_iran_mobile("+98 912-345-6789")

        self.assertEqual(normalize_iran_mobile(normalized), normalized)

    def test_strips_outer_whitespace(self):
        self.assertEqual(normalize_iran_mobile("  09123456789\n"), "09123456789")

    def test_rejects_empty_input(self):
        with self.assertRaisesRegex(ValueError, "Invalid Iranian mobile number"):
            normalize_iran_mobile("")

    def test_rejects_whitespace_only_input(self):
        with self.assertRaisesRegex(ValueError, "Invalid Iranian mobile number"):
            normalize_iran_mobile("   ")

    def test_rejects_too_short_number(self):
        with self.assertRaisesRegex(ValueError, "Invalid Iranian mobile number"):
            normalize_iran_mobile("0912345678")

    def test_rejects_too_long_number(self):
        with self.assertRaisesRegex(ValueError, "Invalid Iranian mobile number"):
            normalize_iran_mobile("091234567890")

    def test_rejects_invalid_prefix(self):
        with self.assertRaisesRegex(ValueError, "Invalid Iranian mobile number"):
            normalize_iran_mobile("08123456789")

    def test_rejects_landline_style_number(self):
        with self.assertRaisesRegex(ValueError, "Invalid Iranian mobile number"):
            normalize_iran_mobile("02112345678")

    def test_rejects_non_digit_characters(self):
        with self.assertRaisesRegex(ValueError, "Invalid Iranian mobile number"):
            normalize_iran_mobile("0912abc67890")

    def test_rejects_parentheses_separator_as_unsupported(self):
        with self.assertRaisesRegex(ValueError, "Invalid Iranian mobile number"):
            normalize_iran_mobile("+98 (912) 345-6789")

    def test_rejects_slash_separator_as_unsupported(self):
        with self.assertRaisesRegex(ValueError, "Invalid Iranian mobile number"):
            normalize_iran_mobile("0912/345/6789")

    def test_rejects_persian_digits_as_unsupported(self):
        with self.assertRaisesRegex(ValueError, "Invalid Iranian mobile number"):
            normalize_iran_mobile("۰۹۱۲۳۴۵۶۷۸۹")

    def test_rejects_arabic_indic_digits_as_unsupported(self):
        with self.assertRaisesRegex(ValueError, "Invalid Iranian mobile number"):
            normalize_iran_mobile("٠٩١٢٣٤٥٦٧٨٩")


if __name__ == "__main__":
    unittest.main()
