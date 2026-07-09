package com.bettertotp.android.vault

import android.content.Context

object VaultFactory {

    private const val PREFS_NAME = "btotp_settings"
    private const val KEY_VAULT_TYPE = "vault_type"

    fun getPreferredType(context: Context): Vault.Type? {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val name = prefs.getString(KEY_VAULT_TYPE, null) ?: return null
        return try {
            Vault.Type.valueOf(name)
        } catch (e: IllegalArgumentException) {
            null
        }
    }

    fun setPreferredType(context: Context, type: Vault.Type) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().putString(KEY_VAULT_TYPE, type.name).apply()
    }

    fun create(context: Context, type: Vault.Type): Vault {
        return when (type) {
            Vault.Type.PASSWORD -> PasswordVault(context)
            Vault.Type.BIOMETRIC -> BiometricVault(context)
        }
    }

    fun passwordVaultExists(context: Context): Boolean {
        val prefs = androidx.security.crypto.EncryptedSharedPreferences.create(
            "btotp_vault_prefs",
            androidx.security.crypto.MasterKeys.getOrCreate(androidx.security.crypto.MasterKeys.AES256_GCM_SPEC),
            context,
            androidx.security.crypto.EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            androidx.security.crypto.EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
        return prefs.contains("vault_data")
    }

    fun biometricVaultExists(context: Context): Boolean {
        val prefs = androidx.security.crypto.EncryptedSharedPreferences.create(
            "btotp_biometric_vault",
            androidx.security.crypto.MasterKeys.getOrCreate(androidx.security.crypto.MasterKeys.AES256_GCM_SPEC),
            context,
            androidx.security.crypto.EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            androidx.security.crypto.EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
        return prefs.contains("vault_data")
    }

    fun vaultOfTypeExists(context: Context, type: Vault.Type): Boolean {
        return when (type) {
            Vault.Type.PASSWORD -> passwordVaultExists(context)
            Vault.Type.BIOMETRIC -> biometricVaultExists(context)
        }
    }
}
