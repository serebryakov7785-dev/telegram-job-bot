import hashlib
import io
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pdf_generator


class TestPdfGenerator:
    @pytest.fixture(autouse=True)
    def mock_md5(self, monkeypatch):
        """Mock hashlib.md5 to ignore usedforsecurity argument on older Python versions."""
        if sys.version_info < (3, 9):
            original_md5 = hashlib.md5

            def patched_md5(*args, **kwargs):
                kwargs.pop("usedforsecurity", None)
                return original_md5(*args, **kwargs)

            monkeypatch.setattr(hashlib, "md5", patched_md5)
            if "reportlab.pdfbase.pdfdoc" in sys.modules:
                monkeypatch.setattr(
                    sys.modules["reportlab.pdfbase.pdfdoc"], "md5", patched_md5
                )

    def test_register_fonts_found(self):
        """Test font registration when font file exists"""
        with patch("os.path.exists", return_value=True), patch(
            "pdf_generator.pdfmetrics.registerFont"
        ) as mock_reg, patch("pdf_generator.TTFont"):
            font = pdf_generator.register_fonts()
            assert font == "DejaVuSans"
            mock_reg.assert_called()

    def test_register_fonts_not_found(self):
        """Test font registration when font file does not exist"""
        with patch("os.path.exists", return_value=False):
            font = pdf_generator.register_fonts()
            assert font == "Helvetica"

    def test_register_fonts_exception(self):
        """Test font registration when exception occurs"""
        with patch("os.path.exists", return_value=True), patch(
            "pdf_generator.pdfmetrics.registerFont", side_effect=Exception("Font error")
        ), patch("pdf_generator.TTFont"):
            font = pdf_generator.register_fonts()
            # Should fallback to Helvetica after trying all paths
            assert font == "Helvetica"

    def test_generate_resume_pdf_json_languages(self):
        """Test PDF generation with languages as JSON string"""
        user_data = {
            "full_name": "Test User",
            "languages": '[{"lang_name": "English", "level_key": "level_b2"}]',
            "profession": "prof_backend",
        }
        with patch("pdf_generator.register_fonts", return_value="Helvetica"), patch(
            "pdf_generator.get_text_by_lang", side_effect=lambda k, l: k
        ):
            pdf = pdf_generator.generate_resume_pdf(user_data)
            assert isinstance(pdf, io.BytesIO)
            assert pdf.getvalue().startswith(b"%PDF")

    def test_generate_resume_pdf_string_languages(self):
        """Test PDF generation with languages as simple string"""
        user_data = {"full_name": "Test User", "languages": "English, Russian"}
        with patch("pdf_generator.register_fonts", return_value="Helvetica"):
            pdf = pdf_generator.generate_resume_pdf(user_data)
            assert isinstance(pdf, io.BytesIO)

    def test_generate_resume_pdf_json_error(self):
        """Test PDF generation with malformed JSON in languages"""
        user_data = {"full_name": "Test User", "languages": "[invalid json"}
        with patch("pdf_generator.register_fonts", return_value="Helvetica"):
            pdf = pdf_generator.generate_resume_pdf(user_data)
            assert isinstance(pdf, io.BytesIO)
