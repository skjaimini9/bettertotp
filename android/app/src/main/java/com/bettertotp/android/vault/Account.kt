package com.bettertotp.android.vault

data class Account(
    val name: String,
    val secret: String,
    val issuer: String = "",
    val algorithm: String = "sha512",
    val digits: Int = 12,
    val period: Int = 45
) {
    fun toMap(): Map<String, Any> = mapOf(
        "secret" to secret,
        "issuer" to issuer,
        "algorithm" to algorithm,
        "digits" to digits,
        "period" to period
    )

    companion object {
        fun fromMap(name: String, map: Map<String, Any>): Account {
            return Account(
                name = name,
                secret = map["secret"] as? String ?: "",
                issuer = map["issuer"] as? String ?: "",
                algorithm = map["algorithm"] as? String ?: "sha512",
                digits = (map["digits"] as? Number)?.toInt() ?: 12,
                period = (map["period"] as? Number)?.toInt() ?: 45
            )
        }
    }
}
