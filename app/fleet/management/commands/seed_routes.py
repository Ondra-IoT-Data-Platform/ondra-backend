from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from organization.models import Organizations
from fleet.models import Terminals, Route
from customers.models import DeliveryAddress


class Command(BaseCommand):
    help = (
        "Seed routes for an organization using the terminal, "
        "destination and transit-time data from the supplied "
        "route sheet."
    )

    # =========================================================
    # ROUTE DATA FROM THE SUPPLIED EXCEL SHEET
    #
    # Format:
    #
    # "TERMINAL": [
    #     ("DESTINATION", TAT_IN_HOURS),
    # ]
    #
    # Transit times have been converted to hours because
    # Route.expected_tat_hours stores hours.
    # =========================================================

    ROUTES = {

        # =====================================================
        # SAPELE TERMINAL
        # =====================================================

        "SAPELE TERMINAL": [
            ("PORT-HAROURT", 4),
            ("ABIA", 5),
            ("ABUJA", 48),
            ("AKWAIBOM", 24),
            ("ANAMBRA", 24),
            ("BAUCHI", 72),
            ("BAYELSA", 6),
            ("BENUE", 48),
            ("BORNO", 96),
            ("RIVERS", 6),
            ("EBONYI", 24),
            ("BIDA", 96),
            ("MINNA", 72),
            ("MOKWA", 48),
            ("JEBBA", 48),
            ("KAIAMA", 72),
            ("ABA", 24),
            ("UYO", 27),
            ("CALABAR", 48),
            ("OBURARA", 48),
            ("EKITI", 26),
            ("ENUGU", 24),
            ("GOMBE", 120),
            ("IMO", 24),
            ("JIGAWA", 96),
            ("KADUNA", 48),
            ("KANO", 72),
            ("KATSINA", 96),
            ("BIRNIN KEBBI", 144),
            ("KOGI", 24),
            ("KWARA", 48),
            ("LAGOS", 27),
            ("EPE", 24),
            ("NASARAWA", 72),
            ("KONTAGORA", 96),
            ("OGUN", 24),
            ("ONDO", 6),
            ("MOWE", 24),
            ("ABEOKUTA", 24),
            ("OSUN", 24),
            ("OYO", 24),
            ("OSOGBO", 24),
            ("ILORIN", 29),
            ("JOS", 72),
            ("RIVERS", 6),
            ("SOKOTO", 120),
            ("TARABA", 72),
            ("ZAMFARA", 96),
            ("JALINGO", 72),
            ("MAYO BELWA", 72),
            ("YOLA", 96),
            ("MUBI", 120),
            ("BIU", 96),
            ("MAIDUGURI", 120),
            ("DAMATURU", 120),
            ("DUTSE", 96),
            ("FUTUA", 96),
            ("GUSAU", 96),
            ("TALATA MAFARA", 120),
        ],

        # =====================================================
        # PHC TERMINAL
        # =====================================================

        "PHC TERMINAL": [
            ("SAPELE", 6),
            ("ABA", 3),
            ("UMUAHIA", 4),
            ("ABUJA", 48),
            ("AKWAIBOM", 8),
            ("ANAMBRA", 8),
            ("BAUCHI", 48),
            ("YENOGOA", 5),
            ("BENUE", 24),
            ("MAIDUGURI", 120),
            ("EBONYI", 24),
            ("BIDA", 96),
            ("MINNA", 72),
            ("MOKWA", 96),
            ("JEBBA", 48),
            ("KAIAMA", 54),
            ("UYO", 8),
            ("CALABAR", 24),
            ("OBURARA", 24),
            ("ADO-EKITI", 31),
            ("ENUGU", 8),
            ("GOMBE", 72),
            ("ANAMBRA", 8),
            ("JIGAWA", 72),
            ("KADUNA", 48),
            ("KANO", 72),
            ("KATSINA", 96),
            ("BIRNIN KEBBI", 144),
            ("OKENE", 30),
            ("KWARA", 48),
            ("LAGOS", 30),
            ("EPE", 24),
            ("NASARAWA", 28),
            ("OGUN", 24),
            ("ONDO", 24),
            ("MOWE", 24),
            ("ABEOKUTA", 24),
            ("OSUN", 24),
            ("OGBOMOSO", 30),
            ("OSOGBO", 24),
            ("ILORIN", 24),
            ("JOS", 72),
            ("SOKOTO", 120),
            ("TARABA", 48),
            ("ZAMFARA", 96),
            ("JALINGO", 72),
            ("MAYO BELWA", 72),
            ("YOLA", 72),
            ("MUBI", 96),
            ("BIU", 72),
            ("DAMATURU", 120),
            ("DUTSE", 96),
            ("FUTUA", 72),
            ("GUSAU", 96),
            ("TALATA MAFARA", 120),
        ],

        # =====================================================
        # GWAGWALADA TERMINAL
        # =====================================================

        "GWAGWALADA TERMINAL": [
            ("SAPELE", 48),
            ("PHC", 72),
            ("ABA", 72),
            ("UMUAHIA", 48),
            ("YOLA", 48),
            ("UYO", 72),
            ("ANAMBRA", 24),
            ("BAUCHI", 24),
            ("BENUE", 24),
            ("MAIDUGURI", 48),
            ("BIDA", 24),
            ("MINNA", 6),
            ("MOKWA", 48),
            ("JEBBA", 48),
            ("ADO-EKITI", 24),
            ("ENUGU", 48),
            ("GOMBE", 48),
            ("JIGAWA", 24),
            ("KADUNA", 6),
            ("KANO", 24),
            ("KATSINA", 48),
            ("BIRNIN KEBBI", 48),
            ("OKENE", 6),
            ("KWARA", 72),
            ("LAGOS", 72),
            ("EPE", 96),
            ("NASARAWA", 6),
            ("KONTAGORA", 24),
            ("OGUN", 48),
            ("ONDO", 48),
            ("MOWE", 48),
            ("OGBOMOSO", 72),
            ("OSOGBO", 72),
            ("ILORIN", 72),
            ("JOS", 24),
            ("SOKOTO", 48),
            ("TARABA", 24),
            ("ZAMFARA", 24),
            ("JALINGO", 48),
            ("MAYO BELWA", 48),
            ("YOLA", 48),
            ("MUBI", 72),
            ("BIU", 48),
            ("DAMATURU", 48),
            ("DUTSE", 24),
            ("FUTUA", 24),
            ("GUSAU", 24),
            ("TALATA MAFARA", 32),
        ],

        # =====================================================
        # KANO TERMINAL
        # =====================================================

        "KANO TERMINAL": [
            ("SAPELE", 72),
            ("GWAGWALADA", 24),
            ("PHC", 96),
            ("YOLA", 48),
            ("UYO", 72),
            ("ANAMBRA", 72),
            ("BAUCHI", 10),
            ("BENUE", 48),
            ("MAIDUGURI", 24),
            ("ENUGU", 48),
            ("GOMBE", 24),
            ("DUTSE", 4),
            ("KADUNA", 6),
            ("KATSINA", 24),
            ("BIRNIN KEBBI", 48),
            ("OKENE", 29),
            ("LAGOS", 72),
            ("NASARAWA", 24),
            ("JOS", 24),
            ("SOKOTO", 48),
            ("ZAMFARA", 24),
            ("JALINGO", 48),
            ("MAYO BELWA", 48),
            ("YOLA", 48),
            ("MUBI", 48),
            ("BIU", 24),
            ("DAMATURU", 24),
            ("FUTUA", 6),
            ("GUSAU", 8),
            ("TALATA MAFARA", 10),
        ],
    }

    # =========================================================
    # DESTINATION NORMALIZATION
    # =========================================================

    DESTINATION_ALIASES = {
        # Excel uses PHC in some sections while customer
        # records may use PORT-HAROURT.
        "PHC": "PORT-HAROURT",

        # Normal spelling/format variations appearing in
        # the source data.
        "PORT HARCOURT": "PORT-HAROURT",
        "PORT-HARCOURT": "PORT-HAROURT",

        "RIVERS": "RIVERS",
        "RIVER": "RIVER",

        "ADO EKITI": "ADO-EKITI",
        "MAYO-BELWA": "MAYO BELWA",
        "TALATA-MAFARA": "TALATA MAFARA",

        "BIRNIN KEBBI": "BIRNIN KEBBI",

        "OGBOMOSO": "OGBOMOSO",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-id",
            required=True,
            help="Organization UUID.",
        )

    @staticmethod
    def normalize(value):
        if not value:
            return ""

        return (
            str(value)
            .strip()
            .upper()
            .replace("–", "-")
            .replace("—", "-")
            .replace("  ", " ")
        )

    def normalize_destination(self, value):
        value = self.normalize(value)

        return self.DESTINATION_ALIASES.get(
            value,
            value,
        )

    # =========================================================
    # MAIN COMMAND
    # =========================================================

    @transaction.atomic
    def handle(self, *args, **options):

        organization_id = options["organization_id"]

        # -----------------------------------------------------
        # ORGANIZATION
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # TERMINALS
        # -----------------------------------------------------

        terminals = list(
            Terminals.objects.filter(
                organization=organization
            )
        )

        if not terminals:

            self.stdout.write(
                self.style.ERROR(
                    "No terminals found for this organization."
                )
            )
            return

        terminal_lookup = {
            self.normalize(terminal.name): terminal
            for terminal in terminals
        }

        # -----------------------------------------------------
        # CUSTOMER DELIVERY ADDRESSES
        # -----------------------------------------------------

        delivery_addresses = list(
            DeliveryAddress.objects.filter(
                customer__organization=organization,
                customer__is_active=True,
                is_active=True,
            ).select_related("customer")
        )

        if not delivery_addresses:

            self.stdout.write(
                self.style.ERROR(
                    "No customer delivery addresses found. "
                    "Run seed_customers first."
                )
            )
            return

        # -----------------------------------------------------
        # BUILD DESTINATION LOOKUP
        # -----------------------------------------------------

        destination_lookup = {}

        for delivery_address in delivery_addresses:

            raw_address = (
                delivery_address.address or ""
            )

            destination = (
                raw_address
                .split(",")[0]
                .strip()
            )

            destination = self.normalize_destination(
                destination
            )

            if destination:
                destination_lookup[destination] = (
                    delivery_address
                )

        # -----------------------------------------------------
        # CREATE ROUTES
        # -----------------------------------------------------

        created = 0
        updated = 0
        skipped = 0

        for terminal_name, route_definitions in (
            self.ROUTES.items()
        ):

            normalized_terminal = self.normalize(
                terminal_name
            )

            terminal = terminal_lookup.get(
                normalized_terminal
            )

            if not terminal:

                self.stdout.write(
                    self.style.WARNING(
                        f"Terminal '{terminal_name}' "
                        "was not found for this organization. "
                        "Skipping its routes."
                    )
                )

                continue

            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    f"Processing {terminal.name}"
                )
            )

            for destination, tat_hours in (
                route_definitions
            ):

                normalized_destination = (
                    self.normalize_destination(
                        destination
                    )
                )

                delivery_address = (
                    destination_lookup.get(
                        normalized_destination
                    )
                )

                if not delivery_address:

                    self.stdout.write(
                        self.style.WARNING(
                            f"  ! No customer delivery "
                            f"address found for "
                            f"'{destination}'. Skipping."
                        )
                    )

                    skipped += 1
                    continue

                route_name = (
                    f"{terminal.name} → {destination}"
                )

                route, was_created = (
                    Route.objects.update_or_create(
                        organization=organization,
                        route_name=route_name,
                        defaults={
                            "origin_terminal": terminal,
                            "destination": (
                                delivery_address.address
                            ),
                            "expected_tat_hours": Decimal(
                                str(tat_hours)
                            ),
                        },
                    )
                )

                if was_created:

                    created += 1

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ Created: {route_name} "
                            f"({tat_hours} hrs)"
                        )
                    )

                else:

                    updated += 1

                    self.stdout.write(
                        f"  ↻ Updated: {route_name} "
                        f"({tat_hours} hrs)"
                    )

        # -----------------------------------------------------
        # SUMMARY
        # -----------------------------------------------------

        self.stdout.write("")
        self.stdout.write("=" * 65)

        self.stdout.write(
            self.style.SUCCESS(
                "ROUTE SEEDING COMPLETED"
            )
        )

        self.stdout.write(
            f"Organization: {organization.name}"
        )

        self.stdout.write(
            f"Terminals found: {len(terminals)}"
        )

        self.stdout.write(
            f"Customer delivery addresses: "
            f"{len(destination_lookup)}"
        )

        self.stdout.write(
            f"Routes created: {created}"
        )

        self.stdout.write(
            f"Routes updated: {updated}"
        )

        self.stdout.write(
            f"Routes skipped: {skipped}"
        )

        self.stdout.write("=" * 65)
