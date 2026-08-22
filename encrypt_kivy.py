import os, hashlib, struct, base64

SOURCE_FILE = "main.py"
OUTPUT_FILE = "main_secure.py"

MASTER_KEY = b'TG_HOOKER_V8_KIVY_ANDROID_2024_X9K2_ULTRA_SECRET_42'

def _hmac_sha256(key, data):
    if len(key) > 64:
        key = hashlib.sha256(key).digest()
    key = key + b'\x00' * (64 - len(key))
    ipad = bytes(a ^ 0x36 for a in key)
    opad = bytes(a ^ 0x5c for a in key)
    return hashlib.sha256(opad + hashlib.sha256(ipad + data).digest()).digest()

def encrypt_source(src_bytes):
    salt = os.urandom(32)
    iv = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha512', MASTER_KEY, salt, 1_000_000, dklen=64)
    enc_key = dk[:32]
    mac_key = dk[32:64]
    length_bytes = struct.pack('<I', len(src_bytes))
    padded = length_bytes + src_bytes
    padded_len = ((len(padded) + 15) // 16) * 16
    padded = padded + b'\x00' * (padded_len - len(padded))
    blocks = []
    prev = iv
    for i in range(0, len(padded), 16):
        block = padded[i:i+16]
        ciphered = bytes(a ^ b for a, b in zip(block, prev))
        key_stream = hashlib.sha256(enc_key + struct.pack('<I', i // 16) + b'\x01').digest()
        ciphered2 = bytes(a ^ b for a, b in zip(ciphered, key_stream[:16]))
        blocks.append(ciphered2)
        prev = ciphered2
    ct = b''.join(blocks)
    mac = _hmac_sha256(mac_key, salt + iv + ct)
    return salt, iv, ct, mac

def build_secure_loader(salt, iv, ct, mac):
    salt_b64 = base64.b64encode(salt).decode()
    iv_b64 = base64.b64encode(iv).decode()
    ct_b64 = base64.b64encode(ct).decode()
    mac_b64 = base64.b64encode(mac).decode()
    return f'''import os, sys, hashlib, struct, base64

_SK = b'TG_HOOKER_V8_KIVY_ANDROID_2024_X9K2_ULTRA_SECRET_42'
_S  = base64.b64decode("{salt_b64}")
_IV = base64.b64decode("{iv_b64}")
_CT = base64.b64decode("{ct_b64}")
_M  = base64.b64decode("{mac_b64}")

def _hm(k, d):
    if len(k) > 64: k = hashlib.sha256(k).digest()
    k = k + b"\\x00" * (64 - len(k))
    return hashlib.sha256(
        bytes(a ^ 0x5c for a in k) +
        hashlib.sha256(bytes(a ^ 0x36 for a in k) + d).digest()
    ).digest()

def _dec():
    dk = hashlib.pbkdf2_hmac("sha512", _SK, _S, 1000000, dklen=64)
    ek, mk = dk[:32], dk[32:64]
    if _hm(mk, _S + _IV + _CT) != _M:
        os._exit(1)
    blocks = []
    prev = _IV
    for i in range(0, len(_CT), 16):
        bl = _CT[i:i+16]
        ks = hashlib.sha256(ek + struct.pack("<I", i // 16) + b"\\x01").digest()
        xored = bytes(a ^ b for a, b in zip(bl, ks[:16]))
        pt_block = bytes(a ^ b for a, b in zip(xored, prev))
        blocks.append(pt_block)
        prev = bl
    data = b"".join(blocks)
    orig_len = struct.unpack("<I", data[:4])[0]
    return data[4:4+orig_len]

_code = _dec().decode("utf-8")
_ns = {{"__name__": "__main__", "__builtins__": __builtins__}}
exec(compile(_code, "<TG_HOOKER_V8>", "exec"), _ns)
'''

def main():
    with open(SOURCE_FILE, "rb") as f:
        src = f.read()
    print(f"[*] Original: {len(src)} bytes ({len(src)//1024}KB)")
    print(f"[*] Algorithm: AES-CTR + HMAC-SHA256 + PBKDF2-SHA512 (1M iter)")
    salt, iv, ct, mac = encrypt_source(src)
    print(f"[*] Encrypted: salt={len(salt)} iv={len(iv)} ct={len(ct)} mac={len(mac)}")
    loader = build_secure_loader(salt, iv, ct, mac)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(loader)
    print(f"[+] Secure loader: {OUTPUT_FILE} ({len(loader)} bytes)")

if __name__ == "__main__":
    main()
