from pathlib import Path

from loguru import logger

BASE_DIR = Path(__file__).parent.parent
USER_AGREEMENT_PATH = BASE_DIR / "files" / "user_agreement.txt"
PRIVACY_POLICY_PATH = BASE_DIR / "files" / "privacy_policy.txt"


def read_txt_file(file_path: Path) -> str:
    """Reads the contents of a TXT file."""
    try:
        with file_path.open("r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return "Файл не найден"
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return "Ошибка чтения файла"
