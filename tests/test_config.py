import os
import tempfile
from unittest import TestCase, main
from unittest.mock import patch

from btotp.config import load_config, save_config, DEFAULTS


class TestConfig(TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.tmpdir, "config.json")
        self.patcher = patch("btotp.config.CONFIG_PATH", self.config_path)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        os.rmdir(self.tmpdir)

    def test_defaults(self):
        config = load_config()
        self.assertEqual(config["time_step"], 45)
        self.assertEqual(config["code_length"], 12)
        self.assertEqual(config["hash_algo"], "sha512")
        self.assertEqual(config["clipboard"], False)

    def test_save_and_load(self):
        save_config({"time_step": 30, "code_length": 8})
        config = load_config()
        self.assertEqual(config["time_step"], 30)
        self.assertEqual(config["code_length"], 8)
        self.assertEqual(config["hash_algo"], "sha512")

    def test_partial_update(self):
        save_config({"time_step": 30})
        config = load_config()
        self.assertEqual(config["time_step"], 30)
        self.assertEqual(config["code_length"], 12)

    def test_persists_across_loads(self):
        save_config({"hash_algo": "sha256"})
        c1 = load_config()
        c2 = load_config()
        self.assertEqual(c1, c2)


if __name__ == "__main__":
    main()
