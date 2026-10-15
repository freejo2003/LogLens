from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.ingestion.models import SourceFile, TextSegment
from apps.ingestion.services.deletion import delete_source_file
from apps.search.models import ErrorGroup
from apps.search.services.error_groups import (
    extract_log_level,
    is_groupable_log_message,
    rebuild_error_groups_for_source_file,
)
from apps.workspaces.models import Workspace


class ErrorGroupLifecycleTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="error-group-owner",
            password="test-password",
        )
        self.workspace = Workspace.objects.create(name="Investigation", owner=self.user)

    def create_source(self, name):
        return SourceFile.objects.create(
            workspace=self.workspace,
            owner=self.user,
            original_name=name,
            storage_key=f"uploads/{name}",
            storage_path=f"uploads/{name}",
            extension=".log",
            detected_type="text/plain",
            byte_size=64,
            checksum="c" * 64,
            extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
        )

    def add_error(self, source_file, *, timestamp, path):
        return TextSegment.objects.create(
            source_file=source_file,
            sequence=1,
            text=f"{timestamp} ERROR Disk read failed path={path}",
            line_number=1,
            parser_name="plain_text",
            parser_version="1.1",
        )

    def test_grouping_accepts_timestamped_or_bare_warning_aliases(self):
        messages = [
            "WARNING Database latency duration=12ms",
            "2026-10-15T10:01:00.250Z WARN Database latency duration=30ms",
        ]
        self.assertEqual(extract_log_level(messages[0]), "WARNING")
        self.assertTrue(all(is_groupable_log_message(message) for message in messages))

        first = self.create_source("bare-warning.log")
        second = self.create_source("timestamped-warning.log")
        for source, message in zip((first, second), messages):
            TextSegment.objects.create(
                source_file=source,
                sequence=1,
                text=message,
                line_number=1,
                parser_name="plain_text",
                parser_version="1.1",
            )
            rebuild_error_groups_for_source_file(owner=self.user, source_file=source)

        group = ErrorGroup.objects.get(workspace=self.workspace)
        self.assertEqual(group.occurrence_count, 2)

    def test_group_count_accumulates_and_rebuilds_across_source_files(self):
        first = self.create_source("first.log")
        second = self.create_source("second.log")
        self.add_error(first, timestamp="2026-10-15 10:00:00", path="/var/a")
        self.add_error(second, timestamp="2026-10-15 10:01:00", path="/var/b")

        rebuild_error_groups_for_source_file(owner=self.user, source_file=first)
        group = ErrorGroup.objects.get(workspace=self.workspace)
        self.assertEqual(group.occurrence_count, 1)

        rebuild_error_groups_for_source_file(owner=self.user, source_file=second)
        group.refresh_from_db()
        self.assertEqual(group.occurrence_count, 2)

        rebuild_error_groups_for_source_file(owner=self.user, source_file=first)
        group.refresh_from_db()
        self.assertEqual(group.occurrence_count, 2)

    def test_deleting_source_updates_and_removes_error_groups(self):
        first = self.create_source("delete-me.log")
        second = self.create_source("keep-me.log")
        self.add_error(first, timestamp="2026-10-15 10:00:00", path="/var/a")
        self.add_error(second, timestamp="2026-10-15 10:01:00", path="/var/b")
        rebuild_error_groups_for_source_file(owner=self.user, source_file=first)
        rebuild_error_groups_for_source_file(owner=self.user, source_file=second)
        group = ErrorGroup.objects.get(workspace=self.workspace)

        delete_source_file(source_file=first, owner=self.user)
        group.refresh_from_db()
        self.assertEqual(group.occurrence_count, 1)

        delete_source_file(source_file=second, owner=self.user)
        self.assertFalse(ErrorGroup.objects.filter(pk=group.pk).exists())
