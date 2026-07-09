package com.bettertotp.android.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.bettertotp.android.vault.Account
import com.bettertotp.android.vault.VaultFactory
import com.bettertotp.android.util.CryptoUtils
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddAccountScreen(
    onNavigateBack: () -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var name by remember { mutableStateOf("") }
    var secret by remember { mutableStateOf("") }
    var issuer by remember { mutableStateOf("") }
    var algorithm by remember { mutableStateOf("sha512") }
    var digits by remember { mutableStateOf("12") }
    var period by remember { mutableStateOf("45") }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var isSaving by remember { mutableStateOf(false) }

    val vaultType = remember { VaultFactory.getPreferredType(context) }
    val vault = remember {
        vaultType?.let { VaultFactory.create(context, it) }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Add Account") },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(24.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            OutlinedTextField(
                value = name,
                onValueChange = { name = it; errorMessage = null },
                label = { Text("Account name *") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )

            OutlinedTextField(
                value = secret,
                onValueChange = { secret = it },
                label = { Text("Secret (hex)") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )

            OutlinedTextField(
                value = issuer,
                onValueChange = { issuer = it },
                label = { Text("Issuer (optional)") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )

            Text(
                text = "Algorithm",
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.SemiBold
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("sha1", "sha256", "sha512").forEach { algo ->
                    FilterChip(
                        selected = algorithm == algo,
                        onClick = { algorithm = algo },
                        label = { Text(algo.uppercase()) }
                    )
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                OutlinedTextField(
                    value = digits,
                    onValueChange = { digits = it },
                    label = { Text("Digits") },
                    modifier = Modifier.weight(1f),
                    singleLine = true
                )
                OutlinedTextField(
                    value = period,
                    onValueChange = { period = it },
                    label = { Text("Period (s)") },
                    modifier = Modifier.weight(1f),
                    singleLine = true
                )
            }

            if (errorMessage != null) {
                Text(
                    text = errorMessage ?: "",
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            Button(
                onClick = {
                    if (name.isBlank()) {
                        errorMessage = "Account name is required"
                        return@Button
                    }
                    if (secret.isBlank()) {
                        errorMessage = "Secret is required"
                        return@Button
                    }
                    isSaving = true
                    errorMessage = null

                    scope.launch {
                        try {
                            val account = Account(
                                name = name.trim(),
                                secret = try {
                                    CryptoUtils.hexToBytes(secret.trim()).joinToString("") { "%02x".format(it) }
                                } catch (e: Exception) {
                                    secret.trim()
                                },
                                issuer = issuer.trim(),
                                algorithm = algorithm,
                                digits = digits.toIntOrNull() ?: 12,
                                period = period.toIntOrNull() ?: 45
                            )
                            vault?.add(account)
                            onNavigateBack()
                        } catch (e: Exception) {
                            errorMessage = e.message ?: "Failed to add account"
                        } finally {
                            isSaving = false
                        }
                    }
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp),
                enabled = !isSaving
            ) {
                if (isSaving) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(24.dp),
                        strokeWidth = 2.dp
                    )
                } else {
                    Text("Add Account")
                }
            }
        }
    }
}
