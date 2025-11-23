#!/usr/bin/env python3
"""
Critical path tests for members_to_sqlite.py
Focuses on essential functionality without exhaustive coverage
"""

import pytest
import sqlite3
import tempfile
from unittest.mock import patch, MagicMock

import members_to_sqlite


class TestDatabaseSetup:
    """Test database initialization - critical for all operations"""

    def test_database_creates_tables(self, tmp_path):
        """Test database creates all required tables"""
        db_file = tmp_path / "test.db"
        original_db = members_to_sqlite.DATABASE_FILE
        members_to_sqlite.DATABASE_FILE = str(db_file)

        try:
            members_to_sqlite.setup_database()

            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}

            required_tables = {
                "members",
                "labels",
                "member_labels",
                "newsletters",
                "member_newsletters",
                "tiers",
                "member_tiers",
                "subscriptions",
                "sync_runs",
            }
            assert required_tables.issubset(tables)
            conn.close()
        finally:
            members_to_sqlite.DATABASE_FILE = original_db


class TestMemberInsertion:
    """Test member data operations - core business logic"""

    def test_insert_member_basic(self, tmp_path):
        """Test inserting a basic member record"""
        db_file = tmp_path / "test.db"
        original_db = members_to_sqlite.DATABASE_FILE
        members_to_sqlite.DATABASE_FILE = str(db_file)

        try:
            members_to_sqlite.setup_database()
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()

            member = {
                "id": "test_123",
                "uuid": "test-uuid",
                "email": "test@example.com",
                "name": "Test User",
                "status": "free",
                "subscribed": True,
                "created_at": "2024-01-01T00:00:00.000Z",
                "updated_at": "2024-01-01T00:00:00.000Z",
            }

            members_to_sqlite.insert_member(cursor, member)
            conn.commit()

            cursor.execute(
                "SELECT email, name FROM members WHERE id = ?", ("test_123",)
            )
            result = cursor.fetchone()
            assert result == ("test@example.com", "Test User")
            conn.close()
        finally:
            members_to_sqlite.DATABASE_FILE = original_db

    def test_insert_member_updates_existing(self, tmp_path):
        """Test inserting same member twice updates instead of duplicating"""
        db_file = tmp_path / "test.db"
        original_db = members_to_sqlite.DATABASE_FILE
        members_to_sqlite.DATABASE_FILE = str(db_file)

        try:
            members_to_sqlite.setup_database()
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()

            member_v1 = {
                "id": "test_123",
                "uuid": "test-uuid",
                "email": "test@example.com",
                "name": "Test User V1",
                "status": "free",
                "subscribed": True,
                "created_at": "2024-01-01T00:00:00.000Z",
                "updated_at": "2024-01-01T00:00:00.000Z",
            }

            member_v2 = member_v1.copy()
            member_v2["name"] = "Test User V2"
            member_v2["updated_at"] = "2024-01-02T00:00:00.000Z"

            members_to_sqlite.insert_member(cursor, member_v1)
            members_to_sqlite.insert_member(cursor, member_v2)
            conn.commit()

            cursor.execute(
                "SELECT COUNT(*), name FROM members WHERE id = ?", ("test_123",)
            )
            result = cursor.fetchone()
            assert result == (1, "Test User V2")
            conn.close()
        finally:
            members_to_sqlite.DATABASE_FILE = original_db


class TestAPFetching:
    """Test API fetching with mocked responses"""

    @patch("members_to_sqlite.make_ghost_request")
    @patch("members_to_sqlite.get_db_connection")
    def test_fetch_single_page(self, mock_db, mock_request):
        """Test fetching members from single API page"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn

        mock_request.return_value = {
            "members": [{"id": "1", "email": "user1@example.com"}],
            "meta": {"pagination": {"page": 1, "pages": 1}},
        }

        count = members_to_sqlite.fetch_and_save_members()
        assert count == 1
        assert mock_request.call_count == 1

    @patch("members_to_sqlite.make_ghost_request")
    @patch("members_to_sqlite.get_db_connection")
    def test_fetch_multiple_pages(self, mock_db, mock_request):
        """Test fetching members across multiple pages"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn

        def mock_response(endpoint, **kwargs):
            if "page=1" in endpoint:
                return {
                    "members": [{"id": "1"}],
                    "meta": {"pagination": {"page": 1, "pages": 2}},
                }
            elif "page=2" in endpoint:
                return {
                    "members": [{"id": "2"}],
                    "meta": {"pagination": {"page": 2, "pages": 2}},
                }
            return {"members": [], "meta": {"pagination": {"page": 3, "pages": 2}}}

        mock_request.side_effect = mock_response
        count = members_to_sqlite.fetch_and_save_members()
        assert count == 2
        assert mock_request.call_count == 2


class TestIncrementalSync:
    """Test incremental sync functionality"""

    def test_get_last_sync_time_empty(self):
        """Test getting last sync time when no database exists"""
        original_db = members_to_sqlite.DATABASE_FILE
        members_to_sqlite.DATABASE_FILE = "/tmp/nonexistent.db"

        try:
            result = members_to_sqlite.get_last_sync_time()
            assert result is None
        finally:
            members_to_sqlite.DATABASE_FILE = original_db

    def test_get_last_sync_time_with_history(self, tmp_path):
        """Test getting last sync time from sync history"""
        db_file = tmp_path / "test.db"
        original_db = members_to_sqlite.DATABASE_FILE
        members_to_sqlite.DATABASE_FILE = str(db_file)

        try:
            members_to_sqlite.setup_database()
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()

            test_time = "2024-01-01T12:00:00.000Z"
            cursor.execute(
                "INSERT INTO sync_runs (started_at, completed_at, status) VALUES (?, ?, ?)",
                ("2024-01-01T11:00:00.000Z", test_time, "completed"),
            )
            conn.commit()
            conn.close()

            result = members_to_sqlite.get_last_sync_time()
            assert result == test_time
        finally:
            members_to_sqlite.DATABASE_FILE = original_db


class TestSoftDelete:
    """Test soft delete functionality"""

    @patch("members_to_sqlite.make_ghost_request")
    @patch("members_to_sqlite.get_db_connection")
    @patch("members_to_sqlite.soft_delete_missing_members")
    def test_soft_delete_missing_members(self, mock_soft_delete, mock_db, mock_request):
        """Test that members missing from API are soft deleted"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn

        mock_request.return_value = {
            "members": [{"id": "1"}],
            "meta": {"pagination": {"page": 1, "pages": 1}},
        }

        mock_soft_delete.return_value = 1

        members_to_sqlite.fetch_and_save_members()

        mock_soft_delete.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
