from unittest import TestCase, main

from btotp.clipboard import copy_to_clipboard


class TestClipboard(TestCase):
    def test_copy_does_not_crash(self):
        result = copy_to_clipboard("test-code-1234")
        self.assertIsInstance(result, bool)


if __name__ == "__main__":
    main()
