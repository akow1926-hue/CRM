import sys
from typing import Optional, Dict, Any, Tuple
import db
from core import security, logger

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def authenticate_user(username: str, password: str, client_ip: str = "") -> Tuple[bool, Optional[Dict[str, Any]], str]:
    if not username or not password:
        return False, None, "Укажите логин и пароль"

    u_clean = username.strip()
    p_clean = password.strip()

    key = f"user:{u_clean.lower()}"
    allowed, remaining_seconds = security.check_brute_force(key)
    if not allowed:
        minutes = (remaining_seconds // 60) + 1
        logger.log_warning(f"Попытка входа заблокированного пользователя '{u_clean}' с IP '{client_ip}'")
        return False, None, f"Превышено количество попыток входа. Попробуйте через {minutes} мин."

    user = db.get_user_by_username(u_clean)
    if not user:
        remaining = security.record_failed_login(key)
        logger.log_warning(f"Неудачная попытка входа: пользователь '{u_clean}' не найден (IP: {client_ip})")
        return False, None, "Неверный логин или пароль"

    if user.get("Status") == "Заблокирован":
        logger.log_warning(f"Попытка входа заблокированного аккаунта '{u_clean}'")
        return False, None, "Ваш аккаунт заблокирован администратором"

    stored_pass = user.get("Password", "")
    is_valid, needs_rehash = security.verify_password(p_clean, stored_pass)

    if not is_valid:
        remaining = security.record_failed_login(key)
        logger.log_warning(f"Неверный пароль для пользователя '{u_clean}' (IP: {client_ip}). Осталось попыток: {remaining}")
        return False, None, "Неверный логин или пароль"

    security.reset_failed_login(key)

    if needs_rehash:
        new_hashed = security.hash_password(p_clean)
        db.update_user_password(u_clean, new_hashed)
        logger.log_info(f"Пароль пользователя '{u_clean}' успешно переведён в защищенный хэш PBKDF2.")

    logger.log_audit(
        username=user["Username"],
        role=user["Role"],
        action="LOGIN_SUCCESS",
        target_type="system",
        target_id=str(user["id"]),
        ip_address=client_ip
    )

    return True, user, ""


def login_telegram_user(telegram_id: str | int, username: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    tg_str = str(telegram_id).strip()
    success, user, err = authenticate_user(username, password, client_ip=f"tg:{tg_str}")

    if success and user:
        current_tg = user.get("TelegramID", "")
        if current_tg != tg_str:
            db.bind_telegram_id(user["Username"], tg_str)
            user["TelegramID"] = tg_str
            logger.log_info(f"Telegram ID {tg_str} успешно привязан к аккаунту {user['Username']}.")

    return success, user, err


def verify_telegram_id_access(telegram_id: str | int, required_role_category: str = "") -> Tuple[bool, Optional[Dict[str, Any]], str]:
    tg_str = str(telegram_id).strip()
    if not tg_str:
        return False, None, "Telegram ID не указан"

    user = db.get_user_by_telegram_id(tg_str)
    if not user:
        return False, None, "Ваш Telegram аккаунт не привязан к сотруднику"

    if user.get("Status") == "Заблокирован":
        return False, None, "Ваш аккаунт заблокирован"

    role = str(user.get("Role", "")).lower()
    if required_role_category:
        req = required_role_category.lower()
        if req == "courier" and not any(k in role for k in ["courier", "курьер", "доставщик", "yuboruvchi", "kuryer", "admin", "админ"]):
            return False, user, "У вас нет прав курьера"
        if req == "dispatcher" and not any(k in role for k in ["dispatcher", "диспетчер", "dispetcher", "admin", "админ"]):
            return False, user, "У вас нет прав диспетчера"

    return True, user, ""


def create_user_session(user: Dict[str, Any], client_ip: str = "") -> Tuple[str, str]:
    payload = {
        "user_id": user.get("id"),
        "username": user.get("Username"),
        "role": user.get("Role"),
        "telegram_id": user.get("TelegramID", "")
    }
    jwt_token = security.generate_jwt_token(payload, expires_in_seconds=86400)
    db.create_session(
        token=jwt_token,
        username=user.get("Username", ""),
        role=user.get("Role", ""),
        telegram_id=user.get("TelegramID", ""),
        ip_address=client_ip,
        ttl_hours=24
    )
    return jwt_token, jwt_token


def validate_session(token: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    is_valid, payload, err = security.verify_jwt_token(token)
    if not is_valid:
        return False, None, err

    session = db.get_session(token)
    if not session:
        return False, None, "Сессия не найдена или её срок истёк"

    return True, session, ""


def logout_session(token: str) -> bool:
    return db.delete_session(token)
