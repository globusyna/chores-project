from django.db import migrations


def create_missing_profiles(apps, schema_editor):
    """Give any pre-existing user a default (CHILD) Profile.

    None are expected this early, but it keeps ``migrate`` safe on a
    database that already has users from before the signal existed.
    """
    User = apps.get_model("auth", "User")
    Profile = apps.get_model("accounts", "Profile")
    for user in User.objects.filter(profile__isnull=True):
        Profile.objects.create(user=user)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_missing_profiles, noop_reverse),
    ]
