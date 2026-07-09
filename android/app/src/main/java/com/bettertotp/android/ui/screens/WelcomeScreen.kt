package com.bettertotp.android.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.bettertotp.android.vault.Vault

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WelcomeScreen(
    onVaultTypeSelected: (Vault.Type) -> Unit
) {
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Text(
                text = "BetterTOTP",
                fontSize = 32.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "Time-based one-time passwords\nalphanumeric + special characters",
                style = MaterialTheme.typography.bodyMedium,
                textAlign = TextAlign.Center,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(modifier = Modifier.height(48.dp))
            Text(
                text = "Choose your vault type",
                style = MaterialTheme.typography.titleMedium
            )
            Spacer(modifier = Modifier.height(24.dp))

            Button(
                onClick = { onVaultTypeSelected(Vault.Type.PASSWORD) },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp),
                shape = MaterialTheme.shapes.medium
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("Master Password", fontWeight = FontWeight.SemiBold)
                    Text(
                        "PBKDF2 + AES-256-GCM encrypted",
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            OutlinedButton(
                onClick = { onVaultTypeSelected(Vault.Type.BIOMETRIC) },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp),
                shape = MaterialTheme.shapes.medium
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("Biometric", fontWeight = FontWeight.SemiBold)
                    Text(
                        "Android Keystore + fingerprint/PIN",
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        }
    }
}
