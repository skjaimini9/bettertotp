try:
    import qrcode
    _HAS_QR = True
except ImportError:
    _HAS_QR = False


def print_qr(text: str):
    if not _HAS_QR:
        raise ImportError("qrcode library is required for QR generation. Install with: pip install bettertotp[qr]")
    qr = qrcode.QRCode(border=1)
    qr.add_data(text)
    qr.make(fit=True)
    qr.print_ascii(invert=True)
