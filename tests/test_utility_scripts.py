import os
import sys
from unittest.mock import patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import remove_bom  # noqa


class TestUtilityScripts:

    # --- Тесты для remove_bom.py ---
    @pytest.fixture
    def temp_file_with_bom(self, tmp_path):
        """Создает временный файл с UTF-8 BOM."""
        file_path = tmp_path / "bom_file.py"
        bom = b"\xef\xbb\xbf"
        content = b"print('hello')"
        with open(file_path, "wb") as f:
            f.write(bom + content)
        return file_path

    @pytest.fixture
    def temp_file_no_bom(self, tmp_path):
        """Создает временный файл без BOM."""
        file_path = tmp_path / "no_bom_file.py"
        content = b"print('world')"
        with open(file_path, "wb") as f:
            f.write(content)
        return file_path

    def test_remove_bom_from_file_with_bom(self, temp_file_with_bom):
        """Тест удаления BOM из файла, где он есть."""
        # Проверяем, что в файле изначально есть BOM
        with open(temp_file_with_bom, "rb") as f:
            assert f.read(3) == b"\xef\xbb\xbf"

        # Запускаем функцию
        assert remove_bom.remove_bom_from_file(str(temp_file_with_bom)) is True

        # Проверяем, что BOM исчез
        with open(temp_file_with_bom, "rb") as f:
            assert f.read(3) != b"\xef\xbb\xbf"

    def test_remove_bom_from_files_main_function(
        self, temp_file_with_bom, temp_file_no_bom
    ):
        """Тест основной функции remove_bom_from_files."""
        directory = temp_file_with_bom.parent

        # Мокаем os.walk, чтобы сканировать только нашу временную папку
        with patch(
            "os.walk",
            return_value=[
                (str(directory), [], [temp_file_with_bom.name, temp_file_no_bom.name])
            ],
        ), patch(
            "os.path.exists", return_value=False
        ):  # Мокаем проверку конкретных файлов
            remove_bom.remove_bom_from_files(str(directory))

        # Проверяем, что BOM был удален из нужного файла
        with open(temp_file_with_bom, "rb") as f:
            assert not f.read().startswith(b"\xef\xbb\xbf")

    def test_remove_bom_from_file_exception(self):
        """Тест обработки исключений в remove_bom_from_file."""
        with patch("builtins.open", side_effect=IOError("Permission denied")):
            assert remove_bom.remove_bom_from_file("any_file.py") is False
