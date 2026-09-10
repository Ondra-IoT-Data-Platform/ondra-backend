import random

from django.core.management.base import BaseCommand
from django.db import transaction

from organization.models import Organizations
from fleet.models import Truck
from terminals.models import Terminals


class Command(BaseCommand):
    help = (
        "Generate synthetic tanker trucks for an organization "
        "and distribute them evenly across its terminals."
    )

    # Realistic tanker capacities in litres.
    TRUCK_CAPACITIES = [
        20_000,
        25_000,
        30_000,
        33_000,
        35_000,
        40_000,
        45_000,
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-id",
            required=True,
            help="Organization UUID.",
        )

        parser.add_argument(
            "--count",
            type=int,
            default=30,
            help="Number of synthetic trucks to create.",
        )

        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for reproducible generation.",
        )

    @transaction.atomic
    def handle(self, *args, **options):

        random.seed(options["seed"])

        organization_id = options["organization_id"]
        count = options["count"]

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

        self.stdout.write(
            self.style.SUCCESS(
                f"Found {len(terminals)} terminals."
            )
        )

        for terminal in terminals:
            self.stdout.write(
                f"  - {terminal.name}"
            )

        # --------------------------------------------------
        # GENERATE TRUCKS
        # --------------------------------------------------

        created = 0

        for index in range(count):

            # ----------------------------------------------
            # Distribute trucks evenly across terminals.
            #
            # Example:
            # 4 terminals + 20 trucks
            #
            # Terminal 1 -> 5
            # Terminal 2 -> 5
            # Terminal 3 -> 5
            # Terminal 4 -> 5
            # ----------------------------------------------

            terminal = terminals[
                index % len(terminals)
            ]

            capacity = random.choice(
                self.TRUCK_CAPACITIES
            )

            # Synthetic plate number.
            #
            # This is only required because your Truck model
            # requires plate_number.
            plate_number = (
                f"SYN-{index + 1:04d}"
            )

            # Avoid duplicate plate numbers if the command
            # has already been run.
            truck, was_created = Truck.objects.get_or_create(
                plate_number=plate_number,
                defaults={
                    "capacity": capacity,
                    "truck_type": Truck.TruckType.TANKER,
                    "current_status": Truck.StatusChoices.PARKED,
                    "home_terminal": terminal,
                    "organization": organization,
                    "is_active": True,
                },
            )

            if was_created:

                created += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ Created {plate_number} "
                        f"| {capacity:,} L "
                        f"| {terminal.name}"
                    )
                )

            else:

                self.stdout.write(
                    f"  ↻ Already exists: {plate_number}"
                )

        # --------------------------------------------------
        # SUMMARY
        # --------------------------------------------------

        self.stdout.write("")
        self.stdout.write("=" * 60)

        self.stdout.write(
            self.style.SUCCESS(
                "TRUCK SEEDING COMPLETED"
            )
        )

        self.stdout.write(
            f"Organization: {organization.name}"
        )

        self.stdout.write(
            f"Terminals: {len(terminals)}"
        )

        self.stdout.write(
            f"Trucks requested: {count}"
        )

        self.stdout.write(
            f"Trucks created: {created}"
        )

        self.stdout.write("=" * 60)

        # --------------------------------------------------
        # TERMINAL DISTRIBUTION
        # --------------------------------------------------

        self.stdout.write("")
        self.stdout.write("TRUCK DISTRIBUTION:")

        for terminal in terminals:

            terminal_count = Truck.objects.filter(
                organization=organization,
                home_terminal=terminal,
            ).count()

            self.stdout.write(
                f"  {terminal.name}: "
                f"{terminal_count} trucks"
            )
