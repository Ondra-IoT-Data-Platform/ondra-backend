import random

from django.core.management.base import BaseCommand
from django.db import transaction

from organization.models import Organizations
from terminals.models import Terminals
from fleet.models import Truck
from users.models import User, DriverProfile


class Command(BaseCommand):
    help = "Create synthetic driver users and DriverProfiles for an organization."

    FIRST_NAMES = [
        "Chinedu",
        "Emeka",
        "Ibrahim",
        "Musa",
        "Yusuf",
        "Daniel",
        "Samuel",
        "Peter",
        "David",
        "Joseph",
        "Victor",
        "Michael",
        "Ifeanyi",
        "Chukwuemeka",
        "Abdul",
        "Usman",
        "Sani",
        "Ahmed",
        "John",
        "Paul",
        "Anthony",
        "Kingsley",
        "Benjamin",
        "Godwin",
        "Kenneth",
        "Okechukwu",
        "Nnamdi",
        "Uche",
        "Obinna",
        "Collins",
        "Stephen",
        "Emmanuel",
        "Friday",
        "Patrick",
        "Charles",
        "Christian",
        "Martin",
        "Gabriel",
        "Henry",
        "Francis",
        "Joshua",
    ]

    LAST_NAMES = [
        "Okafor",
        "Eze",
        "Obi",
        "Nwosu",
        "Okoro",
        "Adeyemi",
        "Bello",
        "Abdullahi",
        "Ibrahim",
        "Musa",
        "Mohammed",
        "Garba",
        "Yusuf",
        "Sule",
        "Usman",
        "Adebayo",
        "Ogunleye",
        "Akinwale",
        "Balogun",
        "Olawale",
        "Opara",
        "Umeh",
        "Chukwu",
        "Ibekwe",
        "Ekwueme",
        "Onyeka",
        "Nwachukwu",
        "Anyanwu",
        "Iroha",
        "Ezeani",
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-id",
            required=True,
            help="Organization UUID.",
        )

    @transaction.atomic
    def handle(self, *args, **options):

        random.seed(42)

        organization_id = options["organization_id"]

        # --------------------------------------------------
        # ORGANIZATION
        # --------------------------------------------------

        try:
            organization = Organizations.objects.get(
                id=organization_id
            )
        except Organizations.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f"Organization {organization_id} does not exist."
                )
            )
            return

        # --------------------------------------------------
        # TERMINALS
        # --------------------------------------------------

        terminals = list(
            Terminals.objects.filter(
                organization=organization
            ).order_by("name")
        )

        if not terminals:
            self.stdout.write(
                self.style.ERROR(
                    "No terminals found for this organization."
                )
            )
            return

        # --------------------------------------------------
        # NAME POOL
        # --------------------------------------------------

        names = [
            f"{first} {last}"
            for first in self.FIRST_NAMES
            for last in self.LAST_NAMES
        ]

        random.shuffle(names)

        name_index = 0
        created = 0
        existing = 0

        # --------------------------------------------------
        # PROCESS EACH TERMINAL
        # --------------------------------------------------

        for terminal in terminals:

            trucks = list(
                Truck.objects.filter(
                    organization=organization,
                    home_terminal=terminal,
                    is_active=True,
                ).order_by("plate_number")
            )

            if not trucks:
                self.stdout.write(
                    self.style.WARNING(
                        f"\n{terminal.name}: no trucks found."
                    )
                )
                continue

            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    f"Processing {terminal.name}"
                )
            )

            self.stdout.write(
                f"Trucks at terminal: {len(trucks)}"
            )

            # --------------------------------------------------
            # CREATE ONE DRIVER PER TRUCK COUNT
            #
            # This does NOT create a database relationship
            # between the driver and truck.
            #
            # We are simply creating enough drivers at this
            # terminal for the synthetic dispatch data.
            # --------------------------------------------------

            for _ in range(len(trucks)):

                if name_index >= len(names):
                    name_index = 0

                full_name = names[name_index]
                name_index += 1

                # Create a unique synthetic email.
                email = (
                    f"driver.{name_index:03d}"
                    "@synthetic.apexpetro.test"
                )

                # --------------------------------------------------
                # CHECK WHETHER THIS DRIVER ALREADY EXISTS
                # --------------------------------------------------

                user = User.objects.filter(
                    email=email
                ).first()

                if user:

                    profile, profile_created = (
                        DriverProfile.objects.get_or_create(
                            user=user,
                            defaults={
                                "full_name": full_name,
                                "job_title": "Truck Driver",
                                "phone_number": (
                                    f"+23480"
                                    f"{random.randint(10000000, 99999999)}"
                                ),
                                "license_number": (
                                    f"SYN-LIC-{name_index:04d}"
                                ),
                                "ops_location": (
                                    terminal.location
                                ),
                            },
                        )
                    )

                    if profile_created:
                        created += 1
                    else:
                        existing += 1

                    continue

                # --------------------------------------------------
                # CREATE USER
                # --------------------------------------------------

                user = User.objects.create_user(
                    email=email,
                    password="SyntheticDriver123!",
                    is_active=True,
                    is_staff=False,
                )

                # --------------------------------------------------
                # CREATE DRIVER PROFILE
                # --------------------------------------------------

                DriverProfile.objects.create(
                    user=user,
                    full_name=full_name,
                    job_title="Truck Driver",
                    phone_number=(
                        f"+23480"
                        f"{random.randint(10000000, 99999999)}"
                    ),
                    license_number=(
                        f"SYN-LIC-{name_index:04d}"
                    ),
                    ops_location=terminal.location,
                )

                created += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ {full_name} "
                        f"→ {terminal.name}"
                    )
                )

        # --------------------------------------------------
        # SUMMARY
        # --------------------------------------------------

        self.stdout.write("")
        self.stdout.write("=" * 60)

        self.stdout.write(
            self.style.SUCCESS(
                "DRIVER SEEDING COMPLETED"
            )
        )

        self.stdout.write(
            f"Organization: {organization.name}"
        )

        self.stdout.write(
            f"Driver profiles created: {created}"
        )

        self.stdout.write(
            f"Existing drivers found: {existing}"
        )

        self.stdout.write("=" * 60)
