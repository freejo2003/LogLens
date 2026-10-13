from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.ingestion.models import SourceFile, TextSegment
from apps.search.models import ErrorGroup, GroupMember
from apps.search.services.error_groups import (
    build_error_group_name,
    create_or_get_error_group,
    extract_log_level,
    group_segment,
    group_source_file,
    is_groupable_log_message,
    normalize_error_message,
    rebuild_error_groups_for_source_file,
)
from apps.workspaces.models import Workspace


class ErrorGroupServiceTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="error-group-user",
            password="test-password",
        )

        self.workspace = Workspace.objects.create(
            name="Error Group Workspace",
            description="Workspace for error grouping tests.",
            owner=self.user,
        )

        self.source_file = SourceFile.objects.create(
            workspace=self.workspace,
            owner=self.user,
            original_name="application.log",
            storage_key="uploads/test-error-groups.log",
            storage_path="C:/test/application.log",
            extension=".log",
            detected_type="text/plain",
            byte_size=100,
            checksum="a" * 64,
            extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
        )

    def create_segment(self, sequence, text):
        return TextSegment.objects.create(
            source_file=self.source_file,
            sequence=sequence,
            text=text,
            line_number=sequence,
            parser_name="test",
            parser_version="1.0",
        )

    def test_extract_log_level_returns_error(self):
        text = (
            "2026-10-12 09:03:10 ERROR "
            "Database connection failed"
        )

        self.assertEqual(
            extract_log_level(text),
            "ERROR",
        )

    def test_extract_log_level_returns_warn(self):
        text = (
            "2026-10-12 09:02:44 WARN "
            "Database connection pool reached 80 percent"
        )

        self.assertEqual(
            extract_log_level(text),
            "WARN",
        )

    def test_extract_log_level_returns_info(self):
        text = (
            "2026-10-12 09:00:01 INFO "
            "Application started successfully"
        )

        self.assertEqual(
            extract_log_level(text),
            "INFO",
        )

    def test_extract_log_level_returns_none_for_invalid_format(self):
        text = "Database connection failed"

        self.assertIsNone(
            extract_log_level(text),
        )

    def test_error_message_is_groupable(self):
        text = (
            "2026-10-12 09:03:10 ERROR "
            "Database connection failed"
        )

        self.assertTrue(
            is_groupable_log_message(text),
        )

    def test_warn_message_is_groupable(self):
        text = (
            "2026-10-12 09:02:44 WARN "
            "Database connection pool reached 80 percent"
        )

        self.assertTrue(
            is_groupable_log_message(text),
        )

    def test_info_message_is_not_groupable(self):
        text = (
            "2026-10-12 09:00:01 INFO "
            "Application started successfully"
        )

        self.assertFalse(
            is_groupable_log_message(text),
        )

    def test_invalid_message_is_not_groupable(self):
        text = "Database connection failed"

        self.assertFalse(
            is_groupable_log_message(text),
        )

    def test_normalization_removes_timestamp_and_log_level(self):
        text = (
            "2026-10-12 09:03:10 ERROR "
            "Database connection failed"
        )

        self.assertEqual(
            normalize_error_message(text),
            "database connection failed",
        )

    def test_normalization_is_case_insensitive(self):
        first = normalize_error_message(
            "2026-10-12 09:03:10 ERROR Database Connection Failed"
        )
        second = normalize_error_message(
            "2026-10-12 09:03:11 error DATABASE CONNECTION FAILED"
        )

        self.assertEqual(first, second)

    def test_normalization_removes_key_value_metadata(self):
        text = (
            "2026-10-12 09:06:01 ERROR "
            "Authentication failed user=alice"
        )

        self.assertEqual(
            normalize_error_message(text),
            "authentication failed",
        )

    def test_normalization_removes_path_metadata(self):
        text = (
            "2026-10-12 09:10:22 ERROR "
            "File not found path=/reports/daily.csv"
        )

        self.assertEqual(
            normalize_error_message(text),
            "file not found",
        )

    def test_normalization_preserves_http_status(self):
        text = (
            "2026-10-12 09:08:42 ERROR "
            "HTTP 500 Internal Server Error endpoint=/api/orders"
        )

        self.assertEqual(
            normalize_error_message(text),
            "http 500 internal server error",
        )

    def test_normalization_removes_duration_metadata(self):
        text = (
            "2026-10-12 09:05:33 WARN "
            "Request took longer than expected duration=3200ms"
        )

        self.assertEqual(
            normalize_error_message(text),
            "request took longer than expected",
        )

    def test_empty_message_normalizes_to_empty_string(self):
        self.assertEqual(
            normalize_error_message("   "),
            "",
        )

    def test_normalization_rejects_non_string(self):
        with self.assertRaises(TypeError):
            normalize_error_message(None)

    def test_group_name_is_truncated_to_255_characters(self):
        normalized_message = "x" * 300

        group_name = build_error_group_name(normalized_message)

        self.assertEqual(len(group_name), 255)

    def test_create_or_get_returns_same_group(self):
        normalized_message = "database connection failed"

        first = create_or_get_error_group(
            owner=self.user,
            workspace=self.workspace,
            normalized_message=normalized_message,
        )

        second = create_or_get_error_group(
            owner=self.user,
            workspace=self.workspace,
            normalized_message=normalized_message,
        )

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(ErrorGroup.objects.count(), 1)

    def test_different_normalized_messages_create_different_groups(self):
        first = create_or_get_error_group(
            owner=self.user,
            workspace=self.workspace,
            normalized_message="database connection failed",
        )

        second = create_or_get_error_group(
            owner=self.user,
            workspace=self.workspace,
            normalized_message="authentication failed",
        )

        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(ErrorGroup.objects.count(), 2)

    def test_group_segment_creates_membership_for_error(self):
        segment = self.create_segment(
            1,
            "2026-10-12 09:03:10 ERROR Database connection failed",
        )

        member = group_segment(
            owner=self.user,
            workspace=self.workspace,
            source_file=self.source_file,
            segment=segment,
        )

        self.assertIsNotNone(member)
        self.assertEqual(GroupMember.objects.count(), 1)

        group = ErrorGroup.objects.get()

        self.assertEqual(
            group.normalized_message,
            "database connection failed",
        )
        self.assertEqual(group.occurrence_count, 1)

    def test_group_segment_creates_membership_for_warn(self):
        segment = self.create_segment(
            1,
            "2026-10-12 09:02:44 WARN Database connection pool reached 80 percent",
        )

        member = group_segment(
            owner=self.user,
            workspace=self.workspace,
            source_file=self.source_file,
            segment=segment,
        )

        self.assertIsNotNone(member)
        self.assertEqual(GroupMember.objects.count(), 1)

        group = ErrorGroup.objects.get()

        self.assertEqual(
            group.normalized_message,
            "database connection pool reached 80 percent",
        )
        self.assertEqual(group.occurrence_count, 1)

    def test_group_segment_ignores_info(self):
        segment = self.create_segment(
            1,
            "2026-10-12 09:00:01 INFO Application started successfully",
        )

        result = group_segment(
            owner=self.user,
            workspace=self.workspace,
            source_file=self.source_file,
            segment=segment,
        )

        self.assertIsNone(result)
        self.assertEqual(ErrorGroup.objects.count(), 0)
        self.assertEqual(GroupMember.objects.count(), 0)

    def test_repeated_identical_errors_share_one_group(self):
        first = self.create_segment(
            1,
            "2026-10-12 09:03:10 ERROR Database connection failed",
        )
        second = self.create_segment(
            2,
            "2026-10-12 09:03:11 ERROR Database connection failed",
        )
        third = self.create_segment(
            3,
            "2026-10-12 09:03:12 ERROR Database connection failed",
        )

        group_segment(
            owner=self.user,
            workspace=self.workspace,
            source_file=self.source_file,
            segment=first,
        )
        group_segment(
            owner=self.user,
            workspace=self.workspace,
            source_file=self.source_file,
            segment=second,
        )
        group_segment(
            owner=self.user,
            workspace=self.workspace,
            source_file=self.source_file,
            segment=third,
        )

        self.assertEqual(ErrorGroup.objects.count(), 1)
        self.assertEqual(GroupMember.objects.count(), 3)

        group = ErrorGroup.objects.get()

        self.assertEqual(
            group.normalized_message,
            "database connection failed",
        )
        self.assertEqual(group.occurrence_count, 3)

    def test_dynamic_user_values_share_one_group(self):
        alice = self.create_segment(
            1,
            "2026-10-12 09:06:01 ERROR Authentication failed user=alice",
        )
        bob = self.create_segment(
            2,
            "2026-10-12 09:06:05 ERROR Authentication failed user=bob",
        )

        group_segment(
            owner=self.user,
            workspace=self.workspace,
            source_file=self.source_file,
            segment=alice,
        )
        group_segment(
            owner=self.user,
            workspace=self.workspace,
            source_file=self.source_file,
            segment=bob,
        )

        self.assertEqual(ErrorGroup.objects.count(), 1)
        self.assertEqual(GroupMember.objects.count(), 2)

        group = ErrorGroup.objects.get()

        self.assertEqual(
            group.normalized_message,
            "authentication failed",
        )
        self.assertEqual(group.occurrence_count, 2)

    def test_dynamic_paths_share_one_group(self):
        daily = self.create_segment(
            1,
            "2026-10-12 09:10:22 ERROR File not found path=/reports/daily.csv",
        )
        monthly = self.create_segment(
            2,
            "2026-10-12 09:11:04 ERROR File not found path=/reports/monthly.csv",
        )

        group_segment(
            owner=self.user,
            workspace=self.workspace,
            source_file=self.source_file,
            segment=daily,
        )
        group_segment(
            owner=self.user,
            workspace=self.workspace,
            source_file=self.source_file,
            segment=monthly,
        )

        self.assertEqual(ErrorGroup.objects.count(), 1)
        self.assertEqual(GroupMember.objects.count(), 2)

        group = ErrorGroup.objects.get()

        self.assertEqual(
            group.normalized_message,
            "file not found",
        )
        self.assertEqual(group.occurrence_count, 2)

    def test_http_status_remains_part_of_group_template(self):
        segment = self.create_segment(
            1,
            "2026-10-12 09:08:42 ERROR "
            "HTTP 500 Internal Server Error endpoint=/api/orders",
        )

        group_segment(
            owner=self.user,
            workspace=self.workspace,
            source_file=self.source_file,
            segment=segment,
        )

        group = ErrorGroup.objects.get()

        self.assertEqual(
            group.normalized_message,
            "http 500 internal server error",
        )

    def test_duplicate_membership_is_not_created(self):
        segment = self.create_segment(
            1,
            "2026-10-12 09:03:10 ERROR Database connection failed",
        )

        first = group_segment(
            owner=self.user,
            workspace=self.workspace,
            source_file=self.source_file,
            segment=segment,
        )

        second = group_segment(
            owner=self.user,
            workspace=self.workspace,
            source_file=self.source_file,
            segment=segment,
        )

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(GroupMember.objects.count(), 1)

        group = ErrorGroup.objects.get()

        self.assertEqual(group.occurrence_count, 1)

    def test_empty_segment_is_ignored(self):
        segment = self.create_segment(1, "   ")

        result = group_segment(
            owner=self.user,
            workspace=self.workspace,
            source_file=self.source_file,
            segment=segment,
        )

        self.assertIsNone(result)
        self.assertEqual(ErrorGroup.objects.count(), 0)
        self.assertEqual(GroupMember.objects.count(), 0)

    def test_group_source_file_matches_full_standard_dataset(self):
        lines = [
            "2026-10-12 09:00:01 INFO Application started successfully",
            "2026-10-12 09:00:03 INFO Connected to PostgreSQL database",
            "2026-10-12 09:00:05 INFO Redis connection established",
            "2026-10-12 09:01:12 INFO User login successful user=admin",
            "2026-10-12 09:02:44 WARN Database connection pool reached 80 percent",
            "2026-10-12 09:03:10 ERROR Database connection failed",
            "2026-10-12 09:03:11 ERROR Database connection failed",
            "2026-10-12 09:03:12 ERROR Database connection failed",
            "2026-10-12 09:04:20 INFO Database connection restored",
            "2026-10-12 09:05:33 WARN Request took longer than expected duration=3200ms",
            "2026-10-12 09:06:01 ERROR Authentication failed user=alice",
            "2026-10-12 09:06:05 ERROR Authentication failed user=bob",
            "2026-10-12 09:07:15 INFO User login successful user=admin",
            "2026-10-12 09:08:42 ERROR HTTP 500 Internal Server Error endpoint=/api/orders",
            "2026-10-12 09:08:43 ERROR HTTP 500 Internal Server Error endpoint=/api/orders",
            "2026-10-12 09:09:01 INFO HTTP request completed status=200",
            "2026-10-12 09:10:22 ERROR File not found path=/reports/daily.csv",
            "2026-10-12 09:11:04 ERROR File not found path=/reports/monthly.csv",
            "2026-10-12 09:12:30 WARN Disk usage exceeded 85 percent",
            "2026-10-12 09:13:15 INFO Scheduled backup started",
            "2026-10-12 09:14:20 ERROR Backup failed reason=connection timeout",
            "2026-10-12 09:15:00 INFO Scheduled backup completed",
            "2026-10-12 09:16:11 ERROR Timeout while connecting to external service",
            "2026-10-12 09:16:12 ERROR Timeout while connecting to external service",
            "2026-10-12 09:17:45 INFO External service connection restored",
            "2026-10-12 09:18:30 INFO Application health check passed",
        ]

        for sequence, line in enumerate(lines, start=1):
            self.create_segment(sequence, line)

        members = group_source_file(
            owner=self.user,
            source_file=self.source_file,
        )

        self.assertEqual(len(members), 15)
        self.assertEqual(GroupMember.objects.count(), 15)
        self.assertEqual(ErrorGroup.objects.count(), 9)

        groups = {
            group.normalized_message: group.occurrence_count
            for group in ErrorGroup.objects.all()
        }

        self.assertEqual(
            groups,
            {
                "database connection failed": 3,
                "authentication failed": 2,
                "http 500 internal server error": 2,
                "file not found": 2,
                "timeout while connecting to external service": 2,
                "database connection pool reached 80 percent": 1,
                "request took longer than expected": 1,
                "disk usage exceeded 85 percent": 1,
                "backup failed timeout": 1,
            },
        )

    def test_rebuild_error_groups_removes_stale_memberships(self):
        lines = [
            "2026-10-12 09:00:01 INFO Application started successfully",
            "2026-10-12 09:02:44 WARN Database connection pool reached 80 percent",
            "2026-10-12 09:03:10 ERROR Database connection failed",
            "2026-10-12 09:03:11 ERROR Database connection failed",
            "2026-10-12 09:03:12 ERROR Database connection failed",
        ]

        for sequence, line in enumerate(lines, start=1):
            self.create_segment(sequence, line)

        stale_group = create_or_get_error_group(
            owner=self.user,
            workspace=self.workspace,
            normalized_message="stale info group",
        )

        GroupMember.objects.create(
            error_group=stale_group,
            source_file=self.source_file,
            segment=TextSegment.objects.get(sequence=1),
        )

        stale_group.occurrence_count = 1
        stale_group.save(update_fields=["occurrence_count"])

        members = rebuild_error_groups_for_source_file(
            owner=self.user,
            source_file=self.source_file,
        )

        self.assertEqual(len(members), 4)
        self.assertEqual(GroupMember.objects.count(), 4)
        self.assertEqual(ErrorGroup.objects.count(), 2)

        groups = {
            group.normalized_message: group.occurrence_count
            for group in ErrorGroup.objects.all()
        }

        self.assertEqual(
            groups,
            {
                "database connection failed": 3,
                "database connection pool reached 80 percent": 1,
            },
        )

    def test_rebuild_error_groups_is_idempotent(self):
        lines = [
            "2026-10-12 09:03:10 ERROR Database connection failed",
            "2026-10-12 09:03:11 ERROR Database connection failed",
            "2026-10-12 09:02:44 WARN Database connection pool reached 80 percent",
        ]

        for sequence, line in enumerate(lines, start=1):
            self.create_segment(sequence, line)

        first_members = rebuild_error_groups_for_source_file(
            owner=self.user,
            source_file=self.source_file,
        )

        first_groups = {
            group.normalized_message: group.occurrence_count
            for group in ErrorGroup.objects.all()
        }

        second_members = rebuild_error_groups_for_source_file(
            owner=self.user,
            source_file=self.source_file,
        )

        second_groups = {
            group.normalized_message: group.occurrence_count
            for group in ErrorGroup.objects.all()
        }

        self.assertEqual(len(first_members), 3)
        self.assertEqual(len(second_members), 3)

        self.assertEqual(
            first_groups,
            second_groups,
        )

        self.assertEqual(GroupMember.objects.count(), 3)
        self.assertEqual(ErrorGroup.objects.count(), 2)