package com.bettertotp.android.vault

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKeys
import com.bettertotp.android.util.CryptoUtils
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

class PasswordVault(private val context: Context) : Vault {

    override val type = Vault.Type.PASSWORD
    override var isLocked: Boolean = true
        private set

    private var password: String? = null
    private var accounts: MutableMap<String, Account> = mutableMapOf()

    private val prefs: SharedPreferences by lazy {
        val masterKeyAlias = MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC)
        EncryptedSharedPreferences.create(
            "btotp_vault_prefs",
            masterKeyAlias,
            context,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    override suspend fun unlock(credential: String?): Boolean = withContext(Dispatchers.IO) {
        val pw = credential ?: return@withContext false
        val encryptedData = prefs.getString("vault_data", null) ?: return@withContext false
        password = pw
        return@withContext try {
            val decrypted = CryptoUtils.aesGcmDecrypt(encryptedData, pw)
            val json = JSONObject(decrypted)
            val accountsObj = json.optJSONObject("accounts") ?: JSONObject()
            accounts.clear()
            for (key in accountsObj.keys()) {
                val accMap = mutableMapOf<String, Any>()
                val accJson = accountsObj.getJSONObject(key)
                accMap["secret"] = accJson.getString("secret")
                accMap["issuer"] = accJson.optString("issuer", "")
                accMap["algorithm"] = accJson.optString("algorithm", "sha512")
                accMap["digits"] = accJson.optInt("digits", 12)
                accMap["period"] = accJson.optInt("period", 45)
                accounts[key] = Account.fromMap(key, accMap)
            }
            isLocked = false
            true
        } catch (e: Exception) {
            password = null
            false
        }
    }

    override suspend fun lock() {
        password = null
        accounts.clear()
        isLocked = true
    }

    override suspend fun create(credential: String?): Unit = withContext(Dispatchers.IO) {
        val pw = credential ?: throw IllegalArgumentException("Password required")
        password = pw
        accounts.clear()
        save()
        isLocked = false
    }

    override suspend fun add(account: Account) {
        if (isLocked) throw IllegalStateException("Vault is locked")
        if (accounts.containsKey(account.name)) throw IllegalArgumentException("Account '${account.name}' already exists")
        accounts[account.name] = account
        save()
    }

    override suspend fun remove(name: String) {
        if (isLocked) throw IllegalStateException("Vault is locked")
        if (!accounts.containsKey(name)) throw IllegalArgumentException("Account '$name' not found")
        accounts.remove(name)
        save()
    }

    override suspend fun rename(oldName: String, newName: String) {
        if (isLocked) throw IllegalStateException("Vault is locked")
        val acc = accounts[oldName] ?: throw IllegalArgumentException("Account '$oldName' not found")
        if (accounts.containsKey(newName)) throw IllegalArgumentException("Account '$newName' already exists")
        accounts.remove(oldName)
        accounts[newName] = acc.copy(name = newName)
        save()
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

    private fun save() {
        val json = JSONObject()
        val accountsObj = JSONObject()
        for ((name, acc) in accounts) {
            accountsObj.put(name, JSONObject(acc.toMap()))
        }
        json.put("accounts", accountsObj)
        val plaintext = json.toString()
        val encrypted = CryptoUtils.aesGcmEncrypt(plaintext, password ?: return)
        prefs.edit().putString("vault_data", encrypted).apply()
    }

    private fun hexStringToByteArray(s: String): ByteArray {
        val cleaned = s.replace(" ", "")
        return ByteArray(cleaned.length / 2) {
            cleaned.substring(it * 2, it * 2 + 2).toInt(16).toByte()
        }
    }
}
