"""Claim-expiry sweep (tasks.md #17).

Run roughly every 5 minutes from system cron, e.g.::

    */5 * * * *  cd /srv/chores && .venv/bin/python manage.py sweep_expired_claims

Returns every unfinished CLAIMED bounty whose claim window has passed back
to OPEN. No rejection and no penalty. The board view does the same revert
lazily between runs, so this is just a backstop. Safe to run when nothing
is expired.
"""

from django.core.management.base import BaseCommand

from chores.models import Bounty


class Command(BaseCommand):
    help = (
        "Return expired unfinished claims to the board. Run about every 5 "
        "minutes via system cron."
    )

    def handle(self, *args, **options):
        count = Bounty.objects.release_expired()
        self.stdout.write(
            self.style.SUCCESS(
                f"sweep_expired_claims: reverted {count} expired claim(s)."
            )
        )
