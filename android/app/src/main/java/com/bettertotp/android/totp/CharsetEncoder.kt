package com.bettertotp.android.totp

object CharsetEncoder {

    private val CHARSET = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ" +
        "abcdefghijklmnopqrstuvwxyz" +
        "0123456789" +
        "!@#\$%&*-_+=?~"
    ).toCharArray()

    private val CHARSET_SIZE = CHARSET.size

    fun encode(hashBytes: ByteArray, length: Int = 12): String {
        val result = CharArray(length)
        for (i in 0 until length) {
            val low = hashBytes[i % hashBytes.size].toInt() and 0xFF
            val high = hashBytes[(i + 1) % hashBytes.size].toInt() and 0xFF
            val idx = (low + high * 256) % CHARSET_SIZE
            result[i] = CHARSET[idx]
        }
        return String(result)
    }
}
