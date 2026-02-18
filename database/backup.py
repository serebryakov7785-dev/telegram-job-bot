import logging
import os
import sqlite3
from datetime import datetime

from .core import get_connection

BACKUP_DIR = "backups"


def create_backup():
    """Создание резервной копии базы данных"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    try:
        # Используем API SQLite для безопасного бэкапа
        src_conn = get_connection()
        dst_conn = sqlite3.connect(backup_path)

        with dst_conn:
            src_conn.backup(dst_conn)

        dst_conn.close()

        logging.info(f"✅ Резервная копия создана: {backup_path}")

        # Удаляем старые бэкапы (оставляем последние 5)
        cleanup_old_backups()

        return True, backup_path
    except Exception as e:
        logging.error(f"❌ Ошибка создания бэкапа: {e}", exc_info=True)
        return False, str(e)


def cleanup_old_backups(keep_last: int = 5) -> None:
    """Удаление старых бэкапов"""
    try:
        if not os.path.exists(BACKUP_DIR):
            return

        files = [
            os.path.join(BACKUP_DIR, f)
            for f in os.listdir(BACKUP_DIR)
            if f.startswith("backup_") and f.endswith(".db")
        ]
        files.sort(key=os.path.getmtime, reverse=True)

        if len(files) > keep_last:
            for f in files[keep_last:]:
                os.remove(f)
                logging.info(f"🗑️ Удален старый бэкап: {f}")
    except Exception as e:
        logging.error(f"❌ Ошибка очистки бэкапов: {e}", exc_info=True)
