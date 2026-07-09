package com.bettertotp.android.ui.screens

import android.content.Context
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import com.bettertotp.android.vault.Vault
import com.bettertotp.android.vault.VaultFactory
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun UnlockScreen(
    vaultType: String,
    onUnlocked: () -> Unit,
    onSwitchVaultType: () -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var password by remember { mutableStateOf("") }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var isLoading by remember { mutableStateOf(false) }
    var isCreating by remember { mutableStateOf(false) }
    var confirmPassword by remember { mutableStateOf("") }
    var showConfirm by remember { mutableStateOf(false) }

    val actualType = if (vaultType.equals("biometric", ignoreCase = true))
        Vault.Type.BIOMETRIC else Vault.Type.PASSWORD

    val vaultExists = remember {
        VaultFactory.vaultOfTypeExists(context, actualType)
    }

    LaunchedEffect(vaultType) {
        if (actualType == Vault.Type.BIOMETRIC && vaultExists) {
            triggerBiometricAuth(context, onSuccess = {
                val vault = VaultFactory.create(context, Vault.Type.BIOMETRIC)
                scope.launch {
                    vault.unlock()
                    onUnlocked()
                }
            })
        }
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Icon(
                imageVector = Icons.Default.Lock,
                contentDescription = null,
                modifier = Modifier.size(64.dp),
                tint = MaterialTheme.colorScheme.primary
            )
            Spacer(modifier = Modifier.height(16.dp))

            Text(
                text = if (vaultExists) "Unlock Vault" else "Create Vault",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(4.dp))

            Text(
                text = if (actualType == Vault.Type.PASSWORD) "Master Password" else "Biometric Authentication",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(modifier = Modifier.height(32.dp))

            if (actualType == Vault.Type.PASSWORD) {
                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it; errorMessage = null },
                    label = { Text("Master password") },
                    visualTransformation = PasswordVisualTransformation(),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    isError = errorMessage != null,
                    supportingText = errorMessage?.let { { Text(it) } }
                )

                if (showConfirm) {
                    Spacer(modifier = Modifier.height(12.dp))
                    OutlinedTextField(
                        value = confirmPassword,
                        onValueChange = { confirmPassword = it },
                        label = { Text("Confirm password") },
                        visualTransformation = PasswordVisualTransformation(),
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                }

                Spacer(modifier = Modifier.height(24.dp))

                Button(
                    onClick = {
                        if (!vaultExists) {
                            if (!showConfirm) {
                                showConfirm = true
                                return@Button
                            }
                            if (password != confirmPassword) {
                                errorMessage = "Passwords do not match"
                                return@Button
                            }
                            if (password.length < 4) {
                                errorMessage = "Password must be at least 4 characters"
                                return@Button
                            }
                        }
                        isLoading = true
                        errorMessage = null
                        val vault = VaultFactory.create(context, Vault.Type.PASSWORD)
                        scope.launch {
                            val success = if (!vaultExists) {
                                try {
                                    vault.create(password)
                                    true
                                } catch (e: Exception) {
                                    errorMessage = e.message ?: "Failed to create vault"
                                    false
                                }
                            } else {
                                vault.unlock(password)
                            }
                            isLoading = false
                            if (success) {
                                VaultFactory.setPreferredType(context, Vault.Type.PASSWORD)
                                onUnlocked()
                            } else if (errorMessage == null) {
                                errorMessage = "Wrong password"
                            }
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(48.dp),
                    enabled = password.isNotEmpty() && !isLoading
                ) {
                    if (isLoading) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(24.dp),
                            strokeWidth = 2.dp
                        )
                    } else {
                        Text(
                            if (vaultExists) "Unlock"
                            else if (showConfirm) "Create Vault"
                            else "Continue"
                        )
                    }
                }
            } else {
                if (!vaultExists) {
                    Text(
                        text = "You'll be prompted for fingerprint or PIN\nto secure your vault.",
                        style = MaterialTheme.typography.bodyMedium,
                        textAlign = TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(24.dp))
                    Button(
                        onClick = {
                            triggerBiometricAuth(
                                context,
                                isCreating = true,
                                onSuccess = {
                                    scope.launch {
                                        val vault = VaultFactory.create(context, Vault.Type.BIOMETRIC)
                                        vault.create()
                                        VaultFactory.setPreferredType(context, Vault.Type.BIOMETRIC)
                                        onUnlocked()
                                    }
                                }
                            )
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Set up biometric authentication")
                    }
                } else {
                    Button(
                        onClick = {
                            triggerBiometricAuth(context, onSuccess = {
                                scope.launch {
                                    val vault = VaultFactory.create(context, Vault.Type.BIOMETRIC)
                                    vault.unlock()
                                    onUnlocked()
                                }
                            })
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Authenticate")
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            TextButton(onClick = onSwitchVaultType) {
                Text("Use different vault type")
            }
        }
    }
}

private fun triggerBiometricAuth(
    context: Context,
    isCreating: Boolean = false,
    onSuccess: () -> Unit
) {
    val activity = context as? FragmentActivity ?: return
    val biometricManager = BiometricManager.from(context)
    when (biometricManager.canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_WEAK or BiometricManager.Authenticators.DEVICE_CREDENTIAL)) {
        BiometricManager.BIOMETRIC_SUCCESS -> {}
        BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE -> {
            return
        }
        else -> return
    }

    val promptInfo = BiometricPrompt.PromptInfo.Builder()
        .setTitle(if (isCreating) "Create biometric vault" else "Unlock vault")
        .setSubtitle("Authenticate to ${if (isCreating) "create your" else "access your"} TOTP vault")
        .setAllowedAuthenticators(
            BiometricManager.Authenticators.BIOMETRIC_WEAK or
                    BiometricManager.Authenticators.DEVICE_CREDENTIAL
        )
        .build()

    val biometricPrompt = BiometricPrompt(
        activity,
        ContextCompat.getMainExecutor(context),
        object : BiometricPrompt.AuthenticationCallback() {
            override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                val vault = VaultFactory.create(context, Vault.Type.BIOMETRIC)
                val cipher = result.cryptoObject?.cipher
                if (cipher != null) {
                    (vault as? com.bettertotp.android.vault.BiometricVault)?.setCipherFromBiometric(cipher)
                }
                onSuccess()
            }
        }
    )

    if (isCreating) {
        val vault = VaultFactory.create(context, Vault.Type.BIOMETRIC) as? com.bettertotp.android.vault.BiometricVault
        val cipher = vault?.getCipherForBiometric()
        if (cipher != null) {
            biometricPrompt.authenticate(promptInfo, BiometricPrompt.CryptoObject(cipher))
            vault.setCipherFromBiometric(cipher)
        }
    } else {
        val vault = VaultFactory.create(context, Vault.Type.BIOMETRIC) as? com.bettertotp.android.vault.BiometricVault
        try {
            val cipher = vault?.getCipherForDecryption()
            if (cipher != null) {
                biometricPrompt.authenticate(promptInfo, BiometricPrompt.CryptoObject(cipher))
                vault.setCipherFromBiometric(cipher)
            }
        } catch (e: Exception) {
            biometricPrompt.authenticate(promptInfo)
        }
    }
}
