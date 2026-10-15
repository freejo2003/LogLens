from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import AuditEvent
from apps.accounts.services import ANALYST_ROLE, assign_role
from apps.ingestion.models import SourceFile, TextSegment
from apps.search.models import IndicatorRule, MatchResult, SearchRun
from apps.search.services.indicators import create_indicator_rule
from apps.workspaces.models import Workspace


class IndicatorWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="indicator-analyst",
            password="test-password",
        )
        assign_role(self.user, ANALYST_ROLE)
        self.workspace = Workspace.objects.create(name="Ops", owner=self.user)
        self.source_file = SourceFile.objects.create(
            workspace=self.workspace,
            owner=self.user,
            original_name="application.log",
            storage_key="uploads/indicator-test.log",
            storage_path="private_media/uploads/indicator-test.log",
            extension=".log",
            detected_type="text/plain",
            byte_size=22,
            checksum="a" * 64,
            extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
        )
        self.segment = TextSegment.objects.create(
            source_file=self.source_file,
            sequence=1,
            text="WARN database timeout",
            line_number=7,
            parser_name="text",
            parser_version="1.1",
        )
        self.rule = create_indicator_rule(
            owner=self.user,
            workspace=self.workspace,
            name="Database timeout",
            pattern="database timeout",
            description="Database calls exceeded their time limit.",
        )
        self.client.force_login(self.user)

    def test_indicator_page_lists_rules_and_editor(self):
        response = self.client.get(reverse("search:indicators"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Database timeout")
        self.assertContains(response, "database timeout")
        self.assertContains(response, reverse("search:indicator-edit", args=[self.rule.pk]))

    def test_saved_indicator_runs_as_literal_search_and_records_rule(self):
        response = self.client.post(
            reverse("search:run"),
            {
                "workspace": self.workspace.pk,
                "source_file": self.source_file.pk,
                "indicator_rule": self.rule.pk,
                "pattern": "",
                "algorithm": "kmp",
                "case_sensitive": "on",
                "unicode_normalization": "none",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        run = SearchRun.objects.get(owner=self.user)
        self.assertEqual(run.pattern, "database timeout")
        self.assertEqual(run.indicator_rule_id, self.rule.pk)
        self.assertEqual(run.indicator_name_snapshot, "Database timeout")
        self.assertEqual(run.total_match_count, 1)
        self.assertEqual(MatchResult.objects.get(search_run=run).segment_id, self.segment.pk)
        self.assertContains(response, "Indicator rule: <span class=\"fw-semibold\">Database timeout")
        self.assertTrue(
            AuditEvent.objects.filter(
                actor=self.user,
                action=AuditEvent.Action.SEARCH_COMPLETED,
                object_id=str(run.pk),
                details__indicator_rule_id=self.rule.pk,
            ).exists()
        )

    def test_indicator_pattern_and_custom_pattern_are_mutually_exclusive(self):
        response = self.client.post(
            reverse("search:run"),
            {
                "workspace": self.workspace.pk,
                "source_file": self.source_file.pk,
                "indicator_rule": self.rule.pk,
                "pattern": "WARN",
                "algorithm": "kmp",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose either a custom pattern")
        self.assertFalse(SearchRun.objects.exists())

    def test_indicator_rule_can_be_edited_and_audited(self):
        response = self.client.post(
            reverse("search:indicator-edit", args=[self.rule.pk]),
            {
                "workspace": self.workspace.pk,
                "name": "Slow database",
                "pattern": "database slow",
                "description": "Updated rule.",
                "is_active": "on",
            },
        )

        self.assertRedirects(response, reverse("search:indicators"))
        self.rule.refresh_from_db()
        self.assertEqual(self.rule.name, "Slow database")
        self.assertEqual(self.rule.pattern, "database slow")
        self.assertTrue(
            AuditEvent.objects.filter(
                actor=self.user,
                action=AuditEvent.Action.INDICATOR_RULE_UPDATED,
                object_id=str(self.rule.pk),
            ).exists()
        )

    def test_foreign_indicator_cannot_be_edited_or_used(self):
        other = get_user_model().objects.create_user(
            username="other-indicator-owner",
            password="test-password",
        )
        assign_role(other, ANALYST_ROLE)
        other_workspace = Workspace.objects.create(name="Other", owner=other)
        other_rule = IndicatorRule.objects.create(
            workspace=other_workspace,
            owner=other,
            name="Private rule",
            pattern="secret",
        )

        response = self.client.get(reverse("search:indicator-edit", args=[other_rule.pk]))
        self.assertEqual(response.status_code, 404)

        post = self.client.post(
            reverse("search:run"),
            {
                "workspace": self.workspace.pk,
                "source_file": self.source_file.pk,
                "indicator_rule": other_rule.pk,
                "pattern": "",
                "algorithm": "kmp",
            },
        )
        self.assertEqual(post.status_code, 200)
        self.assertFalse(SearchRun.objects.exists())
