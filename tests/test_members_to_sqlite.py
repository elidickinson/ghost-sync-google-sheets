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
from members_to_sqlite import database


class TestDatabaseSetup:
    """Test database initialization - critical for all operations"""

    def test_database_creates_tables(self, tmp_path):
        """Test database creates all required tables"""
        db_file = tmp_path / "test.db"
        original_db = members_to_sqlite.DATABASE_FILE
        original_database = members_to_sqlite.database
        members_to_sqlite.DATABASE_FILE = str(db_file)
        members_to_sqlite.database = members_to_sqlite.SqliteDatabase(str(db_file))

        try:
            members_to_sqlite.setup_database()
            members_to_sqlite.database.close()

            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}

            required_tables = {
                "member",
                "label",
                "member_label",
                "newsletter",
                "member_newsletter",
                "tier",
                "member_tier",
                "subscription",
                "sync_run",
            }
            print(f"Actual tables: {tables}")
            assert required_tables.issubset(tables)
            conn.close()
        finally:
            members_to_sqlite.DATABASE_FILE = original_db
            members_to_sqlite.database = original_database


class TestMemberInsertion:
    """Test member data operations - core business logic"""

    def test_insert_member_basic(self, tmp_path):
        """Test inserting a basic member record"""
        db_file = tmp_path / "test.db"
        original_db = members_to_sqlite.DATABASE_FILE
        original_database = members_to_sqlite.database
        members_to_sqlite.DATABASE_FILE = str(db_file)
        members_to_sqlite.database = members_to_sqlite.SqliteDatabase(str(db_file))

        try:
            members_to_sqlite.setup_database()
            members_to_sqlite.database.close()
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

            members_to_sqlite.database.connect()
            members_to_sqlite.insert_member(member)
            members_to_sqlite.database.commit()

            cursor.execute(
                "SELECT email, name FROM member WHERE id = ?", ("test_123",)
            )
            result = cursor.fetchone()
            assert result == ("test@example.com", "Test User")
            members_to_sqlite.database.close()
            conn.close()
        finally:
            members_to_sqlite.DATABASE_FILE = original_db
            members_to_sqlite.database = original_database

    def test_insert_member_updates_existing(self, tmp_path):
        """Test inserting same member twice updates instead of duplicating"""
        db_file = tmp_path / "test.db"
        original_db = members_to_sqlite.DATABASE_FILE
        original_database = members_to_sqlite.database
        members_to_sqlite.DATABASE_FILE = str(db_file)
        members_to_sqlite.database = members_to_sqlite.SqliteDatabase(str(db_file))

        try:
            members_to_sqlite.setup_database()
            members_to_sqlite.database.close()
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

            members_to_sqlite.database.connect()
            members_to_sqlite.insert_member(member_v1)
            members_to_sqlite.insert_member(member_v2)
            members_to_sqlite.database.commit()

            cursor.execute(
                "SELECT COUNT(*), name FROM member WHERE id = ?", ("test_123",)
            )
            result = cursor.fetchone()
            assert result == (1, "Test User V2")
            members_to_sqlite.database.close()
            conn.close()
        finally:
            members_to_sqlite.DATABASE_FILE = original_db
            members_to_sqlite.database = original_database


class TestAPFetching:
    """Test API fetching with mocked responses"""

    @patch("members_to_sqlite.make_ghost_request")
    def test_fetch_single_page(self, mock_request, tmp_path):
        """Test fetching members from single API page"""
        # Set up test database
        db_file = tmp_path / "test.db"
        original_db = members_to_sqlite.DATABASE_FILE
        original_database = members_to_sqlite.database
        members_to_sqlite.DATABASE_FILE = str(db_file)
        members_to_sqlite.database = members_to_sqlite.SqliteDatabase(str(db_file))

        try:
            members_to_sqlite.setup_database()

            mock_request.return_value = {
                "members": [
                    {
                        "id": "1",
                        "uuid": "test-uuid-1",
                        "email": "user1@example.com",
                        "name": "Test User",
                        "status": "free",
                        "subscribed": True,
                        "created_at": "2024-01-01T00:00:00.000Z",
                        "updated_at": "2024-01-01T00:00:00.000Z",
                    }
                ],
                "meta": {"pagination": {"page": 1, "pages": 1}},
            }

            count = members_to_sqlite.fetch_and_save_members()
            assert count == 1
            assert mock_request.call_count == 1
        finally:
            members_to_sqlite.DATABASE_FILE = original_db
            members_to_sqlite.database = original_database

    @patch("members_to_sqlite.make_ghost_request")
    def test_fetch_multiple_pages(self, mock_request, tmp_path):
        """Test fetching members across multiple pages"""
        # Set up test database
        db_file = tmp_path / "test.db"
        original_db = members_to_sqlite.DATABASE_FILE
        original_database = members_to_sqlite.database
        members_to_sqlite.DATABASE_FILE = str(db_file)
        members_to_sqlite.database = members_to_sqlite.SqliteDatabase(str(db_file))

        try:
            members_to_sqlite.setup_database()

            def mock_response(endpoint, **kwargs):
                if "page=1" in endpoint:
                    return {
                        "members": [
                            {
                                "id": "1",
                                "uuid": "test-uuid-1",
                                "email": "user1@example.com",
                                "name": "Test User",
                                "status": "free",
                                "subscribed": True,
                                "created_at": "2024-01-01T00:00:00.000Z",
                                "updated_at": "2024-01-01T00:00:00.000Z",
                            }
                        ],
                        "meta": {"pagination": {"page": 1, "pages": 2}},
                    }
                elif "page=2" in endpoint:
                    return {
                        "members": [
                            {
                                "id": "2",
                                "uuid": "test-uuid-2",
                                "email": "user2@example.com",
                                "name": "Test User 2",
                                "status": "free",
                                "subscribed": True,
                                "created_at": "2024-01-01T00:00:00.000Z",
                                "updated_at": "2024-01-01T00:00:00.000Z",
                            }
                        ],
                        "meta": {"pagination": {"page": 2, "pages": 2}},
                    }
                return {"members": [], "meta": {"pagination": {"page": 3, "pages": 2}}}

            mock_request.side_effect = mock_response
            count = members_to_sqlite.fetch_and_save_members()
            assert count == 2
        finally:
            members_to_sqlite.DATABASE_FILE = original_db
            members_to_sqlite.database = original_database
        assert mock_request.call_count == 2


class TestIncrementalSync:
    """Test incremental sync functionality"""

    def test_get_last_sync_time_empty(self):
        """Test getting last sync time when no database exists"""
        original_db = members_to_sqlite.DATABASE_FILE
        original_database = members_to_sqlite.database
        members_to_sqlite.DATABASE_FILE = "/tmp/nonexistent_test.db"
        members_to_sqlite.database = members_to_sqlite.SqliteDatabase(
            "/tmp/nonexistent_test.db"
        )

        try:
            # Force close any existing connection
            if not members_to_sqlite.database.is_closed():
                members_to_sqlite.database.close()
            result = members_to_sqlite.get_last_sync_time()
            assert result is None
        finally:
            members_to_sqlite.DATABASE_FILE = original_db
            members_to_sqlite.database = original_database

    def test_get_last_sync_time_with_history(self, tmp_path):
        """Test getting last sync time from sync history"""
        db_file = tmp_path / "test.db"
        original_db = members_to_sqlite.DATABASE_FILE
        original_database = members_to_sqlite.database
        members_to_sqlite.DATABASE_FILE = str(db_file)
        members_to_sqlite.database = members_to_sqlite.SqliteDatabase(str(db_file))

        try:
            members_to_sqlite.setup_database()
            members_to_sqlite.database.close()  # Close connection from setup

            test_time = "2024-01-01T12:00:00.000Z"
            members_to_sqlite.database.connect()
            members_to_sqlite.SyncRun.create(
                started_at="2024-01-01T11:00:00.000Z",
                completed_at=test_time,
                status="completed",
            )
            members_to_sqlite.database.commit()
            members_to_sqlite.database.close()

            result = members_to_sqlite.get_last_sync_time()
            assert result == test_time
        finally:
            members_to_sqlite.DATABASE_FILE = original_db
            members_to_sqlite.database = original_database


class TestSoftDelete:
    """Test soft delete functionality"""

    @patch("members_to_sqlite.make_ghost_request")
    @patch("members_to_sqlite.soft_delete_missing_members")
    def test_soft_delete_missing_members(
        self, mock_soft_delete, mock_request, tmp_path
    ):
        """Test that members missing from API are soft deleted"""
        # Set up test database
        db_file = tmp_path / "test.db"
        original_db = members_to_sqlite.DATABASE_FILE
        original_database = members_to_sqlite.database
        members_to_sqlite.DATABASE_FILE = str(db_file)
        members_to_sqlite.database = members_to_sqlite.SqliteDatabase(str(db_file))

        try:
            members_to_sqlite.setup_database()

            mock_request.return_value = {
                "members": [
                    {
                        "id": "1",
                        "uuid": "test-uuid-1",
                        "email": "user1@example.com",
                        "name": "Test User",
                        "status": "free",
                        "subscribed": True,
                        "created_at": "2024-01-01T00:00:00.000Z",
                        "updated_at": "2024-01-01T00:00:00.000Z",
                    }
                ],
                "meta": {"pagination": {"page": 1, "pages": 1}},
            }

            mock_soft_delete.return_value = 1

            members_to_sqlite.fetch_and_save_members()

            mock_soft_delete.assert_called_once()
        finally:
            members_to_sqlite.DATABASE_FILE = original_db
            members_to_sqlite.database = original_database


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
