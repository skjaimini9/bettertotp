/*
 * pam_btotp.c - PAM module for BetterTOTP 2FA authentication
 *
 * This PAM module verifies TOTP codes using BetterTOTP's non-standard algorithm:
 *   - HMAC-SHA512 (default)
 *   - 75-character alphabet: A-Z a-z 0-9 !@#$%&*-_+=?~
 *   - 12-character codes
 *   - 45-second time steps
 *
 * Usage in /etc/pam.d/sshd:
 *   auth required pam_btotp.so nullok
 *
 * The module reads the secret from ~/.btotp (hex string, one line).
 * This file is created by: btotp enroll <account-name>
 *
 * Copyright (c) 2024 Shri Kant - MIT License
 */

#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <limits.h>
#include <pwd.h>
#include <security/pam_modules.h>
#include <security/pam_ext.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <syslog.h>
#include <time.h>
#include <unistd.h>

/* BetterTOTP defaults */
#define BTOTP_DEFAULT_TIME_STEP 45
#define BTOTP_DEFAULT_CODE_LENGTH 12
#define BTOTP_DEFAULT_WINDOW 1

/* BetterTOTP 75-character alphabet */
static const char CHARSET[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    "!@#$%&*-_+=?~";
#define CHARSET_SIZE 75

/* Module argument names */
#define ARG_NULLOK     "nullok"
#define ARG_DEBUG      "debug"
#define ARG_SECRET     "secret="
#define ARG_WINDOW     "window="
#define ARG_TIME_STEP  "time_step="
#define ARG_CODE_LENGTH "code_length="

/* Default secret file path */
#define DEFAULT_SECRET_PATH "~/.btotp"
#define MAX_SECRET_LEN 256

/*
 * HMAC-SHA512 implementation using OpenSSL
 */
#include <openssl/hmac.h>
#include <openssl/evp.h>

/*
 * Parse module arguments
 */
typedef struct {
    int nullok;
    int debug;
    char secret_path[PATH_MAX];
    int window;
    int time_step;
    int code_length;
} btotp_args_t;

static void parse_args(int argc, const char **argv, btotp_args_t *args) {
    /* Defaults */
    args->nullok = 0;
    args->debug = 0;
    strncpy(args->secret_path, DEFAULT_SECRET_PATH, PATH_MAX - 1);
    args->secret_path[PATH_MAX - 1] = '\0';
    args->window = BTOTP_DEFAULT_WINDOW;
    args->time_step = BTOTP_DEFAULT_TIME_STEP;
    args->code_length = BTOTP_DEFAULT_CODE_LENGTH;

    for (int i = 0; i < argc; i++) {
        if (strcmp(argv[i], ARG_NULLOK) == 0) {
            args->nullok = 1;
        } else if (strcmp(argv[i], ARG_DEBUG) == 0) {
            args->debug = 1;
        } else if (strncmp(argv[i], ARG_SECRET, strlen(ARG_SECRET)) == 0) {
            strncpy(args->secret_path, argv[i] + strlen(ARG_SECRET), PATH_MAX - 1);
            args->secret_path[PATH_MAX - 1] = '\0';
        } else if (strncmp(argv[i], ARG_WINDOW, strlen(ARG_WINDOW)) == 0) {
            args->window = atoi(argv[i] + strlen(ARG_WINDOW));
            if (args->window < 1) args->window = 1;
            if (args->window > 10) args->window = 10;
        } else if (strncmp(argv[i], ARG_TIME_STEP, strlen(ARG_TIME_STEP)) == 0) {
            args->time_step = atoi(argv[i] + strlen(ARG_TIME_STEP));
            if (args->time_step < 10) args->time_step = 10;
            if (args->time_step > 120) args->time_step = 120;
        } else if (strncmp(argv[i], ARG_CODE_LENGTH, strlen(ARG_CODE_LENGTH)) == 0) {
            args->code_length = atoi(argv[i] + strlen(ARG_CODE_LENGTH));
            if (args->code_length < 4) args->code_length = 4;
            if (args->code_length > 20) args->code_length = 20;
        }
    }
}

/*
 * Expand ~ in path to user's home directory
 */
static void expand_path(const char *path, const char *home_dir, char *out, size_t out_len) {
    if (path[0] == '~') {
        snprintf(out, out_len, "%s%s", home_dir, path + 1);
    } else {
        strncpy(out, path, out_len - 1);
        out[out_len - 1] = '\0';
    }
}

/*
 * Read secret from file
 * Returns 0 on success, -1 on failure
 */
static int read_secret(const char *path, char *secret, size_t secret_len) {
    FILE *f = fopen(path, "r");
    if (!f) {
        return -1;
    }

    if (!fgets(secret, secret_len, f)) {
        fclose(f);
        return -1;
    }
    fclose(f);

    /* Strip trailing newline */
    size_t len = strlen(secret);
    while (len > 0 && (secret[len - 1] == '\n' || secret[len - 1] == '\r')) {
        secret[--len] = '\0';
    }

    /* Validate hex string */
    if (len == 0 || len % 2 != 0) {
        return -1;
    }
    for (size_t i = 0; i < len; i++) {
        char c = secret[i];
        if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F'))) {
            return -1;
        }
    }

    return 0;
}

/*
 * Validate file permissions (must be regular file, owned by user, 0600)
 */
static int validate_file_permissions(const char *path, uid_t uid) {
    struct stat st;
    if (lstat(path, &st) != 0) {
        return -1;
    }

    /* Must be regular file */
    if (!S_ISREG(st.st_mode)) {
        return -1;
    }

    /* Must not be symlink */
    if (S_ISLNK(st.st_mode)) {
        return -1;
    }

    /* Must be owned by user */
    if (st.st_uid != uid) {
        return -1;
    }

    /* Permissions must be 0600 (owner rw only) */
    if ((st.st_mode & 0777) != 0600) {
        return -1;
    }

    return 0;
}

/*
 * Convert hex string to bytes
 * Returns number of bytes written, or -1 on error
 */
static int hex_to_bytes(const char *hex, unsigned char *bytes, size_t max_bytes) {
    size_t hex_len = strlen(hex);
    if (hex_len % 2 != 0 || hex_len / 2 > max_bytes) {
        return -1;
    }

    for (size_t i = 0; i < hex_len; i += 2) {
        unsigned int byte;
        if (sscanf(hex + i, "%2x", &byte) != 1) {
            return -1;
        }
        bytes[i / 2] = (unsigned char)byte;
    }

    return hex_len / 2;
}

/*
 * BetterTOTP encoding: encode hash bytes to charset
 * Same algorithm as btotp/charset.py
 */
static void encode_to_chars(const unsigned char *hash_bytes, size_t hash_len,
                            char *output, int length) {
    for (int i = 0; i < length; i++) {
        unsigned char low = hash_bytes[i % hash_len];
        unsigned char high = hash_bytes[(i + 1) % hash_len];
        int idx = (low + high * 256) % CHARSET_SIZE;
        output[i] = CHARSET[idx];
    }
    output[length] = '\0';
}

/*
 * Compute HMAC-SHA512
 * Returns digest length, or -1 on error
 */
static int compute_hmac(const unsigned char *key, size_t key_len,
                        const unsigned char *msg, size_t msg_len,
                        unsigned char *digest, unsigned int *digest_len) {
    HMAC(EVP_sha512(), key, key_len, msg, msg_len, digest, digest_len);
    return *digest_len;
}

/*
 * Generate TOTP code for a given counter
 */
static int generate_totp(const unsigned char *secret, size_t secret_len,
                         uint64_t counter, int code_length,
                         char *code_out) {
    /* Pack counter as big-endian 64-bit integer */
    unsigned char msg[8];
    for (int i = 7; i >= 0; i--) {
        msg[i] = counter & 0xFF;
        counter >>= 8;
    }

    /* Compute HMAC-SHA512 */
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int digest_len = 0;
    if (compute_hmac(secret, secret_len, msg, 8, digest, &digest_len) < 0) {
        return -1;
    }

    /* Encode to charset */
    encode_to_chars(digest, digest_len, code_out, code_length);
    return 0;
}

/*
 * Verify TOTP code with time window
 * Returns 1 if valid, 0 if invalid
 */
static int verify_totp(const unsigned char *secret, size_t secret_len,
                       const char *code, int window, int time_step,
                       int code_length) {
    time_t now = time(NULL);
    uint64_t current_counter = (uint64_t)(now / time_step);

    char generated[32];
    for (int offset = -window; offset <= window; offset++) {
        uint64_t counter = current_counter + offset;
        if (generate_totp(secret, secret_len, counter, code_length, generated) < 0) {
            continue;
        }
        if (strcmp(generated, code) == 0) {
            return 1;
        }
    }
    return 0;
}

/*
 * Prompt user for input via PAM conversation function
 */
static int prompt_user(pam_handle_t *pamh, const char *prompt, char **response) {
    struct pam_conv *conv;
    int retval = pam_get_item(pamh, PAM_CONV, (const void **)&conv);
    if (retval != PAM_SUCCESS || conv == NULL || conv->conv == NULL) {
        return PAM_CONV_ERR;
    }

    struct pam_message msg;
    msg.msg_style = PAM_PROMPT_ECHO_OFF;
    msg.msg = prompt;

    const struct pam_message *msgp = &msg;
    struct pam_response *resp = NULL;

    retval = conv->conv(1, &msgp, &resp, conv->appdata_ptr);
    if (retval != PAM_SUCCESS || resp == NULL || resp->resp == NULL) {
        if (resp) {
            free(resp->resp);
            free(resp);
        }
        return PAM_CONV_ERR;
    }

    *response = resp->resp;
    free(resp);
    return PAM_SUCCESS;
}

/*
 * Drop privileges to user
 */
static int drop_privileges(const char *username) {
    struct passwd *pw = getpwnam(username);
    if (pw == NULL) {
        return -1;
    }

    if (setgroups(0, NULL) != 0) {
        return -1;
    }

    if (setgid(pw->pw_gid) != 0) {
        return -1;
    }

    if (setuid(pw->pw_uid) != 0) {
        return -1;
    }

    return 0;
}

/*
 * Restore privileges to root
 */
static int restore_privileges(uid_t ruid, gid_t rgid) {
    if (setegid(rgid) != 0) {
        return -1;
    }
    if (seteuid(ruid) != 0) {
        return -1;
    }
    return 0;
}

/*
 * PAM entry point: authenticate user
 */
PAM_EXTERN int pam_sm_authenticate(pam_handle_t *pamh, int flags,
                                   int argc, const char **argv) {
    (void)flags;
    btotp_args_t args;
    parse_args(argc, argv, &args);

    /* Save root privileges for later restoration */
    uid_t ruid = geteuid();
    gid_t rgid = getegid();

    const char *username = NULL;
    int retval = pam_get_user(pamh, &username, NULL);
    if (retval != PAM_SUCCESS || username == NULL) {
        return PAM_AUTHINFO_UNAVAIL;
    }

    if (args.debug) {
        pam_syslog(pamh, LOG_DEBUG, "btotp: authenticating user %s", username);
    }

    /* Get user's home directory */
    struct passwd *pw = getpwnam(username);
    if (pw == NULL) {
        return PAM_AUTHINFO_UNAVAIL;
    }

    /* Expand secret path */
    char secret_path[PATH_MAX];
    expand_path(args.secret_path, pw->pw_dir, secret_path, sizeof(secret_path));

    /* Drop privileges to user for file access */
    if (drop_privileges(username) != 0) {
        pam_syslog(pamh, LOG_ERR, "btotp: failed to drop privileges for %s", username);
        return PAM_AUTH_ERR;
    }

    /* Read secret file */
    char secret_hex[MAX_SECRET_LEN];
    int secret_exists = (read_secret(secret_path, secret_hex, sizeof(secret_hex)) == 0);

    /* Validate file permissions if secret exists */
    if (secret_exists) {
        if (validate_file_permissions(secret_path, pw->pw_uid) != 0) {
            pam_syslog(pamh, LOG_ERR, "btotp: secret file %s has invalid permissions", secret_path);
            restore_privileges(ruid, rgid);
            return PAM_AUTH_ERR;
        }
    }

    /* Restore root privileges */
    if (restore_privileges(ruid, rgid) != 0) {
        pam_syslog(pamh, LOG_ERR, "btotp: failed to restore privileges");
        return PAM_AUTH_ERR;
    }

    /* If no secret file and nullok is set, allow through */
    if (!secret_exists && args.nullok) {
        if (args.debug) {
            pam_syslog(pamh, LOG_DEBUG, "btotp: no secret file, nullok enabled");
        }
        return PAM_SUCCESS;
    }

    /* If no secret file and nullok not set, deny */
    if (!secret_exists) {
        pam_syslog(pamh, LOG_ERR, "btotp: no secret file for user %s", username);
        return PAM_AUTH_ERR;
    }

    /* Convert hex secret to bytes */
    unsigned char secret_bytes[MAX_SECRET_LEN / 2];
    int secret_len = hex_to_bytes(secret_hex, secret_bytes, sizeof(secret_bytes));
    if (secret_len <= 0) {
        pam_syslog(pamh, LOG_ERR, "btotp: invalid secret format for user %s", username);
        return PAM_AUTH_ERR;
    }

    /* Prompt for verification code */
    char *code = NULL;
    retval = prompt_user(pamh, "Verification code: ", &code);
    if (retval != PAM_SUCCESS || code == NULL) {
        return PAM_CONV_ERR;
    }

    /* Verify the code */
    int valid = verify_totp(secret_bytes, secret_len, code,
                            args.window, args.time_step, args.code_length);

    /* Clear code from memory */
    memset(code, 0, strlen(code));
    free(code);

    if (valid) {
        if (args.debug) {
            pam_syslog(pamh, LOG_DEBUG, "btotp: verification successful for %s", username);
        }
        return PAM_SUCCESS;
    } else {
        if (args.debug) {
            pam_syslog(pamh, LOG_DEBUG, "btotp: verification failed for %s", username);
        }
        return PAM_AUTH_ERR;
    }
}

/*
 * PAM entry point: set credentials (no-op)
 */
PAM_EXTERN int pam_sm_setcred(pam_handle_t *pamh, int flags,
                              int argc, const char **argv) {
    (void)pamh; (void)flags; (void)argc; (void)argv;
    return PAM_SUCCESS;
}

/*
 * PAM entry point: account management (no-op)
 */
PAM_EXTERN int pam_sm_acct_mgmt(pam_handle_t *pamh, int flags,
                                int argc, const char **argv) {
    (void)pamh; (void)flags; (void)argc; (void)argv;
    return PAM_SUCCESS;
}

/*
 * PAM entry point: open session (no-op)
 */
PAM_EXTERN int pam_sm_open_session(pam_handle_t *pamh, int flags,
                                   int argc, const char **argv) {
    (void)pamh; (void)flags; (void)argc; (void)argv;
    return PAM_SUCCESS;
}

/*
 * PAM entry point: close session (no-op)
 */
PAM_EXTERN int pam_sm_close_session(pam_handle_t *pamh, int flags,
                                    int argc, const char **argv) {
    (void)pamh; (void)flags; (void)argc; (void)argv;
    return PAM_SUCCESS;
}

/*
 * PAM entry point: change password (no-op)
 */
PAM_EXTERN int pam_sm_chauthtok(pam_handle_t *pamh, int flags,
                                int argc, const char **argv) {
    (void)pamh; (void)flags; (void)argc; (void)argv;
    return PAM_SUCCESS;
}

#ifdef PAM_MODULE_ENTRY
PAM_MODULE_ENTRY
#endif
