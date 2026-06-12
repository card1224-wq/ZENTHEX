import os
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

# 실 서비스 운영 시에는 반드시 환경 변수에서 가져와야 합니다.
# 32바이트(256비트) 키
SECRET_KEY = os.environ.get("ZENTHEX_CRYPTO_KEY", "zenthex_super_secret_master_key_32_").encode()[:32]

def encrypt_api_key(plain_text: str) -> str:
    if not plain_text:
        return ""
    
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(SECRET_KEY), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plain_text.encode()) + padder.finalize()
    
    encrypted = encryptor.update(padded_data) + encryptor.finalize()
    return base64.b64encode(iv + encrypted).decode('utf-8')

def decrypt_api_key(cipher_text: str) -> str:
    if not cipher_text:
        return ""
    
    try:
        decoded = base64.b64decode(cipher_text)
        iv = decoded[:16]
        encrypted_data = decoded[16:]
        
        cipher = Cipher(algorithms.AES(SECRET_KEY), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()
        
        unpadder = padding.PKCS7(128).unpadder()
        unpadded_data = unpadder.update(decrypted_padded) + unpadder.finalize()
        
        return unpadded_data.decode('utf-8')
    except Exception as e:
        print(f"Decryption Error: {e}")
        return ""
