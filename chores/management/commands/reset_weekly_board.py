"""Weekly board reset (tasks.md #16).

Run weekly -- Sunday 00:00 local -- from system cron, e.g.::

    0 0 * * 0  cd /srv/chores && .venv/bin/python manage.py reset_weekly_board

Each run spawns one OPEN `Bounty` per *active* `ChoreTemplate`,
unconditionally. Cron runs it once a week, so duplicates don't arise in
practice; running it by hand a second time simply adds another set.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from chores.models import Bounty, ChoreTemplate


class Command(BaseCommand):
    help = (
        "Repopulate the bounty board from active chore templates. Intended "
        "to run weekly (Sunday 00:00 local) via system cron. Each run spawns "
        "one OPEN bounty per active template, unconditionally."
    )

    def handle(self, *args, **options):
        with transaction.atomic():
            templates = list(ChoreTemplate.objects.filter(active=True))
            Bounty.objects.bulk_create(
                Bounty(
                    title=t.title,
                    description=t.description,
                    point_value=t.default_point_value,
                    status=Bounty.Status.OPEN,
                    source_template=t,
                    created_by=None,
                )
                for t in templates
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"reset_weekly_board: created {len(templates)} bounty(ies) "
                f"from active templates."
            )
        )
