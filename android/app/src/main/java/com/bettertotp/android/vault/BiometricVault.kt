package com.bettertotp.android.vault

import android.content.Context
import android.content.SharedPreferences
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKeys
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class BiometricVault(private val context: Context) : Vault {

    override val type = Vault.Type.BIOMETRIC
    override var isLocked: Boolean = true
        private set

    private var cipher: Cipher? = null
    private var accounts: MutableMap<String, Account> = mutableMapOf()

    private companion object {
        private const val KEYSTORE_ALIAS = "btotp_biometric_key"
        private const val ANDROID_KEYSTORE = "AndroidKeyStore"
        private const val PREFS_NAME = "btotp_biometric_vault"

        // Global shared prefs for encrypted data storage
        fun getPrefs(context: Context): SharedPreferences {
            val masterKeyAlias = MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC)
            return EncryptedSharedPreferences.create(
                PREFS_NAME,
                masterKeyAlias,
                context,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )
        }
    }

    private val prefs: SharedPreferences by lazy { getPrefs(context) }

    fun getCipherForBiometric(): Cipher {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE)
        keyStore.load(null)
        val secretKey = keyStore.getKey(KEYSTORE_ALIAS, null) as? SecretKey
            ?: throw IllegalStateException("Biometric key not found. Create vault first.")
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, secretKey)
        return cipher
    }

    fun getCipherForDecryption(): Cipher {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE)
        keyStore.load(null)
        val secretKey = keyStore.getKey(KEYSTORE_ALIAS, null) as? SecretKey
            ?: throw IllegalStateException("Biometric key not found.")
        val iv = prefs.getString("biometric_iv", null)
            ?: throw IllegalStateException("IV not found in prefs.")
        val ivBytes = android.util.Base64.decode(iv, android.util.Base64.DEFAULT)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        val spec = GCMParameterSpec(128, ivBytes)
        cipher.init(Cipher.DECRYPT_MODE, secretKey, spec)
        return cipher
    }

    fun setCipherFromBiometric(cipher: Cipher) {
        this.cipher = cipher
    }

    override suspend fun unlock(credential: String?): Boolean = withContext(Dispatchers.IO) {
        val c = cipher ?: return@withContext false
        try {
            val encryptedData = prefs.getString("vault_data", null) ?: return@withContext false
            val encryptedBytes = android.util.Base64.decode(encryptedData, android.util.Base64.DEFAULT)
            val decryptedBytes = c.doFinal(encryptedBytes)
            val plaintext = String(decryptedBytes, Charsets.UTF_8)
            val json = JSONObject(plaintext)
            val accountsObj = json.optJSONObject("accounts") ?: JSONObject()
            accounts.clear()
            for (key in accountsObj.keys()) {
                val accJson = accountsObj.getJSONObject(key)
                val accMap = mutableMapOf<String, Any>()
                accMap["secret"] = accJson.getString("secret")
                accMap["issuer"] = accJson.optString("issuer", "")
                accMap["algorithm"] = accJson.optString("algorithm", "sha512")
                accMap["digits"] = accJson.optInt("digits", 12)
                accMap["period"] = accJson.optInt("period", 45)
                accounts[key] = Account.fromMap(key, accMap)
            }
            isLocked = false
            this@BiometricVault.cipher = null
            true
        } catch (e: Exception) {
            this@BiometricVault.cipher = null
            false
        }
    }

    override suspend fun lock() {
        accounts.clear()
        cipher = null
        isLocked = true
    }

    override suspend fun create(credential: String?): Unit = withContext(Dispatchers.IO) {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE)
        keyStore.load(null)

        val keyGenerator = KeyGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_AES,
            ANDROID_KEYSTORE
        )
        val spec = KeyGenParameterSpec.Builder(
            KEYSTORE_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setUserAuthenticationRequired(true)
            .setInvalidatedByBiometricEnrollment(true)
            .build()
        keyGenerator.init(spec)
        keyGenerator.generateKey()

        accounts.clear()
        saveWithKey()
        isLocked = false
    }

    private fun saveWithKey() {
        val json = JSONObject()
        val accountsObj = JSONObject()
        for ((name, acc) in accounts) {
            accountsObj.put(name, JSONObject(acc.toMap()))
        }
        json.put("accounts", accountsObj)
        val plaintext = json.toString()

        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE)
        keyStore.load(null)
        val secretKey = keyStore.getKey(KEYSTORE_ALIAS, null) as SecretKey
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, secretKey)
        val encryptedBytes = cipher.doFinal(plaintext.toByteArray(Charsets.UTF_8))
        val iv = android.util.Base64.encodeToString(cipher.iv, android.util.Base64.DEFAULT)

        prefs.edit()
            .putString("vault_data", android.util.Base64.encodeToString(encryptedBytes, android.util.Base64.DEFAULT))
            .putString("biometric_iv", iv)
            .apply()
    }

    override suspend fun add(account: Account) {
        if (isLocked) throw IllegalStateException("Vault is locked")
        if (accounts.containsKey(account.name)) throw IllegalArgumentException("Account '${account.name}' already exists")
        accounts[account.name] = account
        saveIfUnlocked()
    }

    override suspend fun remove(name: String) {
        if (isLocked) throw IllegalStateException("Vault is locked")
        if (!accounts.containsKey(name)) throw IllegalArgumentException("Account '$name' not found")
        accounts.remove(name)
        saveIfUnlocked()
    }

    override suspend fun rename(oldName: String, newName: String) {
        if (isLocked) throw IllegalStateException("Vault is locked")
        val acc = accounts[oldName] ?: throw IllegalArgumentException("Account '$oldName' not found")
        if (accounts.containsKey(newName)) throw IllegalArgumentException("Account '$newName' already exists")
        accounts.remove(oldName)
        accounts[newName] = acc.copy(name = newName)
        saveIfUnlocked()
    }

    override suspend fun get(name: String): Account? = accounts[name]

    override suspend fun list(): List<Account> = accounts.values.sortedBy { it.name }

    override suspend fun code(name: String): String? {
        val acc = accounts[name] ?: return null
        return withContext(Dispatchers.Default) {
            val secretBytes = hexStringToByteArray(acc.secret)
            com.bettertotp.android.totp.TOTPGenerator.generateCode(
                secretBytes,
                algorithm = acc.algorithm,
                codeLength = acc.digits,
                timeStep = acc.period.toLong()
            )
        }
    }

    private fun saveIfUnlocked() {
        if (!isLocked) saveWithKey()
    }

    fun vaultExists(): Boolean = prefs.contains("vault_data")

    private fun hexStringToByteArray(s: String): ByteArray {
        val cleaned = s.replace(" ", "")
        return ByteArray(cleaned.length / 2) {
            cleaned.substring(it * 2, it * 2 + 2).toInt(16).toByte()
        }
    }
}
