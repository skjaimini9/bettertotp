package com.bettertotp.android.util

import android.util.Base64
import java.security.spec.KeySpec
import javax.crypto.Cipher
import javax.crypto.SecretKey
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.PBEKeySpec
import javax.crypto.spec.SecretKeySpec

object CryptoUtils {

    private const val PBKDF2_ITERATIONS = 600_000
    private const val AES_KEY_LENGTH = 256
    private const val GCM_NONCE_LENGTH = 12
    private const val GCM_TAG_LENGTH = 128

    fun deriveKey(password: String, salt: ByteArray): SecretKey {
        val factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
        val spec: KeySpec = PBEKeySpec(password.toCharArray(), salt, PBKDF2_ITERATIONS, AES_KEY_LENGTH)
        val tmp = factory.generateSecret(spec)
        return SecretKeySpec(tmp.encoded, "AES")
    }

    fun aesGcmEncrypt(plaintext: String, password: String): String {
        val salt = ByteArray(16).also { java.security.SecureRandom().nextBytes(it) }
        val nonce = ByteArray(GCM_NONCE_LENGTH).also { java.security.SecureRandom().nextBytes(it) }
        val key = deriveKey(password, salt)

        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        val spec = GCMParameterSpec(GCM_TAG_LENGTH, nonce)
        cipher.init(Cipher.ENCRYPT_MODE, key, spec)
        val ciphertext = cipher.doFinal(plaintext.toByteArray(Charsets.UTF_8))

        val payload = mapOf(
            "version" to 1,
            "salt" to Base64.encodeToString(salt, Base64.DEFAULT),
            "nonce" to Base64.encodeToString(nonce, Base64.DEFAULT),
            "data" to Base64.encodeToString(ciphertext, Base64.DEFAULT)
        )
        val json = org.json.JSONObject(payload).toString()
        return Base64.encodeToString(json.toByteArray(), Base64.DEFAULT)
    }

    fun aesGcmDecrypt(encryptedBase64: String, password: String): String {
        val jsonBytes = Base64.decode(encryptedBase64, Base64.DEFAULT)
        val jsonStr = String(jsonBytes, Charsets.UTF_8)
        val payload = org.json.JSONObject(jsonStr)

        val salt = Base64.decode(payload.getString("salt"), Base64.DEFAULT)
        val nonce = Base64.decode(payload.getString("nonce"), Base64.DEFAULT)
        val data = Base64.decode(payload.getString("data"), Base64.DEFAULT)

        val key = deriveKey(password, salt)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        val spec = GCMParameterSpec(GCM_TAG_LENGTH, nonce)
        cipher.init(Cipher.DECRYPT_MODE, key, spec)
        val plaintext = cipher.doFinal(data)
        return String(plaintext, Charsets.UTF_8)
    }

    fun hexToBytes(hex: String): ByteArray {
        val cleaned = hex.replace(" ", "")
        return ByteArray(cleaned.length / 2) {
            cleaned.substring(it * 2, it * 2 + 2).toInt(16).toByte()
        }
    }

    fun bytesToHex(bytes: ByteArray): String = bytes.joinToString("") { "%02x".format(it) }
}
