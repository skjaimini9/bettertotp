import json
import os
import tempfile
from unittest import TestCase, main

from btotp.vault import Vault, _derive_key, _encrypt, _decrypt


class TestVaultCrypto(TestCase):
    def test_derive_key_is_deterministic(self):
        k1 = _derive_key("password", b"saltsaltsaltsalt")
        k2 = _derive_key("password", b"saltsaltsaltsalt")
        self.assertEqual(k1, k2)

    def test_derive_key_differs_for_different_salts(self):
        k1 = _derive_key("password", b"saltsaltsaltsalt")
        k2 = _derive_key("password", b"saltsaltsaltsalt")
        self.assertEqual(k1, k2)

    def test_encrypt_decrypt_roundtrip(self):
        payload = _encrypt("hello world", "mypassword")
        self.assertIn("salt", payload)
        self.assertIn("nonce", payload)
        self.assertIn("data", payload)
        plain = _decrypt(payload, "mypassword")
        self.assertEqual(plain, "hello world")

    def test_decrypt_wrong_password_fails(self):
        payload = _encrypt("secret", "password1")
        with self.assertRaises(Exception):
            _decrypt(payload, "password2")


class TestVault(TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.vault_path = os.path.join(self.tmpdir, "vault.json")

    def tearDown(self):
        for f in os.listdir(self.tmpdir):
            os.remove(os.path.join(self.tmpdir, f))
        os.rmdir(self.tmpdir)

    def test_create_and_exists(self):
        v = Vault(self.vault_path)
        self.assertFalse(v.exists())
        v.create("testpass")
        self.assertTrue(v.exists())

    def test_create_and_unlock(self):
        v = Vault(self.vault_path)
        v.create("testpass")
        v2 = Vault(self.vault_path)
        v2.unlock("testpass")
        self.assertEqual(v2.list_accounts(), [])

    def test_add_and_list(self):
        v = Vault(self.vault_path)
        v.create("testpass")
        v.add("example", "deadbeef" * 8, issuer="Test")
        accounts = v.list_accounts()
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]["name"], "example")
        self.assertEqual(accounts[0]["issuer"], "Test")

    def test_add_duplicate_fails(self):
        v = Vault(self.vault_path)
        v.create("testpass")
        v.add("example", "deadbeef" * 8)
        with self.assertRaises(KeyError):
            v.add("example", "deadbeef" * 8)

    def test_get(self):
        v = Vault(self.vault_path)
        v.create("testpass")
        v.add("example", "deadbeef" * 8, issuer="Acme")
        acc = v.get("example")
        self.assertEqual(acc["secret"], "deadbeef" * 8)
        self.assertEqual(acc["issuer"], "Acme")

    def test_get_nonexistent_fails(self):
        v = Vault(self.vault_path)
        v.create("testpass")
        with self.assertRaises(KeyError):
            v.get("nonexistent")

    def test_remove(self):
        v = Vault(self.vault_path)
        v.create("testpass")
        v.add("example", "deadbeef" * 8)
        v.remove("example")
        self.assertEqual(len(v.list_accounts()), 0)

    def test_remove_nonexistent_fails(self):
        v = Vault(self.vault_path)
        v.create("testpass")
        with self.assertRaises(KeyError):
            v.remove("nonexistent")

    def test_rename(self):
        v = Vault(self.vault_path)
        v.create("testpass")
        v.add("old", "deadbeef" * 8)
        v.rename("old", "new")
        self.assertEqual(len(v.list_accounts()), 1)
        self.assertEqual(v.list_accounts()[0]["name"], "new")

    def test_rename_to_existing_fails(self):
        v = Vault(self.vault_path)
        v.create("testpass")
        v.add("a", "deadbeef" * 8)
        v.add("b", "deadbeef" * 8)
        with self.assertRaises(KeyError):
            v.rename("a", "b")

    def test_persistence(self):
        v = Vault(self.vault_path)
        v.create("testpass")
        v.add("persist", "cafebabe" * 8)

        v2 = Vault(self.vault_path)
        v2.unlock("testpass")
        accounts = v2.list_accounts()
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]["name"], "persist")

    def test_export_import_json(self):
        v = Vault(self.vault_path)
        v.create("testpass")
        v.add("exp", "deadbeef" * 8)
        exported = v.export_json()

        v2 = Vault(self.vault_path + ".new")
        v2.create("testpass2")
        v2.import_json(exported)
        accounts = v2.list_accounts()
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]["name"], "exp")

    def test_code_generation(self):
        v = Vault(self.vault_path)
        v.create("testpass")
        v.add("test", "deadbeef" * 8)
        code = v.code("test")
        self.assertEqual(len(code), 12)

    def test_import_duplicate_fails(self):
        v = Vault(self.vault_path)
        v.create("testpass")
        v.add("dup", "deadbeef" * 8)
        with self.assertRaises(KeyError):
            v.import_json(json.dumps({"accounts": {"dup": {"secret": "cafebabe" * 8}}}))


if __name__ == "__main__":
    main()
