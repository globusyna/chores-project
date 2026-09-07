"""Local dev / demo seed data (tasks.md #21).

Creates a handful of chore templates and perks, a parent account, a child
account, a plain ``test_user`` account (for poking at the login flow), and
a couple of OPEN bounties so the board isn't empty. Idempotent -- every
object is created with ``get_or_create`` on a natural key, so running it
again changes nothing. Dev only: it refuses to run with ``DEBUG=False``.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Profile
from chores.models import Bounty, ChoreTemplate
from store.models import Perk

PARENT = ("parent", "parent-password")
CHILD = ("child", "child-password")
# A plain account for exercising the login flow. Child role by default;
# promote it in the admin if you need parent access.
TEST = ("test_user", "test_password")

TEMPLATES = [
    {
        "title": "Wash the dishes",
        "description": "After dinner, including drying and putting away.",
        "default_point_value": 5,
    },
    {"title": "Take out the bins", "description": "", "default_point_value": 3},
    {
        "title": "Vacuum the living room",
        "description": "Under the sofa cushions too.",
        "default_point_value": 8,
    },
]

PERKS = [
    {"title": "Movie night pick", "description": "Choose the film.", "point_cost": 30},
    {
        "title": "Extra hour of screen time",
        "description": "One-off, not on a school night.",
        "point_cost": 15,
    },
    {
        "title": "Choose the weekend outing",
        "description": "Within reason!",
        "point_cost": 60,
    },
]


class Command(BaseCommand):
    help = (
        "Populate a demo board, perks and parent / child / test_user "
        "accounts. DEV ONLY -- refuses to run with DEBUG=False."
    )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "seed_dev refuses to run with DEBUG=False -- it is dev-only."
            )

        User = get_user_model()

        with transaction.atomic():
            for data in TEMPLATES:
                ChoreTemplate.objects.get_or_create(
                    title=data["title"], defaults=data
                )
            for data in PERKS:
                Perk.objects.get_or_create(title=data["title"], defaults=data)

            parent = self._account(User, PARENT, Profile.Role.PARENT)
            self._account(User, CHILD, Profile.Role.CHILD)
            self._account(User, TEST, Profile.Role.CHILD)

            # Leave the board populated without piling up on re-runs.
            for template in ChoreTemplate.objects.filter(active=True)[:2]:
                Bounty.objects.get_or_create(
                    title=template.title,
                    source_template=template,
                    defaults={
                        "description": template.description,
                        "point_value": template.default_point_value,
                        "status": Bounty.Status.OPEN,
                        "created_by": parent,
                    },
                )

        self.stdout.write(self.style.SUCCESS("Seeded dev data."))
        self.stdout.write(f"  parent login:    {PARENT[0]} / {PARENT[1]}")
        self.stdout.write(f"  child login:     {CHILD[0]} / {CHILD[1]}")
        self.stdout.write(f"  test_user login: {TEST[0]} / {TEST[1]}")

    @staticmethod
    def _account(User, credentials, role):
        username, password = credentials
        user, created = User.objects.get_or_create(username=username)
        if created:
            user.set_password(password)
            user.save(update_fields=["password"])
        # role is idempotent to re-assert
        user.profile.role = role
        user.profile.save(update_fields=["role"])
        return user
