from django.core.management.base import BaseCommand
from django.db import transaction

from organization.models import Organizations
from fleet.models import Terminals


class Command(BaseCommand):
    help = "Create synthetic petroleum terminals for an organization."

    TERMINALS = [
        {
            "name": "Sapele Terminal",
            "location": "Sapele, Delta State",
            "latitude": "5.894344",
            "longitude": "5.687989",
        },
        {
            "name": "Lagos Terminal",
            "location": "Apapa, Lagos State",
            "latitude": "6.452824",
            "longitude": "3.331898",
        },
        {
            "name": "Port Harcourt Terminal",
            "location": "Trans-Amadi, Rivers State",
            "latitude": "4.817454",
            "longitude": "7.055094",
        },
        {
            "name": "Abuja Terminal",
            "location": "Gwagwalada, Abuja",
            "latitude": "8.935830",
            "longitude": "7.081372",
        },
        {
            "name": "Kano Terminal",
            "location": "Kano, Kano State",
            "latitude": "12.029936",
            "longitude": "8.701276",
        },
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-id",
            required=True,
            help="Organization UUID.",
        )

        parser.add_argument(
            "--status",
            default="active",
            choices=[
                "active",
                "closed",
                "decommissioned",
            ],
            help="Status assigned to created terminals.",
        )

    @transaction.atomic
    def handle(self, *args, **options):

        organization_id = options["organization_id"]
        status = options["status"]

        # -----------------------------------------------
        # ORGANIZATION
        # -----------------------------------------------

        try:
            organization = Organizations.objects.get(
                id=organization_id
            )
        except Organizations.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f"Organization {organization_id} "
                    "does not exist."
                )
            )
            return

        # -----------------------------------------------
        # CREATE TERMINALS
        # -----------------------------------------------

        created = 0
        existing = 0

        for data in self.TERMINALS:

            terminal, was_created = Terminals.objects.get_or_create(
                organization=organization,
                name=data["name"],
                defaults={
                    "location": data["location"],
                    "longitude": data["longitude"],
                    "latitude": data["latitude"],
                    "status": status,
                },
            )

            if was_created:
                created += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created: {terminal.name} "
                        f"({terminal.location})"
                    )
                )

            else:
                existing += 1

                self.stdout.write(
                    f"Already exists: {terminal.name}"
                )

        # -----------------------------------------------
        # SUMMARY
        # -----------------------------------------------

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Finished. Created: {created}, "
                f"Already existed: {existing}"
            )
        )
