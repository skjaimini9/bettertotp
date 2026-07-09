package com.bettertotp.android.totp

import java.security.InvalidKeyException
import java.security.NoSuchAlgorithmException
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

object TOTPGenerator {

    private val ALGO_MAP = mapOf(
        "sha1" to "HmacSHA1",
        "sha256" to "HmacSHA256",
        "sha512" to "HmacSHA512"
    )

    private const val DEFAULT_TIME_STEP = 45L
    private const val DEFAULT_CODE_LENGTH = 12
    private const val DEFAULT_HASH_ALGO = "sha512"

    fun generateCode(
        keyBytes: ByteArray,
        t: Long? = null,
        algorithm: String = DEFAULT_HASH_ALGO,
        codeLength: Int = DEFAULT_CODE_LENGTH,
        timeStep: Long = DEFAULT_TIME_STEP
    ): String {
        val counter = timeCounter(t, timeStep)
        return hotp(keyBytes, counter, algorithm, codeLength)
    }

    fun generateCodeAt(
        keyBytes: ByteArray,
        timestamp: Long,
        algorithm: String = DEFAULT_HASH_ALGO,
        codeLength: Int = DEFAULT_CODE_LENGTH,
        timeStep: Long = DEFAULT_TIME_STEP
    ): String {
        return totp(keyBytes, timestamp, algorithm, codeLength, timeStep)
    }

    fun verifyCode(
        keyBytes: ByteArray,
        code: String,
        window: Int = 1,
        algorithm: String = DEFAULT_HASH_ALGO,
        codeLength: Int = DEFAULT_CODE_LENGTH,
        timeStep: Long = DEFAULT_TIME_STEP
    ): Boolean {
        val currentCounter = timeCounter(timeStep = timeStep)
        for (offset in -window..window) {
            val candidate = hotp(keyBytes, currentCounter + offset, algorithm, codeLength)
            if (candidate == code) return true
        }
        return false
    }

    fun totp(
        keyBytes: ByteArray,
        t: Long? = null,
        algorithm: String = DEFAULT_HASH_ALGO,
        codeLength: Int = DEFAULT_CODE_LENGTH,
        timeStep: Long = DEFAULT_TIME_STEP
    ): String {
        val counter = timeCounter(t, timeStep)
        return hotp(keyBytes, counter, algorithm, codeLength)
    }

    fun hotp(
        keyBytes: ByteArray,
        counter: Long,
        algorithm: String = DEFAULT_HASH_ALGO,
        codeLength: Int = DEFAULT_CODE_LENGTH
    ): String {
        val hashBytes = hmac(keyBytes, counter, algorithm)
        return CharsetEncoder.encode(hashBytes, codeLength)
    }

    private fun timeCounter(t: Long?, timeStep: Long): Long {
        val now = t ?: (System.currentTimeMillis() / 1000L)
        return now / timeStep
    }

    private fun hmac(keyBytes: ByteArray, counter: Long, algorithm: String): ByteArray {
        val algoName = ALGO_MAP[algorithm] ?: throw IllegalArgumentException("Unknown algorithm: $algorithm")
        val mac = Mac.getInstance(algoName)
        val keySpec = SecretKeySpec(keyBytes, algoName)
        mac.init(keySpec)

        val msg = ByteArray(8)
        var c = counter
        for (i in 7 downTo 0) {
            msg[i] = (c and 0xFF).toByte()
            c = c shr 8
        }
        return mac.doFinal(msg)
    }

    fun getDefaultTimeStep(): Long = DEFAULT_TIME_STEP
    fun getDefaultCodeLength(): Int = DEFAULT_CODE_LENGTH
    fun getDefaultHashAlgo(): String = DEFAULT_HASH_ALGO
}
