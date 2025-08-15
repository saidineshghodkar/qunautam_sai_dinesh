# crypto_utils.py - AES encryption and decryption

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import base64

def aes_encrypt(key: bytes, plaintext: bytes) -> str:
    iv = get_random_bytes(16)
    cipher = AES.new(key[:32], AES.MODE_CBC, iv)
    ct = cipher.encrypt(pad(plaintext, AES.block_size))
    payload = iv + ct
    return base64.b64encode(payload).decode()

def aes_decrypt(key: bytes, payload_b64: str) -> bytes:
    data = base64.b64decode(payload_b64)
    iv = data[:16]
    ct = data[16:]
    cipher = AES.new(key[:32], AES.MODE_CBC, iv)
    pt = unpad(cipher.decrypt(ct), AES.block_size)
    return pt
