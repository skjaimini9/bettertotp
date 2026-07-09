package com.bettertotp.android.ui.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import com.bettertotp.android.ui.screens.AccountDetailScreen
import com.bettertotp.android.ui.screens.AddAccountScreen
import com.bettertotp.android.ui.screens.MainScreen
import com.bettertotp.android.ui.screens.SettingsScreen
import com.bettertotp.android.ui.screens.UnlockScreen
import com.bettertotp.android.ui.screens.WelcomeScreen
import com.bettertotp.android.vault.Vault

object Routes {
    const val WELCOME = "welcome"
    const val UNLOCK = "unlock/{vaultType}"
    const val MAIN = "main"
    const val ADD_ACCOUNT = "add_account"
    const val ACCOUNT_DETAIL = "account_detail/{accountName}"
    const val SETTINGS = "settings"

    fun unlock(vaultType: String) = "unlock/$vaultType"
    fun accountDetail(accountName: String) = "account_detail/$accountName"
}

@Composable
fun BetterTOTPNavGraph(
    navController: NavHostController,
    startDestination: String
) {
    NavHost(navController = navController, startDestination = startDestination) {
        composable(Routes.WELCOME) {
            WelcomeScreen(
                onVaultTypeSelected = { type ->
                    navController.navigate(Routes.unlock(type.name.lowercase()))
                }
            )
        }
        composable(
            route = Routes.UNLOCK,
            arguments = listOf(navArgument("vaultType") { type = NavType.StringType })
        ) { backStackEntry ->
            val vaultType = backStackEntry.arguments?.getString("vaultType") ?: "password"
            UnlockScreen(
                vaultType = vaultType,
                onUnlocked = {
                    navController.navigate(Routes.MAIN) {
                        popUpTo(Routes.WELCOME) { inclusive = true }
                    }
                },
                onSwitchVaultType = {
                    navController.popBackStack(Routes.WELCOME, inclusive = false)
                }
            )
        }
        composable(Routes.MAIN) {
            MainScreen(
                onAddAccount = { navController.navigate(Routes.ADD_ACCOUNT) },
                onAccountClick = { name -> navController.navigate(Routes.accountDetail(name)) },
                onSettings = { navController.navigate(Routes.SETTINGS) }
            )
        }
        composable(Routes.ADD_ACCOUNT) {
            AddAccountScreen(
                onNavigateBack = { navController.popBackStack() }
            )
        }
        composable(
            route = Routes.ACCOUNT_DETAIL,
            arguments = listOf(navArgument("accountName") { type = NavType.StringType })
        ) { backStackEntry ->
            val accountName = backStackEntry.arguments?.getString("accountName") ?: ""
            AccountDetailScreen(
                accountName = accountName,
                onNavigateBack = { navController.popBackStack() }
            )
        }
        composable(Routes.SETTINGS) {
            SettingsScreen(
                onNavigateBack = { navController.popBackStack() },
                onLogout = {
                    navController.navigate(Routes.WELCOME) {
                        popUpTo(0) { inclusive = true }
                    }
                }
            )
        }
    }
}
