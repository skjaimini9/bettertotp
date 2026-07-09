import subprocess
import sys

_HAS_PYPERCLIP = False
try:
    import pyperclip
    _HAS_PYPERCLIP = True
except ImportError:
    pass


def _xclip_copy(text: str) -> bool:
    try:
        proc = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
        proc.communicate(text.encode("utf-8"))
        return proc.returncode == 0
    except FileNotFoundError:
        return False


def _xsel_copy(text: str) -> bool:
    try:
        proc = subprocess.Popen(["xsel", "-b", "-i"], stdin=subprocess.PIPE)
        proc.communicate(text.encode("utf-8"))
        return proc.returncode == 0
    except FileNotFoundError:
        return False


def _pbcopy_copy(text: str) -> bool:
    try:
        proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        proc.communicate(text.encode("utf-8"))
        return proc.returncode == 0
    except FileNotFoundError:
        return False


def _powershell_copy(text: str) -> bool:
    if sys.platform != "win32":
        return False
    try:
        proc = subprocess.Popen(["powershell", "-command", "Set-Clipboard", text], stdin=subprocess.PIPE)
        proc.communicate()
        return proc.returncode == 0
    except FileNotFoundError:
        return False


_COPY_FUNCS = [_powershell_copy, _pbcopy_copy, _xclip_copy, _xsel_copy]


def copy_to_clipboard(text: str) -> bool:
    if _HAS_PYPERCLIP:
        try:
            pyperclip.copy(text)
            return True
        except Exception:
            pass

    for func in _COPY_FUNCS:
        if func(text):
            return True
    return False
