# Keep data classes for Gson/JSON
-keep class com.bettertotp.android.vault.Account { *; }

# Keep cryptography related
-keep class javax.crypto.** { *; }
-keep class android.security.keystore.** { *; }
