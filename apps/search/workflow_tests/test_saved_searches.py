from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.ingestion.models import SourceFile
from apps.search.forms import IndicatorRuleForm, SavedSearchForm
from apps.search.models import IndicatorRule
from apps.search.services.indicators import (
    create_indicator_rule,
    get_indicator_rules_for_user,
)
from apps.search.services.saved_searches import (
    create_saved_search,
    get_saved_searches_for_user,
)
from apps.workspaces.models import Workspace


User = get_user_model()


class SavedSearchTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="saveduser",
            password="test-password",
        )

        self.other_user = User.objects.create_user(
            username="otheruser",
            password="test-password",
        )

        self.workspace = Workspace.objects.create(
            name="Saved Workspace",
            owner=self.user,
        )

        self.other_workspace = Workspace.objects.create(
            name="Other Workspace",
            owner=self.other_user,
        )

        self.source_file = SourceFile.objects.create(
            workspace=self.workspace,
            owner=self.user,
            original_name="saved-search.log",
            storage_key="uploads/test-saved-search.log",
            storage_path="",
            extension=".log",
            detected_type="text/plain",
            byte_size=100,
            checksum="a" * 64,
            extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
        )

        self.other_source_file = SourceFile.objects.create(
            workspace=self.other_workspace,
            owner=self.other_user,
            original_name="other-search.log",
            storage_key="uploads/test-other-search.log",
            storage_path="",
            extension=".log",
            detected_type="text/plain",
            byte_size=100,
            checksum="b" * 64,
            extraction_status=SourceFile.ExtractionStatus.SUCCEEDED,
        )

    def test_saved_search_can_be_created(self):
        saved = create_saved_search(
            owner=self.user,
            workspace=self.workspace,
            source_file=self.source_file,
            name="Database Errors",
            pattern="ERROR",
            algorithm="kmp",
            description="Find database errors.",
        )

        self.assertEqual(saved.owner_id, self.user.id)
        self.assertEqual(saved.workspace_id, self.workspace.id)
        self.assertEqual(saved.source_file_id, self.source_file.id)
        self.assertEqual(saved.pattern, "ERROR")
        self.assertEqual(saved.algorithm, "kmp")
        self.assertEqual(
            saved.source_checksum,
            self.source_file.checksum,
        )

    def test_saved_searches_are_scoped_to_user(self):
        create_saved_search(
            owner=self.user,
            workspace=self.workspace,
            source_file=self.source_file,
            name="My Search",
            pattern="ERROR",
            algorithm="naive",
        )

        create_saved_search(
            owner=self.other_user,
            workspace=self.other_workspace,
            source_file=self.other_source_file,
            name="Other Search",
            pattern="WARNING",
            algorithm="kmp",
        )

        results = list(
            get_saved_searches_for_user(self.user)
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "My Search")

    def test_saved_search_rejects_foreign_workspace(self):
        with self.assertRaises(PermissionError):
            create_saved_search(
                owner=self.user,
                workspace=self.other_workspace,
                source_file=self.other_source_file,
                name="Invalid Search",
                pattern="ERROR",
                algorithm="naive",
            )


class IndicatorRuleTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="indicatoruser",
            password="test-password",
        )

        self.other_user = User.objects.create_user(
            username="otherindicator",
            password="test-password",
        )

        self.workspace = Workspace.objects.create(
            name="Indicator Workspace",
            owner=self.user,
        )

        self.other_workspace = Workspace.objects.create(
            name="Other Indicator Workspace",
            owner=self.other_user,
        )

    def test_indicator_rule_can_be_created(self):
        indicator = create_indicator_rule(
            owner=self.user,
            workspace=self.workspace,
            name="Database Error",
            pattern="database connection failed",
            description="Database connectivity indicator.",
        )

        self.assertEqual(
            indicator.owner_id,
            self.user.id,
        )

        self.assertEqual(
            indicator.pattern,
            "database connection failed",
        )

        self.assertTrue(indicator.is_active)

    def test_indicator_rules_are_scoped_to_user(self):
        create_indicator_rule(
            owner=self.user,
            workspace=self.workspace,
            name="My Indicator",
            pattern="ERROR",
        )

        create_indicator_rule(
            owner=self.other_user,
            workspace=self.other_workspace,
            name="Other Indicator",
            pattern="WARNING",
        )

        results = list(
            get_indicator_rules_for_user(self.user)
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0].name,
            "My Indicator",
        )

    def test_indicator_rule_rejects_foreign_workspace(self):
        with self.assertRaises(PermissionError):
            create_indicator_rule(
                owner=self.user,
                workspace=self.other_workspace,
                name="Invalid Indicator",
                pattern="ERROR",
            )


class SavedSearchFormTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="formuser",
            password="test-password",
        )

        self.workspace = Workspace.objects.create(
            name="Form Workspace",
            owner=self.user,
        )

    def test_empty_saved_search_name_is_rejected(self):
        form = SavedSearchForm(
            data={
                "workspace": self.workspace.id,
                "name": "",
                "pattern": "ERROR",
                "algorithm": "naive",
                "description": "",
            },
            user=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "The saved search name cannot be empty.",
            form.errors["name"],
        )

    def test_empty_saved_search_pattern_is_rejected(self):
        form = SavedSearchForm(
            data={
                "workspace": self.workspace.id,
                "name": "Test Search",
                "pattern": "",
                "algorithm": "naive",
                "description": "",
            },
            user=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "The saved search pattern cannot be empty.",
            form.errors["pattern"],
        )


class IndicatorRuleFormTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="indicatorform",
            password="test-password",
        )

        self.workspace = Workspace.objects.create(
            name="Indicator Form Workspace",
            owner=self.user,
        )

    def test_empty_indicator_name_is_rejected(self):
        form = IndicatorRuleForm(
            data={
                "workspace": self.workspace.id,
                "name": "",
                "pattern": "ERROR",
                "description": "",
                "is_active": "on",
            },
            user=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "The indicator name cannot be empty.",
            form.errors["name"],
        )

    def test_empty_indicator_pattern_is_rejected(self):
        form = IndicatorRuleForm(
            data={
                "workspace": self.workspace.id,
                "name": "Error Indicator",
                "pattern": "",
                "description": "",
                "is_active": "on",
            },
            user=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "The indicator pattern cannot be empty.",
            form.errors["pattern"],
        )