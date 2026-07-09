import argparse
import sys
import time

from .core import generate_code, verify_code, DEFAULT_HASH_ALGO, DEFAULT_CODE_LENGTH, DEFAULT_TIME_STEP
from .secret import generate_secret, format_secret_for_display, secret_to_b32, b32_to_secret, hex_to_secret
from .vault import Vault
from .uri import parse_otpauth, generate_uri
from .clipboard import copy_to_clipboard
from .config import load_config


def hex_to_bytes(h):
    h = h.replace(" ", "")
    return bytes.fromhex(h)


def _get_vault(args) -> Vault:
    vault = Vault()
    if not vault.exists():
        print("No vault found. Create one with: btotp init", file=sys.stderr)
        sys.exit(1)
    vault.unlock()
    return vault


def handle_generate_secret(args):
    secret = generate_secret()
    if args.format == "b32":
        output = secret_to_b32(secret)
    else:
        output = format_secret_for_display(secret)
    if args.output:
        with open(args.output, "w") as f:
            if args.format == "b32":
                f.write(output)
            else:
                f.write(secret.hex())
        print(f"Secret written to {args.output}", file=sys.stderr)
    else:
        print(output)


def handle_code(args):
    config = load_config()
    algorithm = args.algorithm or config.get("hash_algo", DEFAULT_HASH_ALGO)
    code_length = args.length or config.get("code_length", DEFAULT_CODE_LENGTH)
    time_step = args.step or config.get("time_step", DEFAULT_TIME_STEP)
    clipboard = args.clipboard or config.get("clipboard", False)

    if args.secret:
        secret = hex_to_bytes(args.secret)
    elif args.account:
        vault = _get_vault(args)
        secret = bytes.fromhex(vault.get(args.account)["secret"])
        account_info = vault.get(args.account)
        algorithm = account_info.get("algorithm", algorithm)
        code_length = account_info.get("digits", code_length)
        time_step = account_info.get("period", time_step)
    else:
        print("Either --secret or --account is required", file=sys.stderr)
        sys.exit(1)

    if args.watch:
        last_code = None
        try:
            while True:
                code = generate_code(secret, algorithm=algorithm, code_length=code_length, time_step=time_step)
                if code != last_code:
                    print(code)
                    last_code = code
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
    else:
        code = generate_code(secret, algorithm=algorithm, code_length=code_length, time_step=time_step)
        if clipboard:
            if copy_to_clipboard(code):
                print(f"Copied to clipboard: {code}")
            else:
                print(f"Failed to copy to clipboard: {code}", file=sys.stderr)
                sys.exit(1)
        else:
            print(code)


def handle_verify(args):
    config = load_config()
    algorithm = args.algorithm or config.get("hash_algo", DEFAULT_HASH_ALGO)
    code_length = args.length or config.get("code_length", DEFAULT_CODE_LENGTH)
    time_step = args.step or config.get("time_step", DEFAULT_TIME_STEP)

    if args.secret:
        secret = hex_to_bytes(args.secret)
    elif args.account:
        vault = _get_vault(args)
        secret = bytes.fromhex(vault.get(args.account)["secret"])
        account_info = vault.get(args.account)
        algorithm = account_info.get("algorithm", algorithm)
        code_length = account_info.get("digits", code_length)
        time_step = account_info.get("period", time_step)
    else:
        print("Either --secret or --account is required", file=sys.stderr)
        sys.exit(1)

    valid = verify_code(secret, args.code, args.window, algorithm=algorithm, code_length=code_length, time_step=time_step)
    if valid:
        print("VALID")
        sys.exit(0)
    else:
        print("INVALID")
        sys.exit(1)


def handle_init(args):
    vault = Vault()
    if vault.exists():
        print("Vault already exists at", vault.path, file=sys.stderr)
        sys.exit(1)
    vault.create()
    print(f"Vault created at {vault.path}", file=sys.stderr)


def handle_add(args):
    vault = _get_vault(args)
    secret_hex = None
    if args.secret:
        secret_hex = format_secret_for_display(hex_to_bytes(args.secret)).replace(" ", "").lower()
    elif args.b32:
        secret_hex = b32_to_secret(args.b32).hex()
    elif args.uri:
        parsed = parse_otpauth(args.uri)
        secret_hex = parsed["secret"]
        if not args.issuer:
            args.issuer = parsed["issuer"]
        if not args.algorithm:
            args.algorithm = parsed["algorithm"]
        if not args.digits:
            args.digits = parsed["digits"]
        if not args.period:
            args.period = parsed["period"]
    elif args.generate:
        secret_hex = generate_secret().hex()
    else:
        print("Provide --secret, --b32, --uri, or --generate", file=sys.stderr)
        sys.exit(1)

    vault.add(args.name, secret_hex, issuer=args.issuer, algorithm=args.algorithm,
               digits=args.digits, period=args.period)
    print(f"Added account '{args.name}' to vault")


def handle_list(args):
    vault = _get_vault(args)
    accounts = vault.list_accounts()
    if not accounts:
        print("No accounts in vault")
        return
    name_width = max(len(a["name"]) for a in accounts)
    for acc in accounts:
        code = vault.code(acc["name"])
        issuer = f"[{acc.get('issuer', '')}] " if acc.get("issuer") else ""
        print(f"  {acc['name']:{name_width}}  {code}  {issuer}({acc.get('digits', 12)}c / {acc.get('period', 45)}s)")


def handle_show(args):
    vault = _get_vault(args)
    try:
        code = vault.code(args.name)
    except KeyError:
        print(f"Account '{args.name}' not found", file=sys.stderr)
        sys.exit(1)
    if args.clipboard:
        if copy_to_clipboard(code):
            print(f"Copied to clipboard: {code}")
        else:
            print(f"Failed to copy to clipboard: {code}", file=sys.stderr)
            sys.exit(1)
    else:
        print(code)


def handle_remove(args):
    vault = _get_vault(args)
    try:
        vault.remove(args.name)
        print(f"Removed account '{args.name}'")
    except KeyError:
        print(f"Account '{args.name}' not found", file=sys.stderr)
        sys.exit(1)


def handle_rename(args):
    vault = _get_vault(args)
    try:
        vault.rename(args.old_name, args.new_name)
        print(f"Renamed '{args.old_name}' to '{args.new_name}'")
    except KeyError as e:
        print(e, file=sys.stderr)
        sys.exit(1)


def handle_import_uri(args):
    vault = _get_vault(args)
    parsed = parse_otpauth(args.uri)
    name = args.name or parsed.get("account", "unknown")
    vault.add(name, parsed["secret"], issuer=parsed.get("issuer", ""),
               algorithm=parsed.get("algorithm", DEFAULT_HASH_ALGO),
               digits=parsed.get("digits", DEFAULT_CODE_LENGTH),
               period=parsed.get("period", DEFAULT_TIME_STEP))
    print(f"Imported '{name}' from URI")


def handle_export(args):
    vault = _get_vault(args)
    data = vault.export_json()
    if args.output:
        with open(args.output, "w") as f:
            f.write(data)
        print(f"Exported to {args.output}")
    else:
        print(data)


def handle_import(args):
    vault = _get_vault(args)
    if args.input:
        with open(args.input) as f:
            data = f.read()
    else:
        data = sys.stdin.read()
    vault.import_json(data)
    print("Import complete")


def handle_uri(args):
    vault = _get_vault(args)
    try:
        acc = vault.get(args.name)
    except KeyError:
        print(f"Account '{args.name}' not found", file=sys.stderr)
        sys.exit(1)
    uri = generate_uri(
        account=args.name,
        secret_hex=acc["secret"],
        issuer=acc.get("issuer", ""),
        algorithm=acc.get("algorithm", DEFAULT_HASH_ALGO),
        digits=acc.get("digits", DEFAULT_CODE_LENGTH),
        period=acc.get("period", DEFAULT_TIME_STEP),
    )
    if args.qr:
        try:
            from .qr import print_qr
            print_qr(uri)
        except ImportError as e:
            print(e, file=sys.stderr)
            sys.exit(1)
    else:
        print(uri)


def handle_completion(args):
    shell = args.shell
    try:
        import argcomplete
    except ImportError:
        print("argcomplete is required. Install with: pip install bettertotp[completion]", file=sys.stderr)
        sys.exit(1)

    parser = build_parser()
    if shell == "bash":
        print("source <(register-python-argcomplete btotp)")
    elif shell == "zsh":
        print("autoload -U bashcompinit && bashcompinit && source <(register-python-argcomplete btotp)")
    elif shell == "fish":
        print("register-python-argcomplete --shell fish btotp | source")
    else:
        print(f"Unsupported shell: {shell}", file=sys.stderr)
        sys.exit(1)


def handle_config(args):
    from .config import load_config, save_config
    config = load_config()
    if args.show:
        import json
        print(json.dumps(config, indent=2))
        return
    if args.set:
        key, value = args.set.split("=", 1)
        if key == "time_step":
            value = int(value)
        elif key == "code_length":
            value = int(value)
        elif key == "clipboard":
            value = value.lower() == "true"
        save_config({key: value})
        print(f"Set {key}={value}")


def build_parser():
    parser = argparse.ArgumentParser(
        description="BetterTOTP - Time-based one-time passwords with alphanumeric+special output"
    )
    sub = parser.add_subparsers(dest="command")

    p_gen = sub.add_parser("generate-secret", help="Generate a new secret key")
    p_gen.add_argument("-o", "--output", help="Output file (default: stdout)")
    p_gen.add_argument("-f", "--format", choices=["hex", "b32"], default="hex", help="Output format")

    p_code = sub.add_parser("code", help="Generate a TOTP code")
    p_code.add_argument("-s", "--secret", help="Secret key (hex string)")
    p_code.add_argument("-a", "--account", help="Account name in vault")
    p_code.add_argument("-w", "--watch", action="store_true", help="Watch mode, refresh periodically")
    p_code.add_argument("--copy", dest="clipboard", action="store_true", help="Copy to clipboard")
    p_code.add_argument("--algo", "--algorithm", dest="algorithm", help="Hash algorithm (sha1, sha256, sha512)")
    p_code.add_argument("--length", type=int, help="Code length")
    p_code.add_argument("--step", type=int, help="Time step in seconds")

    p_verify = sub.add_parser("verify", help="Verify a TOTP code")
    p_verify.add_argument("-s", "--secret", help="Secret key (hex string)")
    p_verify.add_argument("-a", "--account", help="Account name in vault")
    p_verify.add_argument("-c", "--code", required=True, help="Code to verify")
    p_verify.add_argument("-n", "--window", type=int, default=1, help="Window size for time drift")
    p_verify.add_argument("--algo", "--algorithm", dest="algorithm", help="Hash algorithm (sha1, sha256, sha512)")
    p_verify.add_argument("--length", type=int, help="Code length")
    p_verify.add_argument("--step", type=int, help="Time step in seconds")

    p_init = sub.add_parser("init", help="Create a new encrypted vault")
    p_add = sub.add_parser("add", help="Add an account to the vault")
    p_add.add_argument("name", help="Account name")
    p_add.add_argument("-s", "--secret", help="Secret key (hex string)")
    p_add.add_argument("--b32", help="Secret key (base32 string)")
    p_add.add_argument("-u", "--uri", help="Import from otpauth:// URI")
    p_add.add_argument("-g", "--generate", action="store_true", help="Generate a new random secret")
    p_add.add_argument("-i", "--issuer", default="", help="Issuer name")
    p_add.add_argument("--algo", "--algorithm", dest="algorithm", default=DEFAULT_HASH_ALGO, help="Hash algorithm")
    p_add.add_argument("--digits", type=int, default=DEFAULT_CODE_LENGTH, help="Code length")
    p_add.add_argument("--period", type=int, default=DEFAULT_TIME_STEP, help="Time step in seconds")

    sub.add_parser("list", help="List all accounts with current codes")
    p_show = sub.add_parser("show", help="Show current code for an account")
    p_show.add_argument("name", help="Account name")
    p_show.add_argument("--copy", dest="clipboard", action="store_true", help="Copy to clipboard")

    p_remove = sub.add_parser("remove", help="Remove an account")
    p_remove.add_argument("name", help="Account name")

    p_rename = sub.add_parser("rename", help="Rename an account")
    p_rename.add_argument("old_name", help="Current account name")
    p_rename.add_argument("new_name", help="New account name")

    p_import_uri = sub.add_parser("import-uri", help="Import an account from an otpauth:// URI")
    p_import_uri.add_argument("uri", help="otpauth:// URI")
    p_import_uri.add_argument("-n", "--name", help="Account name (default: from URI)")

    p_export = sub.add_parser("export", help="Export vault as JSON")
    p_export.add_argument("-o", "--output", help="Output file (default: stdout)")

    p_import = sub.add_parser("import", help="Import accounts from JSON")
    p_import.add_argument("input", nargs="?", help="Input file (default: stdin)")

    p_uri = sub.add_parser("uri", help="Generate otpauth:// URI for an account")
    p_uri.add_argument("name", help="Account name")
    p_uri.add_argument("--qr", action="store_true", help="Display as QR code")

    p_comp = sub.add_parser("completion", help="Generate shell completion script")
    p_comp.add_argument("shell", choices=["bash", "zsh", "fish"], help="Shell type")

    p_config = sub.add_parser("config", help="Manage configuration")
    p_config.add_argument("--show", action="store_true", help="Show current configuration")
    p_config.add_argument("--set", help="Set a config value (key=value)")

    p_help = sub.add_parser("help", help="Show help for a command")
    p_help.add_argument("command_name", nargs="?", help="Command to show help for")

    return parser


def handle_help(args, parser):
    if args.command_name:
        sub = parser._subparsers._group_actions[0]
        for action in sub.choices.values():
            if action.prog.endswith(" " + args.command_name):
                action.print_help()
                return
        print(f"Unknown command: {args.command_name}", file=sys.stderr)
        sys.exit(1)
    else:
        parser.print_help()


def main():
    parser = build_parser()
    args = parser.parse_args()

    handlers = {
        "generate-secret": handle_generate_secret,
        "code": handle_code,
        "verify": handle_verify,
        "init": handle_init,
        "add": handle_add,
        "list": handle_list,
        "show": handle_show,
        "remove": handle_remove,
        "rename": handle_rename,
        "import-uri": handle_import_uri,
        "export": handle_export,
        "import": handle_import,
        "uri": handle_uri,
        "completion": handle_completion,
        "config": handle_config,
    }

    handler = handlers.get(args.command)
    if handler:
        handler(args)
    elif args.command == "help":
        handle_help(args, parser)
    else:
        parser.print_help()
        sys.exit(1)
