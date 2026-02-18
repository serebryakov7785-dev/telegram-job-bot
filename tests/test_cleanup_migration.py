import os
import sys
from unittest.mock import patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import cleanup_migration  # noqa: E402


class TestCleanupMigration:
    def test_cleanup_files_exist(self):
        """Test cleanup when files exist"""
        with patch("os.path.exists", return_value=True), patch(
            "os.remove"
        ) as mock_remove, patch("builtins.print"):

            cleanup_migration.cleanup()

            # Should try to remove all files in the list
            # files_to_remove has 5 items in the script
            assert mock_remove.call_count == 5

    def test_cleanup_files_not_exist(self):
        """Test cleanup when files do not exist"""
        with patch("os.path.exists", return_value=False), patch(
            "os.remove"
        ) as mock_remove, patch("builtins.print"):

            cleanup_migration.cleanup()

            mock_remove.assert_not_called()

    def test_cleanup_remove_error(self):
        """Test cleanup when removal fails."""
        with patch("os.path.exists", return_value=True), patch(
            "os.remove", side_effect=Exception("Error")
        ), patch("builtins.print") as mock_print:

            cleanup_migration.cleanup()

            # Should print error messages
            # 1 initial print + 5 error prints + 1 final print = 7
            assert mock_print.call_count >= 5
