package com.bettertotp.android.totp

object TOTPVerifier {

    fun verify(
        keyBytes: ByteArray,
        code: String,
        window: Int = 1,
        algorithm: String = "sha512",
        codeLength: Int = 12,
        timeStep: Long = 45L
    ): Boolean {
        return TOTPGenerator.verifyCode(keyBytes, code, window, algorithm, codeLength, timeStep)
    }

    fun isValidCodeFormat(code: String): Boolean {
        if (code.isEmpty()) return false
        val charset = (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ" +
            "abcdefghijklmnopqrstuvwxyz" +
            "0123456789" +
            "!@#\$%&*-_+=?~"
        )
        return code.all { it in charset }
    }
}
