import os, hashlib, struct, base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SOURCE_FILE = "main.py"
OUTPUT_FILE = "main_secure.py"

MASTER_KEY = b'TG_HOOKER_V8_KIVY_ANDROID_2024_X9K2_ULTRA_SECRET_42'

def encrypt_source(src_bytes):
    salt = os.urandom(32)
    dk = hashlib.pbkdf2_hmac('sha512', MASTER_KEY, salt, 1_000_000, dklen=32)
    nonce = os.urandom(12)
    aesgcm = AESGCM(dk)
    ct_tag = aesgcm.encrypt(nonce, src_bytes, None)
    return salt, nonce, ct_tag

def build_secure_loader(salt, nonce, ct_tag):
    salt_b64 = base64.b64encode(salt).decode()
    nonce_b64 = base64.b64encode(nonce).decode()
    ct_b64 = base64.b64encode(ct_tag).decode()

    return f'''import os, sys, hashlib, base64, time as _time
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_SK = b'TG_HOOKER_V8_KIVY_ANDROID_2024_X9K2_ULTRA_SECRET_42'
_S  = base64.b64decode("{salt_b64}")
_N  = base64.b64decode("{nonce_b64}")
_CT = base64.b64decode("{ct_b64}")

def _dec():
    dk = hashlib.pbkdf2_hmac("sha512", _SK, _S, 1000000, dklen=32)
    aesgcm = AESGCM(dk)
    return aesgcm.decrypt(_N, _CT, None)

_code = _dec().decode("utf-8")
_ns = {{"__name__": "__main__", "__builtins__": __builtins__}}
exec(compile(_code, "<TG_HOOKER_V8_KIVY>", "exec"), _ns)
'''

def main():
    with open(SOURCE_FILE, "rb") as f:
        src = f.read()
    print(f"[*] Original: {len(src)} bytes ({len(src)//1024}KB)")
    print(f"[*] Algorithm: AES-256-GCM + PBKDF2-HMAC-SHA512 (1M iterations)")
    salt, nonce, ct_tag = encrypt_source(src)
    print(f"[*] Encrypted: salt={len(salt)} nonce={len(nonce)} ct_tag={len(ct_tag)}")
    loader = build_secure_loader(salt, nonce, ct_tag)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(loader)
    print(f"[+] Secure loader: {OUTPUT_FILE} ({len(loader)} bytes)")

if __name__ == "__main__":
    main()
