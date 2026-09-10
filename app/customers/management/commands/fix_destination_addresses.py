from django.core.management.base import BaseCommand
from django.db import transaction

from organization.models import Organizations
from customers.models import Customer, DeliveryAddress


class Command(BaseCommand):
    help = (
        "Fix synthetic delivery addresses so they exactly "
        "match destination values from the route sheet."
    )

    DESTINATION_FIXES = [
        "AKWAIBOM",
        "RIVER",
        "OBURARA",
        "FUTUA",
        "YENOGOA",
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-id",
            required=True,
            help="Organization UUID.",
        )

    def normalize_destination(self, destination):
        """
        Normalize destination names from the source route sheet
        to the canonical customer/delivery-address names.
        """

        destination = destination.strip().upper()

        destination_aliases = {
            "RIVER": "RIVERS",
            "YENOGOA": "YENOGOA",
            "AKWAIBOM": "AKWAIBOM",
            "OBURARA": "OBURARA",
            "FUTUA": "FUTUA",
        }

        return destination_aliases.get(
            destination,
            destination,
        )

    @transaction.atomic
    def handle(self, *args, **options):

        organization_id = options["organization_id"]

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

        self.stdout.write(
            f"Organization: {organization.name}"
        )

        fixed = 0
        created = 0

        for destination in self.DESTINATION_FIXES:

            # -------------------------------------------------
            # Find an existing delivery address using a broad
            # case-insensitive search.
            #
            # This handles:
            # RIVER
            # Rivers
            # RIVERS, Nigeria
            # etc.
            # -------------------------------------------------
            destination = self.normalize_destination(destination)

            addresses = DeliveryAddress.objects.filter(
                customer__organization=organization
            )

            matching_address = None

            for address in addresses:

                existing = (
                    address.address
                    or ""
                ).strip().upper()

                # Handle RIVER / RIVERS specifically
                if destination == "RIVER":
                    if existing in {
                        "RIVER",
                        "RIVERS",
                        "RIVER, NIGERIA",
                        "RIVERS, NIGERIA",
                    }:
                        matching_address = address
                        break

                elif destination == "YENOGOA":
                    if existing in {
                        "YENOGOA",
                        "YENAGOA",
                        "YENOGOA, NIGERIA",
                        "YENAGOA, NIGERIA",
                    }:
                        matching_address = address
                        break

                else:
                    if (
                        existing == destination
                        or existing == f"{destination}, NIGERIA"
                    ):
                        matching_address = address
                        break

            # -------------------------------------------------
            # EXISTING ADDRESS FOUND
            # -------------------------------------------------

            if matching_address:

                old_value = matching_address.address

                if old_value != destination:

                    matching_address.address = destination

                    matching_address.save(
                        update_fields=[
                            "address",
                            "updated_at",
                        ]
                    )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ↻ Fixed: "
                            f"'{old_value}' → '{destination}'"
                        )
                    )

                    fixed += 1

                else:

                    self.stdout.write(
                        f"  ✓ Already correct: "
                        f"{destination}"
                    )

                continue

            # -------------------------------------------------
            # ADDRESS DOES NOT EXIST
            #
            # Create the missing synthetic customer/address.
            # -------------------------------------------------

            display_name = destination.title()

            customer_name = (
                f"Synthetic Customer - {display_name}"
            )

            customer, customer_created = (
                Customer.objects.get_or_create(
                    organization=organization,
                    name=customer_name,
                    defaults={
                        "email": None,
                        "phone_number": None,
                        "address": destination,
                        "is_active": True,
                    },
                )
            )

            if customer_created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  + Created customer: "
                        f"{customer_name}"
                    )
                )

            DeliveryAddress.objects.create(
                customer=customer,
                label=f"{display_name} Delivery Site",
                address=destination,
                latitude=None,
                longitude=None,
                is_default=True,
                is_active=True,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"  + Created delivery address: "
                    f"{destination}"
                )
            )

            created += 1

        # -----------------------------------------------------
        # SUMMARY
        # -----------------------------------------------------

        self.stdout.write("")
        self.stdout.write("=" * 60)

        self.stdout.write(
            self.style.SUCCESS(
                "DESTINATION ADDRESS FIX COMPLETED"
            )
        )

        self.stdout.write(
            f"Organization: {organization.name}"
        )

        self.stdout.write(
            f"Addresses fixed: {fixed}"
        )

        self.stdout.write(
            f"Customers/addresses created: {created}"
        )

        self.stdout.write("=" * 60)
