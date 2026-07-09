package com.bettertotp.android

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.navigation.compose.rememberNavController
import com.bettertotp.android.ui.navigation.BetterTOTPNavGraph
import com.bettertotp.android.ui.navigation.Routes
import com.bettertotp.android.ui.theme.BetterTOTPTheme
import com.bettertotp.android.vault.VaultFactory

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            BetterTOTPTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    val navController = rememberNavController()
                    val startDestination = remember {
                        val preferredType = VaultFactory.getPreferredType(this@MainActivity)
                        if (preferredType != null && VaultFactory.vaultOfTypeExists(this@MainActivity, preferredType)) {
                            Routes.unlock(preferredType.name.lowercase())
                        } else {
                            Routes.WELCOME
                        }
                    }

                    BetterTOTPNavGraph(
                        navController = navController,
                        startDestination = startDestination
                    )
                }
            }
        }
    }
}
