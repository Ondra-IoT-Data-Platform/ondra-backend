import random
import uuid
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from organization.models import Organizations
from fleet.models import Truck, Route, Product
from customers.models import Customer, DeliveryAddress
from dispatch.models import Dispatch, TripMetadata
from users.models import User, DriverProfile


class Command(BaseCommand):
    help = "Generate synthetic completed dispatch records for ETA training."

    RANDOM_SEED = 42

    # Synthetic tanker quantities in litres.
    QUANTITIES = [
        20_000,
        25_000,
        30_000,
        33_000,
        35_000,
        40_000,
        45_000,
    ]

    # Synthetic empty tanker weights in tonnes.
    TARE_WEIGHTS = [
        10.5,
        11.0,
        11.5,
        12.0,
        12.5,
        13.0,
        13.5,
    ]

    # Used only when a route does not yet have
    # standard_distance_km.
    #
    # This is synthetic/estimated data for the prototype.
    AVERAGE_SPEED_KMH = 50

    PRODUCT_DENSITY = 0.82

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-id",
            required=True,
            help="Organization UUID.",
        )

        parser.add_argument(
            "--records",
            type=int,
            default=1500,
            help="Number of synthetic dispatches to create.",
        )

    @transaction.atomic
    def handle(self, *args, **options):

        random.seed(self.RANDOM_SEED)

        organization_id = options["organization_id"]
        total_records = options["records"]

        # =====================================================
        # ORGANIZATION
        # =====================================================

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
            self.style.SUCCESS(
                f"Organization: {organization.name}"
            )
        )

        # =====================================================
        # ROUTES
        #
        # IMPORTANT:
        # We only require expected_tat_hours.
        #
        # standard_distance_km may currently be NULL.
        # =====================================================

        routes = list(
            Route.objects.filter(
                organization=organization,
                expected_tat_hours__isnull=False,
            )
            .select_related("origin_terminal")
            .order_by("origin_terminal__name", "destination")
        )

        if not routes:

            self.stdout.write(
                self.style.ERROR(
                    "No usable routes found. "
                    "Routes must have expected_tat_hours."
                )
            )

            return

        # =====================================================
        # PRODUCTS
        # =====================================================

        products = list(
            Product.objects.filter(
                organization=organization,
            )
        )

        if not products:

            self.stdout.write(
                self.style.ERROR(
                    "No products found for this organization. "
                    "Run your product seeder first."
                )
            )

            return

        # =====================================================
        # TRUCKS
        # =====================================================

        trucks = list(
            Truck.objects.filter(
                organization=organization,
                is_active=True,
                home_terminal__isnull=False,
            )
            .select_related("home_terminal")
        )

        if not trucks:

            self.stdout.write(
                self.style.ERROR(
                    "No active trucks with home terminals found."
                )
            )

            return

        # =====================================================
        # DRIVERS
        #
        # Drivers are NOT tied permanently to trucks.
        # =====================================================

        driver_profiles = list(
            DriverProfile.objects.filter(
                user__is_active=True,
            ).select_related("user")
        )

        if not driver_profiles:

            self.stdout.write(
                self.style.ERROR(
                    "No DriverProfiles found. "
                    "Run seed_drivers first."
                )
            )

            return

        drivers = [
            profile.user
            for profile in driver_profiles
        ]

        # =====================================================
        # DELIVERY ADDRESSES
        #
        # These are the customer destinations that were
        # already seeded from your destination data.
        # =====================================================

        delivery_addresses = list(
            DeliveryAddress.objects.filter(
                customer__organization=organization,
                is_active=True,
            )
            .select_related("customer")
        )

        if not delivery_addresses:

            self.stdout.write(
                self.style.ERROR(
                    "No delivery addresses found for this organization."
                )
            )

            return

        # =====================================================
        # TRUCKS BY TERMINAL
        # =====================================================

        trucks_by_terminal = {}

        for truck in trucks:

            terminal_id = truck.home_terminal_id

            trucks_by_terminal.setdefault(
                terminal_id,
                [],
            ).append(truck)

        # =====================================================
        # DISPLAY SUMMARY
        # =====================================================

        self.stdout.write("")
        self.stdout.write(f"Routes: {len(routes)}")
        self.stdout.write(f"Products: {len(products)}")
        self.stdout.write(f"Trucks: {len(trucks)}")
        self.stdout.write(f"Drivers: {len(drivers)}")
        self.stdout.write(
            f"Delivery addresses: {len(delivery_addresses)}"
        )
        self.stdout.write("")

        # =====================================================
        # GENERATE DISPATCHES
        # =====================================================

        created_dispatches = 0
        created_metadata = 0

        skipped_no_truck = 0
        skipped_no_customer = 0
        skipped_no_terminal = 0

        base_date = timezone.now() - timedelta(days=365)

        # -----------------------------------------------------
        # Cycle through routes so all routes receive
        # representation in the synthetic dataset.
        # -----------------------------------------------------

        for index in range(total_records):

            route = routes[index % len(routes)]

            # =================================================
            # ORIGIN TERMINAL
            # =================================================

            terminal = route.origin_terminal

            if not terminal:

                skipped_no_terminal += 1

                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping route {route.id}: "
                        "no origin terminal."
                    )
                )

                continue

            # =================================================
            # TRUCK
            # =================================================

            terminal_trucks = trucks_by_terminal.get(
                terminal.id,
                [],
            )

            if not terminal_trucks:

                skipped_no_truck += 1

                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping {terminal.name} → "
                        f"{route.destination}: "
                        "no trucks at terminal."
                    )
                )

                continue

            truck = random.choice(
                terminal_trucks
            )

            # =================================================
            # CUSTOMER / DELIVERY ADDRESS
            #
            # IMPORTANT:
            # Do NOT randomly fall back to another customer.
            #
            # We want:
            #
            # Route destination
            #       ↓
            # Customer delivery address
            #
            # to remain consistent.
            # =================================================

            matching_addresses = [
                address
                for address in delivery_addresses
                if self.destination_matches(
                    route.destination,
                    address,
                )
            ]

            if not matching_addresses:

                skipped_no_customer += 1

                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping {terminal.name} → "
                        f"{route.destination}: "
                        "no matching customer delivery address."
                    )
                )

                continue

            delivery_address = random.choice(
                matching_addresses
            )

            customer = delivery_address.customer

            # =================================================
            # DRIVER
            # =================================================

            driver = random.choice(
                drivers
            )

            # =================================================
            # PRODUCT
            # =================================================

            product = random.choice(
                products
            )

            # =================================================
            # QUANTITY
            # =================================================

            quantity = random.choice(
                self.QUANTITIES
            )

            if truck.capacity:

                quantity = min(
                    quantity,
                    truck.capacity,
                )

            # =================================================
            # HISTORICAL DISPATCH DATE
            # =================================================

            dispatch_date = (
                base_date
                + timedelta(
                    days=random.randint(
                        0,
                        364,
                    ),
                    hours=random.randint(
                        5,
                        18,
                    ),
                    minutes=random.randint(
                        0,
                        59,
                    ),
                )
            )

            expected_departure = dispatch_date

            # =================================================
            # ACTUAL DEPARTURE
            # =================================================

            departure_delay = random.randint(
                -15,
                90,
            )

            actual_departure = (
                expected_departure
                + timedelta(
                    minutes=departure_delay
                )
            )

            # =================================================
            # ROUTE EXPECTED TAT
            # =================================================

            expected_tat_hours = float(
                route.expected_tat_hours
            )

            base_eta_minutes = (
                expected_tat_hours * 60
            )

            # =================================================
            # ACTUAL TRIP DURATION
            #
            # THIS BECOMES THE ML TARGET.
            # =================================================

            variation = random.gauss(
                0,
                base_eta_minutes * 0.10,
            )

            actual_duration_minutes = (
                base_eta_minutes
                + variation
            )

            # Prevent unrealistically short trips.

            actual_duration_minutes = max(
                actual_duration_minutes,
                base_eta_minutes * 0.70,
            )

            # =================================================
            # TIME-BASED OPERATIONAL VARIATION
            # =================================================

            hour = actual_departure.hour

            # Morning departure effect.

            if hour in [7, 8, 9]:

                actual_duration_minutes *= (
                    random.uniform(
                        1.00,
                        1.08,
                    )
                )

            # Friday / Saturday effect.

            if actual_departure.weekday() in [4, 5]:

                actual_duration_minutes *= (
                    random.uniform(
                        1.00,
                        1.05,
                    )
                )

            # =================================================
            # ACTUAL ARRIVAL
            #
            # This is the ground-truth outcome.
            # =================================================

            actual_arrival = (
                actual_departure
                + timedelta(
                    minutes=actual_duration_minutes
                )
            )

            # =================================================
            # SYNTHETIC BASELINE ETA
            #
            # This is NOT the actual arrival.
            #
            # It represents the route's expected ETA before
            # considering the actual trip outcome.
            # =================================================

            eta = (
                actual_departure
                + timedelta(
                    minutes=base_eta_minutes
                )
            )

            # =================================================
            # DISTANCE
            #
            # Use actual route distance if it exists.
            #
            # Otherwise estimate it from TAT for now.
            # =================================================

            if route.standard_distance_km is not None:

                distance_km = float(
                    route.standard_distance_km
                )

            else:

                distance_km = (
                    base_eta_minutes / 60
                ) * self.AVERAGE_SPEED_KMH

            # =================================================
            # WAYBILL / SALES ORDER
            #
            # UUID suffix prevents collisions if the command
            # is run more than once.
            # =================================================

            unique_suffix = uuid.uuid4().hex[:10].upper()

            waybill_number = (
                f"SYN-WB-{unique_suffix}"
            )

            sales_order_no = (
                f"SYN-SO-{unique_suffix}"
            )

            # =================================================
            # CREATE DISPATCH
            # =================================================

            dispatch = Dispatch.objects.create(
                waybill_number=waybill_number,
                sales_order_no=sales_order_no,

                truck=truck,
                driver=driver,

                customer=customer,
                delivery_address=delivery_address,

                origin_terminal=terminal,
                route=route,

                product=product,

                quantity=Decimal(
                    str(quantity)
                ),

                status=Dispatch.Status.DELIVERED,

                expected_departure=expected_departure,
                actual_departure=actual_departure,

                # Synthetic baseline ETA.
                eta=eta,

                # Actual ground-truth arrival.
                actual_arrival=actual_arrival,

                notes=(
                    "Synthetic ETA training record. "
                    "Actual arrival and duration are simulated."
                ),

                organization=organization,

                created_by=self.get_created_by(),

                created_at=dispatch_date,
            )

            created_dispatches += 1

            # =================================================
            # TRIP METADATA
            # =================================================

            tare_weight = random.choice(
                self.TARE_WEIGHTS
            )

            # Approximate product weight in tonnes.

            net_weight = (
                quantity
                * self.PRODUCT_DENSITY
                / 1000
            )

            gross_weight = (
                tare_weight
                + net_weight
            )

            # =================================================
            # ODOMETER
            # =================================================

            odometer_departure = random.randint(
                50_000,
                500_000,
            )

            odometer_arrival = (
                odometer_departure
                + int(round(distance_km))
            )

            # =================================================
            # WEIGHBRIDGE TIMES
            # =================================================

            scale_in_time = (
                actual_departure
                - timedelta(
                    minutes=random.randint(
                        30,
                        120,
                    )
                )
            )

            scale_out_time = (
                actual_departure
                - timedelta(
                    minutes=random.randint(
                        5,
                        20,
                    )
                )
            )

            # =================================================
            # TRIP METADATA
            # =================================================

            TripMetadata.objects.create(
                dispatch=dispatch,

                scale_in_time=scale_in_time,
                scale_out_time=scale_out_time,

                tare_weight=Decimal(
                    str(
                        round(
                            tare_weight,
                            3,
                        )
                    )
                ),

                gross_weight=Decimal(
                    str(
                        round(
                            gross_weight,
                            3,
                        )
                    )
                ),

                net_weight=Decimal(
                    str(
                        round(
                            net_weight,
                            3,
                        )
                    )
                ),

                rob="0",

                seal_numbers=(
                    f"SYN-SEAL-{unique_suffix}"
                ),

                loading_temp=Decimal(
                    str(
                        round(
                            random.uniform(
                                25,
                                38,
                            ),
                            2,
                        )
                    )
                ),

                fuel_intank=Decimal(
                    str(
                        random.randint(
                            100,
                            500,
                        )
                    )
                ),

                odometer_departure=(
                    odometer_departure
                ),

                odometer_arrival=(
                    odometer_arrival
                ),

                remarks=(
                    "Synthetic ETA training record."
                ),
            )

            created_metadata += 1

            # =================================================
            # PROGRESS
            # =================================================

            if created_dispatches % 100 == 0:

                self.stdout.write(
                    f"Created {created_dispatches} "
                    f"dispatches..."
                )

        # =====================================================
        # SUMMARY
        # =====================================================

        self.stdout.write("")
        self.stdout.write("=" * 70)

        self.stdout.write(
            self.style.SUCCESS(
                "DISPATCH SEEDING COMPLETED"
            )
        )

        self.stdout.write(
            f"Organization: {organization.name}"
        )

        self.stdout.write(
            f"Routes available: {len(routes)}"
        )

        self.stdout.write(
            f"Dispatches created: {created_dispatches}"
        )

        self.stdout.write(
            f"Trip metadata created: {created_metadata}"
        )

        self.stdout.write(
            f"Skipped — no terminal: {skipped_no_terminal}"
        )

        self.stdout.write(
            f"Skipped — no trucks: {skipped_no_truck}"
        )

        self.stdout.write(
            f"Skipped — no customer address: "
            f"{skipped_no_customer}"
        )

        self.stdout.write(
            f"Requested records: {total_records}"
        )

        self.stdout.write("=" * 70)

    # =========================================================
    # DESTINATION MATCHING
    # =========================================================

    @staticmethod
    def destination_matches(
        destination,
        delivery_address,
    ):
        """
        Match a Route destination to a seeded
        DeliveryAddress.

        Examples:

            ABUJA
            ABUJA, NIGERIA

            PHC
            PORT HARCOURT
            PORT-HARCOURT
            RIVERS

            AKWAIBOM
            AKWA IBOM
            UYO
        """

        if not destination:
            return False

        destination = (
            str(destination)
            .strip()
            .upper()
        )

        address = (
            str(delivery_address.address or "")
            .strip()
            .upper()
        )

        label = (
            str(delivery_address.label or "")
            .strip()
            .upper()
        )

        # -----------------------------------------------------
        # Normalize common punctuation.
        # -----------------------------------------------------

        destination_normalized = (
            destination
            .replace("-", " ")
            .replace(",", " ")
        )

        address_normalized = (
            address
            .replace("-", " ")
            .replace(",", " ")
        )

        label_normalized = (
            label
            .replace("-", " ")
            .replace(",", " ")
        )

        # -----------------------------------------------------
        # Direct matching.
        # -----------------------------------------------------

        if destination_normalized in address_normalized:
            return True

        if destination_normalized in label_normalized:
            return True

        # -----------------------------------------------------
        # Aliases.
        # -----------------------------------------------------

        aliases = {
            "PHC": [
                "PORT HARCOURT",
                "RIVERS",
            ],

            "PORT HARCOURT": [
                "PHC",
                "RIVERS",
            ],

            "RIVERS": [
                "PORT HARCOURT",
                "PHC",
            ],

            "ABUJA": [
                "FCT",
            ],

            "FCT": [
                "ABUJA",
            ],

            "AKWAIBOM": [
                "AKWA IBOM",
                "UYO",
            ],

            "AKWA IBOM": [
                "AKWAIBOM",
                "UYO",
            ],

            "UYO": [
                "AKWAIBOM",
                "AKWA IBOM",
            ],

            "SAPELE": [
                "DELTA",
            ],

            "DELTA": [
                "SAPELE",
            ],
        }

        for alias in aliases.get(
            destination_normalized,
            [],
        ):

            alias_normalized = (
                alias
                .replace("-", " ")
                .replace(",", " ")
            )

            if alias_normalized in address_normalized:
                return True

            if alias_normalized in label_normalized:
                return True

        return False

    # =========================================================
    # CREATED BY
    # =========================================================

    @staticmethod
    def get_created_by():

        """
        Logistics user responsible for creating dispatches.

        Current synthetic/test logistics user:
        d097a1aa-a51a-459f-964c-5c0dad32aec8
        """

        user_id = (
            "d097a1aa-a51a-459f-964c-5c0dad32aec8"
        )

        try:

            return User.objects.get(
                id=user_id
            )

        except User.DoesNotExist:

            return None
