from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import AuditEvent
from apps.accounts.services import ANALYST_ROLE, assign_role
from apps.ingestion.models import SourceFile, TextSegment
from apps.search.models import MatchResult, SavedSearch, SearchRun
from apps.workspaces.models import Workspace


class SearchRunWorkflowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="search-workflow-user",
            password="test-password",
        )
        self.other_user = user_model.objects.create_user(
            username="search-workflow-other",
            password="test-password",
        )
        assign_role(self.user, ANALYST_ROLE)
        assign_role(self.other_user, ANALYST_ROLE)
        self.workspace = Workspace.objects.create(name="Analysis", owner=self.user)
        self.other_workspace = Workspace.objects.create(name="Private", owner=self.other_user)
        self.source_file = SourceFile.objects.create(
            workspace=self.workspace,
            owner=self.user,
            original_name="application.log",
            storage_key="uploads/search-workflow.log",
            storage_path="uploads/search-workflow.log",
            extension=".log",
            detected_type="text/plain",
            byte_size=100,
            checksum="a" * 64,
            extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
        )
        self.segment = TextSegment.objects.create(
            source_file=self.source_file,
            sequence=1,
            text="=SUM(A1:A2) ERROR Straße",
            line_number=12,
            parser_name="plain_text",
            parser_version="1.1",
        )
        self.client.force_login(self.user)

    def run_search(self):
        return self.client.post(
            reverse("search:run"),
            {
                "workspace": self.workspace.pk,
                "source_file": self.source_file.pk,
                "pattern": "STRASSE",
                "algorithm": "kmp",
                "case_sensitive": "",
                "unicode_normalization": "NFC",
            },
            follow=True,
        )

    def test_search_saves_configuration_and_renders_source_locations(self):
        response = self.run_search()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "search/search_results.html")
        run = SearchRun.objects.get(owner=self.user)
        result = MatchResult.objects.get(search_run=run)
        self.assertEqual(result.segment_id, self.segment.pk)
        self.assertEqual(result.positions, [18])
        self.assertFalse(run.case_sensitive)
        self.assertEqual(run.unicode_normalization, "NFC")

    def test_large_result_sets_are_paginated(self):
        TextSegment.objects.bulk_create(
            [
                TextSegment(
                    source_file=self.source_file,
                    sequence=sequence,
                    text="ERROR repeated",
                    line_number=sequence,
                    parser_name="plain_text",
                    parser_version="1.1",
                )
                for sequence in range(2, 122)
            ]
        )
        response = self.client.post(
            reverse("search:run"),
            {
                "workspace": self.workspace.pk,
                "source_file": self.source_file.pk,
                "pattern": "ERROR",
                "algorithm": "kmp",
            },
            follow=True,
        )
        run = SearchRun.objects.get(owner=self.user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["match_results"].paginator.per_page, 100)
        self.assertEqual(len(response.context["match_results"].object_list), 100)
        second_page = self.client.get(
            reverse("search:history-detail", args=[run.pk]), {"page": "2"}
        )
        self.assertEqual(len(second_page.context["match_results"].object_list), 21)
        self.assertContains(response, "Next")

    def test_saved_search_can_be_rerun_with_its_snapshot(self):
        self.run_search()
        self.client.post(
            reverse("search:save"),
            {
                "workspace": self.workspace.pk,
                "source_file": self.source_file.pk,
                "name": "Unicode Errors",
                "pattern": "STRASSE",
                "algorithm": "kmp",
                "case_sensitive": "False",
                "unicode_normalization": "NFC",
                "description": "",
            },
        )
        saved = SavedSearch.objects.get(owner=self.user)
        response = self.client.post(reverse("search:saved-run", args=[saved.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SearchRun.objects.filter(owner=self.user).count(), 2)
        rerun = SearchRun.objects.latest("created_at")
        self.assertFalse(rerun.case_sensitive)
        self.assertEqual(rerun.unicode_normalization, "NFC")

    def test_history_and_exports_are_owner_scoped(self):
        self.run_search()
        run = SearchRun.objects.get(owner=self.user)

        history = self.client.get(reverse("search:history"))
        self.assertEqual(history.status_code, 200)
        self.assertContains(history, "application.log")

        csv_response = self.client.get(
            reverse("search:history-export-csv", args=[run.pk])
        )
        self.assertEqual(csv_response.status_code, 200)
        self.assertTrue(
            AuditEvent.objects.filter(
                actor=self.user,
                action=AuditEvent.Action.EXPORT_CREATED,
                object_type="SearchRun",
                object_id=str(run.pk),
                details={"format": "csv"},
            ).exists()
        )
        csv_body = b"".join(csv_response.streaming_content).decode("utf-8")
        self.assertIn("'=SUM(A1:A2) ERROR Straße", csv_body)

        foreign_run = SearchRun.objects.create(
            workspace=self.other_workspace,
            owner=self.other_user,
            pattern="SECRET",
            algorithm="kmp",
        )
        denied = self.client.get(
            reverse("search:history-detail", args=[foreign_run.pk])
        )
        self.assertEqual(denied.status_code, 404)

    def test_json_export_contains_configuration_and_match_locator(self):
        self.run_search()
        run = SearchRun.objects.get(owner=self.user)
        response = self.client.get(
            reverse("search:history-export-json", args=[run.pk])
        )
        payload = response.json()
        self.assertEqual(payload["run"]["unicode_normalization"], "NFC")
        self.assertEqual(payload["results"][0]["line"], 12)
        self.assertEqual(payload["results"][0]["positions"], [18])
        self.assertTrue(
            AuditEvent.objects.filter(
                actor=self.user,
                action=AuditEvent.Action.EXPORT_CREATED,
                details={"format": "json"},
            ).exists()
        )
