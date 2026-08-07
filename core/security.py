import os
import time
import json
import hmac
import hashlib
import base64
from typing import Optional, Dict, Any, Tuple
from config import settings

_failed_attempts: Dict[str, Dict[str, Any]] = {}

HASH_ALGORITHM = "sha256"
HASH_ITERATIONS = 100000


def hash_password(password: str) -> str:
    if not password:
        return ""
    salt = os.urandom(16).hex()
    hashed = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        HASH_ITERATIONS
    ).hex()
    return f"pbkdf2:{HASH_ALGORITHM}:{HASH_ITERATIONS}${salt}${hashed}"


def verify_password(password: str, stored_hash: str) -> Tuple[bool, bool]:
    if not password or not stored_hash:
        return False, False

    if stored_hash.startswith("pbkdf2:"):
        try:
            algorithm_part, salt_part, hash_part = stored_hash.split("$")
            _, algo, iterations = algorithm_part.split(":")
            iterations = int(iterations)

            computed_hash = hashlib.pbkdf2_hmac(
                algo,
                password.encode("utf-8"),
                salt_part.encode("utf-8"),
                iterations
            ).hex()

            is_valid = hmac.compare_digest(computed_hash, hash_part)
            return is_valid, False
        except Exception:
            return False, False

    is_valid = (password == stored_hash)
    return is_valid, is_valid


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def _b64_decode(data: str) -> bytes:
    padding = '=' * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode(data + padding)


def generate_jwt_token(payload: Dict[str, Any], secret: Optional[str] = None, expires_in_seconds: int = 86400) -> str:
    key = (secret or settings.JWT_SECRET).encode('utf-8')
    header = {"alg": "HS256", "typ": "JWT"}

    current_time = int(time.time())
    token_payload = payload.copy()
    token_payload["iat"] = current_time
    token_payload["exp"] = current_time + expires_in_seconds

    header_b64 = _b64_encode(json.dumps(header).encode('utf-8'))
    payload_b64 = _b64_encode(json.dumps(token_payload).encode('utf-8'))

    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(key, signing_input, hashlib.sha256).digest()
    signature_b64 = _b64_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def verify_jwt_token(token: str, secret: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    if not token or not isinstance(token, str):
        return False, None, "Токен отсутствует"

    if token.startswith("Bearer "):
        token = token[7:]

    parts = token.split(".")
    if len(parts) != 3:
        return False, None, "Неверный формат токена"

    header_b64, payload_b64, signature_b64 = parts
    key = (secret or settings.JWT_SECRET).encode('utf-8')

    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    expected_sig = hmac.new(key, signing_input, hashlib.sha256).digest()
    expected_sig_b64 = _b64_encode(expected_sig)

    if not hmac.compare_digest(signature_b64, expected_sig_b64):
        return False, None, "Недействительная подпись токена"

    try:
        payload_bytes = _b64_decode(payload_b64)
        payload = json.loads(payload_bytes.decode('utf-8'))
    except Exception as e:
        return False, None, f"Ошибка декодирования payload: {e}"

    exp = payload.get("exp")
    if exp and int(time.time()) > int(exp):
        return False, None, "Срок действия токена истёк"

    return True, payload, ""


def check_brute_force(key: str, max_attempts: int = 5, lockout_seconds: int = 900) -> Tuple[bool, int]:
    now = time.time()
    record = _failed_attempts.get(key)
    if not record:
        return True, 0

    attempts = record.get("count", 0)
    lockout_until = record.get("lockout_until", 0)

    if now < lockout_until:
        remaining = int(lockout_until - now)
        return False, remaining

    if attempts >= max_attempts and now >= lockout_until:
        _failed_attempts[key] = {"count": 0, "lockout_until": 0}
        return True, 0

    return True, 0


def record_failed_login(key: str, max_attempts: int = 5, lockout_seconds: int = 900) -> int:
    now = time.time()
    record = _failed_attempts.get(key, {"count": 0, "lockout_until": 0})
    count = record.get("count", 0) + 1
    lockout_until = 0

    if count >= max_attempts:
        lockout_until = now + lockout_seconds
        print(f"[SECURITY WARNING] Заблокирован ключ '{key}' на {lockout_seconds} секунд из-за {count} неудачных попыток.")

    _failed_attempts[key] = {"count": count, "lockout_until": lockout_until}
    return max(0, max_attempts - count)


def reset_failed_login(key: str):
    if key in _failed_attempts:
        del _failed_attempts[key]


def is_origin_allowed(origin: str) -> bool:
    if not origin:
        return True
    if origin in settings.ALLOWED_ORIGINS or "*" in settings.ALLOWED_ORIGINS:
        return True
    if any(origin.startswith(prefix) for prefix in [
        "http://localhost", "https://localhost", "http://127.0.0.1",
        "https://crm-cosmo.streamlit.app", "https://web.telegram.org"
    ]):
        return True
    return False
