import time
from unittest import TestCase, main

from btotp.core import _time_counter, _hmac, hotp, totp, generate_code, verify_code
from btotp.core import DEFAULT_TIME_STEP, DEFAULT_CODE_LENGTH, DEFAULT_HASH_ALGO
from btotp.charset import CHARSET, encode_to_chars
from btotp.secret import generate_secret


class TestTimeCounter(TestCase):
    def test_counter_at_epoch(self):
        self.assertEqual(_time_counter(0), 0)

    def test_counter_starts_at_zero(self):
        self.assertEqual(_time_counter(0), 0)

    def test_counter_increments_per_time_step(self):
        self.assertEqual(_time_counter(DEFAULT_TIME_STEP - 0.001), 0)
        self.assertEqual(_time_counter(DEFAULT_TIME_STEP), 1)
        self.assertEqual(_time_counter(2 * DEFAULT_TIME_STEP), 2)

    def test_counter_at_time_step(self):
        self.assertEqual(_time_counter(DEFAULT_TIME_STEP - 1), 0)
        self.assertEqual(_time_counter(DEFAULT_TIME_STEP), 1)
        self.assertEqual(_time_counter(2 * DEFAULT_TIME_STEP), 2)

    def test_counter_returns_int(self):
        cnt = _time_counter()
        self.assertIsInstance(cnt, int)
        self.assertGreater(cnt, 1000000)

    def test_custom_time_step(self):
        self.assertEqual(_time_counter(0, time_step=30), 0)
        self.assertEqual(_time_counter(30, time_step=30), 1)
        self.assertEqual(_time_counter(60, time_step=30), 2)

    def test_custom_time_step_half(self):
        self.assertEqual(_time_counter(29, time_step=30), 0)
        self.assertEqual(_time_counter(30, time_step=30), 1)


class TestEncodedToChars(TestCase):
    def test_output_length(self):
        result = encode_to_chars(bytes(range(64)))
        self.assertEqual(len(result), 12)

    def test_output_contains_only_valid_chars(self):
        result = encode_to_chars(bytes(range(64)))
        for ch in result:
            self.assertIn(ch, CHARSET, f"Character {ch!r} not in charset")

    def test_deterministic(self):
        h1 = encode_to_chars(bytes(range(64)))
        h2 = encode_to_chars(bytes(range(64)))
        self.assertEqual(h1, h2)

    def test_different_inputs_produce_different_outputs(self):
        h1 = encode_to_chars(bytes(range(64)))
        h2 = encode_to_chars(bytes(range(1, 65)))
        self.assertNotEqual(h1, h2)

    def test_custom_length(self):
        for length in [6, 8, 12, 16]:
            result = encode_to_chars(bytes(range(64)), length)
            self.assertEqual(len(result), length)


class TestHotp(TestCase):
    def test_deterministic_hotp(self):
        secret = bytes(range(16))
        c1 = hotp(secret, 42)
        c2 = hotp(secret, 42)
        self.assertEqual(c1, c2)

    def test_different_counter_produces_different_code(self):
        secret = bytes(range(16))
        c1 = hotp(secret, 1)
        c2 = hotp(secret, 2)
        self.assertNotEqual(c1, c2)

    def test_length_is_12(self):
        secret = bytes(range(16))
        code = hotp(secret, 0)
        self.assertEqual(len(code), 12)

    def test_only_valid_chars(self):
        secret = bytes(range(16))
        for _ in range(10):
            code = hotp(secret, _)
            for c in code:
                self.assertIn(c, CHARSET)

    def test_custom_code_length(self):
        secret = bytes(range(16))
        code = hotp(secret, 0, code_length=8)
        self.assertEqual(len(code), 8)

    def test_custom_algorithm(self):
        secret = bytes(range(16))
        c1 = hotp(secret, 0, algorithm="sha1")
        c2 = hotp(secret, 0, algorithm="sha256")
        c3 = hotp(secret, 0, algorithm="sha512")
        self.assertEqual(len(c1), 12)
        self.assertEqual(len(c2), 12)
        self.assertEqual(len(c3), 12)

    def test_different_algos_differ(self):
        secret = bytes(range(16))
        c1 = hotp(secret, 0, algorithm="sha1")
        c2 = hotp(secret, 0, algorithm="sha256")
        self.assertNotEqual(c1, c2)


class TestTOTP(TestCase):
    def test_totp_deterministic_in_same_second(self):
        secret = bytes(range(16))
        t = int(time.time())
        t = t - (t % DEFAULT_TIME_STEP) + 1
        r1 = totp(secret, t)
        r2 = totp(secret, t)
        self.assertEqual(r1, r2)

    def test_valid_output(self):
        secret = bytes(range(16))
        code = totp(secret)
        self.assertEqual(len(code), 12)
        for c in code:
            self.assertIn(c, CHARSET)

    def test_custom_time_step(self):
        secret = bytes(range(16))
        code = totp(secret, time_step=30)
        self.assertEqual(len(code), 12)

    def test_custom_code_length(self):
        secret = bytes(range(16))
        code = totp(secret, code_length=8)
        self.assertEqual(len(code), 8)


class TestVerify(TestCase):
    def test_verify_own_code(self):
        secret = bytes(range(16))
        code = totp(secret)
        self.assertTrue(verify_code(secret, code))

    def test_verify_rejects_bad_code(self):
        secret = bytes(range(16))
        bad = "a" * 12
        self.assertFalse(verify_code(secret, bad))

    def test_verify_tolerates_one_step_window(self):
        secret = bytes(range(16))
        base_counter = _time_counter()
        next_code = hotp(secret, base_counter + 1)
        self.assertTrue(verify_code(secret, next_code, window=1))

    def test_verify_rejects_outside_window(self):
        secret = bytes(range(16))
        base_counter = _time_counter()
        far_code = hotp(secret, base_counter + 3)
        self.assertFalse(verify_code(secret, far_code, window=1))

    def test_verify_accepts_previous_step(self):
        secret = bytes(range(16))
        base_counter = _time_counter()
        prev_code = hotp(secret, base_counter - 1)
        self.assertTrue(verify_code(secret, prev_code, window=1))

    def test_verify_with_custom_params(self):
        secret = bytes(range(16))
        code = totp(secret, algorithm="sha256", code_length=8, time_step=30)
        self.assertTrue(verify_code(secret, code, algorithm="sha256", code_length=8, time_step=30))
        self.assertFalse(verify_code(secret, code, algorithm="sha1", code_length=8, time_step=30))

    def test_verify_with_string_key(self):
        code = generate_code("test-key")
        self.assertTrue(verify_code("test-key", code))


class TestGenerateCode(TestCase):
    def test_generate_accepts_string(self):
        code = generate_code("test-key-1234")
        self.assertEqual(len(code), 12)

    def test_generate_accepts_bytes(self):
        code = generate_code(b"test-key-1234")
        self.assertEqual(len(code), 12)

    def test_deterministic(self):
        c1 = generate_code(b"fixed-key", 100000)
        c2 = generate_code(b"fixed-key", 100000)
        self.assertEqual(c1, c2)

    def test_generate_with_all_params(self):
        code = generate_code(b"test", algorithm="sha256", code_length=8, time_step=30)
        self.assertEqual(len(code), 8)

    def test_generate_code_at(self):
        from btotp.core import generate_code_at
        code = generate_code_at(b"test", 100000)
        self.assertEqual(len(code), 12)


class TestSecretGeneration(TestCase):
    def test_secret_length(self):
        s = generate_secret()
        self.assertEqual(len(s), 64)

    def test_secret_is_random(self):
        s1 = generate_secret()
        s2 = generate_secret()
        self.assertNotEqual(s1, s2)

    def test_secret_custom_length(self):
        s = generate_secret(32)
        self.assertEqual(len(s), 32)


class TestHMACDeterminism(TestCase):
    def test_hmac_deterministic(self):
        secret = bytes(range(64))
        r1 = _hmac(secret, 42)
        r2 = _hmac(secret, 42)
        self.assertEqual(r1, r2)

    def test_different_inputs_differ(self):
        r1 = _hmac(bytes(range(64)), 1)
        r2 = _hmac(bytes(range(64)), 2)
        self.assertNotEqual(r1, r2)

    def test_output_length(self):
        result = _hmac(bytes(range(64)), 0)
        self.assertEqual(len(result), 64)

    def test_sha256_output_length(self):
        result = _hmac(bytes(range(64)), 0, algorithm="sha256")
        self.assertEqual(len(result), 32)

    def test_sha1_output_length(self):
        result = _hmac(bytes(range(64)), 0, algorithm="sha1")
        self.assertEqual(len(result), 20)

    def test_known_output(self):
        secret = bytes.fromhex("000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f")
        result = _hmac(secret, 0)
        expected_prefix = bytes.fromhex("2142fd323744ca3e")
        self.assertEqual(result[:len(expected_prefix)], expected_prefix)

    def test_sanity_hotp_produces_valid_results(self):
        secret = bytes(range(32))
        for c in range(10):
            code = hotp(secret, c)
            self.assertEqual(len(code), 12)
            for ch in code:
                self.assertIn(ch, CHARSET)

    def test_different_algorithms(self):
        secret = bytes(range(16))
        for algo in ("sha1", "sha256", "sha512"):
            result = _hmac(secret, 0, algorithm=algo)
            self.assertIn(len(result), (20, 32, 64))


class TestRoundTrip(TestCase):
    def test_secret_to_code_to_verify(self):
        secret = generate_secret()
        code = totp(secret)
        self.assertTrue(verify_code(secret, code))
        self.assertFalse(verify_code(secret, code + "x"))


if __name__ == "__main__":
    main()
