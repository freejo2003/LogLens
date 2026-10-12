from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.ingestion.models import SourceFile, TextSegment
from apps.search.models import MatchResult, SearchRun
from apps.workspaces.models import Workspace


User = get_user_model()


class SearchWorkflowTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="searchuser",
            password="test-password",
        )

        self.other_user = User.objects.create_user(
            username="otheruser",
            password="test-password",
        )

        self.workspace = Workspace.objects.create(
            name="Search Workspace",
            owner=self.user,
        )

        self.other_workspace = Workspace.objects.create(
            name="Other Workspace",
            owner=self.other_user,
        )

        self.source_file = SourceFile.objects.create(
            workspace=self.workspace,
            owner=self.user,
            original_name="test.txt",
            storage_key="uploads/search-test.txt",
            storage_path="private_media/uploads/search-test.txt",
            extension=".txt",
            detected_type="text/plain",
            byte_size=27,
            checksum="a" * 64,
            extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
        )

        self.segment = TextSegment.objects.create(
            source_file=self.source_file,
            sequence=1,
            text="ERROR database connection failed",
            line_number=1,
            parser_name="plain_text",
            parser_version="1.0",
        )

        self.url = reverse("search:run")

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_authenticated_user_can_open_search_page(self):
        self.client.login(
            username="searchuser",
            password="test-password",
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Search")

    def test_authenticated_user_can_run_search(self):
        self.client.login(
            username="searchuser",
            password="test-password",
        )

        response = self.client.post(
            self.url,
            {
                "workspace": self.workspace.id,
                "source_file": self.source_file.id,
                "pattern": "ERROR",
                "algorithm": "naive",
            },
        )

        self.assertEqual(response.status_code, 200)

        search_run = SearchRun.objects.get()

        self.assertEqual(
            search_run.owner_id,
            self.user.id,
        )

        self.assertEqual(
            search_run.pattern,
            "ERROR",
        )

        self.assertEqual(
            search_run.algorithm,
            "naive",
        )

        self.assertEqual(
            search_run.total_match_count,
            1,
        )

        self.assertEqual(
            MatchResult.objects.filter(
                search_run=search_run
            ).count(),
            1,
        )

        self.assertContains(response, "ERROR")

    def test_other_users_source_file_is_rejected(self):
        self.client.login(
            username="searchuser",
            password="test-password",
        )

        other_source_file = SourceFile.objects.create(
            workspace=self.other_workspace,
            owner=self.other_user,
            original_name="private.txt",
            storage_key="uploads/private.txt",
            storage_path="private_media/uploads/private.txt",
            extension=".txt",
            detected_type="text/plain",
            byte_size=10,
            checksum="b" * 64,
            extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
        )

        response = self.client.post(
            self.url,
            {
                "workspace": self.workspace.id,
                "source_file": other_source_file.id,
                "pattern": "ERROR",
                "algorithm": "kmp",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice")
        self.assertEqual(SearchRun.objects.count(), 0)

    def test_other_users_workspace_is_rejected(self):
        self.client.login(
            username="searchuser",
            password="test-password",
        )

        response = self.client.post(
            self.url,
            {
                "workspace": self.other_workspace.id,
                "source_file": self.source_file.id,
                "pattern": "ERROR",
                "algorithm": "kmp",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice")
        self.assertEqual(SearchRun.objects.count(), 0)

    def test_workspace_and_source_file_must_match(self):
        self.client.login(
            username="searchuser",
            password="test-password",
        )

        another_workspace = Workspace.objects.create(
            name="Another User Workspace",
            owner=self.user,
        )

        response = self.client.post(
            self.url,
            {
                "workspace": another_workspace.id,
                "source_file": self.source_file.id,
                "pattern": "ERROR",
                "algorithm": "rabin_karp",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "does not belong to the selected workspace",
        )
        self.assertEqual(SearchRun.objects.count(), 0)

    def test_empty_pattern_is_rejected(self):
        self.client.login(
            username="searchuser",
            password="test-password",
        )

        response = self.client.post(
            self.url,
            {
                "workspace": self.workspace.id,
                "source_file": self.source_file.id,
                "pattern": "",
                "algorithm": "naive",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "The search pattern cannot be empty.",
        )
        self.assertEqual(SearchRun.objects.count(), 0)

    def test_invalid_algorithm_is_rejected(self):
        self.client.login(
            username="searchuser",
            password="test-password",
        )

        response = self.client.post(
            self.url,
            {
                "workspace": self.workspace.id,
                "source_file": self.source_file.id,
                "pattern": "ERROR",
                "algorithm": "invalid",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Select a valid choice.",
        )
        self.assertEqual(SearchRun.objects.count(), 0)