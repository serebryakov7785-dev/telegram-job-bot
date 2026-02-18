import os
import sys
from unittest.mock import patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import cleanup  # noqa: E402


class TestCleanup:
    @pytest.fixture
    def mock_paths(self):
        with patch("os.path.exists") as mock_exists, patch(
            "os.path.isdir"
        ) as mock_isdir, patch("shutil.rmtree") as mock_rmtree, patch(
            "os.remove"
        ) as mock_remove, patch(
            "os.walk"
        ) as mock_walk:
            yield {
                "exists": mock_exists,
                "isdir": mock_isdir,
                "rmtree": mock_rmtree,
                "remove": mock_remove,
                "walk": mock_walk,
            }

    def test_clean_removes_directory(self, mock_paths):
        """Test removing an existing directory"""
        mock_paths["exists"].return_value = True
        mock_paths["isdir"].return_value = True
        mock_paths["walk"].return_value = []  # No files to walk

        cleanup.clean()

        assert mock_paths["rmtree"].call_count >= 1

    def test_clean_removes_file(self, mock_paths):
        """Test removing an existing file"""
        mock_paths["exists"].return_value = True
        mock_paths["isdir"].return_value = False
        mock_paths["walk"].return_value = []

        cleanup.clean()

        assert mock_paths["remove"].call_count >= 1

    def test_clean_handles_errors(self, mock_paths):
        """Test error handling during removal"""
        mock_paths["exists"].return_value = True
        mock_paths["isdir"].return_value = True
        mock_paths["rmtree"].side_effect = Exception("Permission denied")
        mock_paths["walk"].return_value = []

        # Should not raise exception
        cleanup.clean()

    def test_clean_pycache(self, mock_paths):
        """Test cleaning __pycache__ and .pyc files"""
        mock_paths["exists"].return_value = False  # Main paths don't exist
        # Simulate os.walk yielding a __pycache__ dir and a .pyc file
        mock_paths["walk"].return_value = [
            ("/root", ["__pycache__"], ["test.pyc", "test.py"])
        ]

        cleanup.clean()

        mock_paths["rmtree"].assert_called_with(
            os.path.join("/root", "__pycache__"), ignore_errors=True
        )
        mock_paths["remove"].assert_called_with(os.path.join("/root", "test.pyc"))
