from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from apps.accounts.services import (
    ADMIN_ROLE,
    ANALYST_ROLE,
    REVIEWER_ROLE,
    assign_role,
    get_or_create_role_groups,
    get_user_role,
    has_role,
    is_admin,
    is_analyst,
    is_reviewer,
)


User = get_user_model()


class RoleServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="role_test_user",
            password="test-password-123",
        )

    def test_role_groups_are_created(self):
        roles = get_or_create_role_groups()

        self.assertEqual(set(roles.keys()), {
            ADMIN_ROLE,
            ANALYST_ROLE,
            REVIEWER_ROLE,
        })

        self.assertEqual(Group.objects.count(), 3)

    def test_assign_admin_role(self):
        assign_role(self.user, ADMIN_ROLE)

        self.assertEqual(get_user_role(self.user), ADMIN_ROLE)
        self.assertTrue(is_admin(self.user))
        self.assertFalse(is_analyst(self.user))
        self.assertFalse(is_reviewer(self.user))

    def test_assign_analyst_role(self):
        assign_role(self.user, ANALYST_ROLE)

        self.assertEqual(get_user_role(self.user), ANALYST_ROLE)
        self.assertTrue(is_analyst(self.user))
        self.assertFalse(is_admin(self.user))
        self.assertFalse(is_reviewer(self.user))

    def test_assign_reviewer_role(self):
        assign_role(self.user, REVIEWER_ROLE)

        self.assertEqual(get_user_role(self.user), REVIEWER_ROLE)
        self.assertTrue(is_reviewer(self.user))
        self.assertFalse(is_admin(self.user))
        self.assertFalse(is_analyst(self.user))

    def test_assigning_new_role_removes_previous_role(self):
        assign_role(self.user, ANALYST_ROLE)
        assign_role(self.user, REVIEWER_ROLE)

        self.assertEqual(get_user_role(self.user), REVIEWER_ROLE)

        self.assertEqual(
            list(self.user.groups.values_list("name", flat=True)),
            [REVIEWER_ROLE],
        )

    def test_unknown_role_is_rejected(self):
        with self.assertRaises(ValueError):
            assign_role(self.user, "Unknown Role")

    def test_superuser_is_always_admin(self):
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save(update_fields=["is_superuser", "is_staff"])

        self.assertEqual(get_user_role(self.user), ADMIN_ROLE)
        self.assertTrue(is_admin(self.user))

    def test_user_without_role_returns_none(self):
        self.assertIsNone(get_user_role(self.user))

    def test_has_role(self):
        assign_role(self.user, ANALYST_ROLE)

        self.assertTrue(has_role(self.user, ANALYST_ROLE))
        self.assertFalse(has_role(self.user, ADMIN_ROLE))
        self.assertFalse(has_role(self.user, REVIEWER_ROLE))
