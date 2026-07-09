from unittest import TestCase, main

from btotp.uri import parse_otpauth, generate_uri


class TestParseOTPAuth(TestCase):
    def test_basic_uri(self):
        uri = "otpauth://totp/Example:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Example"
        result = parse_otpauth(uri)
        self.assertEqual(result["account"], "user@example.com")
        self.assertEqual(result["issuer"], "Example")
        self.assertEqual(result["algorithm"], "sha1")
        self.assertEqual(result["digits"], 12)
        self.assertEqual(result["period"], 45)

    def test_without_issuer_prefix(self):
        uri = "otpauth://totp/user@example.com?secret=JBSWY3DPEHPK3PXP"
        result = parse_otpauth(uri)
        self.assertEqual(result["account"], "user@example.com")
        self.assertEqual(result["issuer"], "")

    def test_custom_params(self):
        uri = "otpauth://totp/Test:app?secret=JBSWY3DPEHPK3PXP&algorithm=SHA256&digits=8&period=30"
        result = parse_otpauth(uri)
        self.assertEqual(result["algorithm"], "sha256")
        self.assertEqual(result["digits"], 8)
        self.assertEqual(result["period"], 30)

    def test_invalid_scheme(self):
        with self.assertRaises(ValueError):
            parse_otpauth("otpauth://hotp/secret?secret=JBSWY3DPEHPK3PXP")

    def test_missing_secret(self):
        with self.assertRaises(ValueError):
            parse_otpauth("otpauth://totp/test?issuer=Test")


class TestGenerateURI(TestCase):
    def test_generate_basic(self):
        uri = generate_uri("user@example.com", "deadbeef" * 8, issuer="Example")
        self.assertTrue(uri.startswith("otpauth://totp/"))
        self.assertIn("secret=", uri)
        self.assertIn("issuer=Example", uri)

    def test_roundtrip(self):
        uri = generate_uri("myaccount", "deadbeef" * 8, issuer="MyApp",
                           algorithm="sha256", digits=8, period=30)
        parsed = parse_otpauth(uri)
        self.assertEqual(parsed["account"], "myaccount")
        self.assertEqual(parsed["issuer"], "MyApp")
        self.assertEqual(parsed["secret"], "deadbeef" * 8)
        self.assertEqual(parsed["algorithm"], "sha256")
        self.assertEqual(parsed["digits"], 8)
        self.assertEqual(parsed["period"], 30)

    def test_no_issuer(self):
        uri = generate_uri("myaccount", "deadbeef" * 8)
        parsed = parse_otpauth(uri)
        self.assertEqual(parsed["account"], "myaccount")
        self.assertEqual(parsed["issuer"], "")


if __name__ == "__main__":
    main()
