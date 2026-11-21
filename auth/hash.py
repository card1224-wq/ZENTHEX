import hashlib
import hmac
import secrets

ITERATIONS = 600000


def get_password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
    return f'pbkdf2_sha256${ITERATIONS}${salt}${digest}'


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        if hashed_password.startswith('pbkdf2_sha256$'):
            algorithm, count, salt, expected = hashed_password.split('$')
            count = int(count)
            if not 100000 <= count <= 2000000 or len(salt) != 32 or len(expected) != 64:
                return False
            actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), count).hex()
            return hmac.compare_digest(actual, expected)
        if len(hashed_password) == 64:
            return hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), hashed_password)
    except (AttributeError, TypeError, ValueError):
        return False
    return False
