package com.bettertotp.android.vault

sealed interface Vault {
    enum class Type { PASSWORD, BIOMETRIC }

    val type: Type
    val isLocked: Boolean

    suspend fun unlock(credential: String? = null): Boolean
    suspend fun lock()
    suspend fun create(credential: String? = null)

    suspend fun add(account: Account)
    suspend fun remove(name: String)
    suspend fun rename(oldName: String, newName: String)
    suspend fun get(name: String): Account?
    suspend fun list(): List<Account>
    suspend fun code(name: String): String?
}
