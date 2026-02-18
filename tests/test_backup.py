import os
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import database.backup  # noqa: E402


@pytest.fixture
def backup_dir(tmp_path):
    """Create a temporary backup directory."""
    dir_path = tmp_path / "backups"
    dir_path.mkdir()
    # Patch the BACKUP_DIR constant in the backup module
    with patch.object(database.backup, "BACKUP_DIR", str(dir_path)):
        yield str(dir_path)


def test_cleanup_old_backups(backup_dir):
    """Test that old backups are cleaned up correctly."""
    # Create more files than should be kept
    file_names = []
    for i in range(7):
        file_path = os.path.join(backup_dir, f"backup_20260101_00000{i}.db")
        with open(file_path, "w") as f:
            f.write("test")
        # We need to manually set modification times to ensure order
        os.utime(file_path, (time.time() + i, time.time() + i))
        file_names.append(file_path)

    # By default, it keeps 5
    database.backup.cleanup_old_backups(keep_last=5)

    remaining_files = os.listdir(backup_dir)
    assert len(remaining_files) == 5
    # The first two (oldest) files should be deleted
    assert os.path.basename(file_names[0]) not in remaining_files
    assert os.path.basename(file_names[1]) not in remaining_files
    # The last five (newest) files should remain
    assert os.path.basename(file_names[2]) in remaining_files
    assert os.path.basename(file_names[6]) in remaining_files


def test_cleanup_not_enough_backups(backup_dir):
    """Test cleanup when there are fewer backups than the keep limit."""
    # Create 3 files
    for i in range(3):
        file_path = os.path.join(backup_dir, f"backup_20260101_00000{i}.db")
        with open(file_path, "w") as f:
            f.write("test")

    database.backup.cleanup_old_backups(keep_last=5)

    # No files should be deleted
    assert len(os.listdir(backup_dir)) == 3


def test_cleanup_no_backup_dir():
    """Test cleanup when the backup directory does not exist."""
    # Patch BACKUP_DIR to a non-existent directory
    with patch.object(database.backup, "BACKUP_DIR", "non_existent_dir"):
        # The function should run without errors
        database.backup.cleanup_old_backups()
        # And the directory should not be created
        assert not os.path.exists("non_existent_dir")


def test_create_backup_success(backup_dir):
    """Test successful backup creation."""
    with patch("database.backup.get_connection") as mock_get_conn, patch(
        "sqlite3.connect"
    ) as mock_connect, patch("database.backup.cleanup_old_backups") as mock_cleanup:

        mock_src_conn = MagicMock()
        mock_dst_conn = MagicMock()
        mock_get_conn.return_value = mock_src_conn
        mock_connect.return_value = mock_dst_conn

        success, path = database.backup.create_backup()

        assert success is True
        assert "backup_" in path
        mock_src_conn.backup.assert_called_with(mock_dst_conn)
        mock_dst_conn.close.assert_called()
        mock_cleanup.assert_called()


def test_create_backup_failure(backup_dir):
    """Test backup creation failure."""
    with patch("database.backup.get_connection", side_effect=Exception("DB Error")):
        success, error = database.backup.create_backup()
        assert success is False
        assert "DB Error" in error
