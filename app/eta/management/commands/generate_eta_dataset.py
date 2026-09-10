import random
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand
from django.db.models import Prefetch

from organization.models import Organizations
from dispatch.models import Dispatch, TripMetadata


class Command(BaseCommand):
    help = "Generate an ETA training CSV from synthetic dispatch records."

    RANDOM_SEED = 42

    # Used ONLY when Route.standard_distance_km is unavailable.
    # This is synthetic distance estimation, not real road distance.
    DEFAULT_AVERAGE_SPEED_KMH = 50

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-id",
            required=True,
            help="Organization UUID.",
        )

        parser.add_argument(
            "--output",
            default="eta_training_dataset.csv",
            help="Output CSV file path.",
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Optional maximum number of dispatches to include.",
        )

    def handle(self, *args, **options):

        random.seed(self.RANDOM_SEED)

        organization_id = options["organization_id"]
        output_path = Path(options["output"])
        limit = options["limit"]

        # ---------------------------------------------------------
        # ORGANIZATION
        # ---------------------------------------------------------

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

        # ---------------------------------------------------------
        # DISPATCHES
        # ---------------------------------------------------------

        queryset = (
            Dispatch.objects
            .filter(
                organization=organization,
                status=Dispatch.Status.DELIVERED,
                actual_departure__isnull=False,
                eta__isnull=False,
            )
            .select_related(
                "truck",
                "customer",
                "delivery_address",
                "origin_terminal",
                "route",
                "product",
            )
            .prefetch_related(
                Prefetch(
                    "trip_metadata",
                    queryset=TripMetadata.objects.all(),
                )
            )
            .order_by("created_at")
        )

        if limit:
            queryset = queryset[:limit]

        dispatches = list(queryset)

        if not dispatches:
            self.stdout.write(
                self.style.ERROR(
                    "No completed dispatches found for this organization."
                )
            )
            return

        self.stdout.write(
            f"Completed dispatches found: {len(dispatches)}"
        )

        # ---------------------------------------------------------
        # GENERATE DATASET
        # ---------------------------------------------------------

        records = []

        skipped = 0

        for dispatch in dispatches:

            # -----------------------------------------------------
            # REQUIRED RELATIONS
            # -----------------------------------------------------

            if not dispatch.route:
                skipped += 1
                continue

            if not dispatch.origin_terminal:
                skipped += 1
                continue

            if not dispatch.actual_departure:
                skipped += 1
                continue

            if not dispatch.eta:
                skipped += 1
                continue

            # -----------------------------------------------------
            # ACTUAL TRIP DURATION
            #
            # ETA is currently being used as the synthetic
            # completed-arrival timestamp.
            # -----------------------------------------------------

            actual_duration_seconds = (
                dispatch.eta - dispatch.actual_departure
            ).total_seconds()

            actual_duration_minutes = (
                actual_duration_seconds / 60
            )

            if actual_duration_minutes <= 0:
                skipped += 1
                continue

            # -----------------------------------------------------
            # ROUTE
            # -----------------------------------------------------

            route = dispatch.route

            expected_tat_hours = float(
                route.expected_tat_hours
            )

            base_eta_minutes = (
                expected_tat_hours * 60
            )

            # -----------------------------------------------------
            # DISTANCE
            #
            # Prefer actual route distance.
            #
            # If it doesn't exist, derive a synthetic distance
            # from expected travel time.
            # -----------------------------------------------------

            if route.standard_distance_km is not None:

                distance_km = float(
                    route.standard_distance_km
                )

                distance_source = "route"

            else:

                distance_km = (
                    base_eta_minutes / 60
                ) * self.DEFAULT_AVERAGE_SPEED_KMH

                distance_source = "synthetic"

            # -----------------------------------------------------
            # DEPARTURE FEATURES
            # -----------------------------------------------------

            departure = dispatch.actual_departure

            hour_of_day = departure.hour

            day_of_week = departure.weekday()

            is_weekend = (
                1
                if day_of_week >= 5
                else 0
            )

            is_peak_hour = (
                1
                if hour_of_day in [7, 8, 9, 16, 17, 18]
                else 0
            )

            # -----------------------------------------------------
            # TRUCK
            # -----------------------------------------------------

            truck = dispatch.truck

            truck_capacity = (
                float(truck.capacity)
                if truck.capacity
                else None
            )

            # -----------------------------------------------------
            # QUANTITY
            # -----------------------------------------------------

            quantity = float(
                dispatch.quantity
            )

            # -----------------------------------------------------
            # LOAD UTILIZATION
            #
            # Quantity / truck capacity.
            # -----------------------------------------------------

            if truck_capacity and truck_capacity > 0:

                load_utilization = (
                    quantity / truck_capacity
                )

            else:

                load_utilization = None

            # -----------------------------------------------------
            # PRODUCT
            # -----------------------------------------------------

            product = dispatch.product

            # Keep product name for human readability.
            product_name = (
                product.name
                if product
                else "Unknown"
            )

            # -----------------------------------------------------
            # DELIVERY ADDRESS
            # -----------------------------------------------------

            delivery_address = (
                dispatch.delivery_address
            )

            destination_address = ""

            if delivery_address:

                destination_address = (
                    str(delivery_address.address)
                )

            # -----------------------------------------------------
            # CUSTOMER
            # -----------------------------------------------------

            customer = dispatch.customer

            customer_name = (
                str(customer)
                if customer
                else ""
            )

            # -----------------------------------------------------
            # ROUTE NAME
            # -----------------------------------------------------

            route_destination = (
                route.destination
                if route.destination
                else ""
            )

            # -----------------------------------------------------
            # TRIP METADATA
            # -----------------------------------------------------

            try:

                metadata = (
                    dispatch.trip_metadata
                )

            except TripMetadata.DoesNotExist:

                metadata = None

            # -----------------------------------------------------
            # METADATA FEATURES
            # -----------------------------------------------------

            tare_weight = None
            gross_weight = None
            net_weight = None
            loading_temp = None
            fuel_intank = None

            if metadata:

                if metadata.tare_weight is not None:
                    tare_weight = float(
                        metadata.tare_weight
                    )

                if metadata.gross_weight is not None:
                    gross_weight = float(
                        metadata.gross_weight
                    )

                if metadata.net_weight is not None:
                    net_weight = float(
                        metadata.net_weight
                    )

                if metadata.loading_temp is not None:
                    loading_temp = float(
                        metadata.loading_temp
                    )

                if metadata.fuel_intank is not None:
                    fuel_intank = float(
                        metadata.fuel_intank
                    )

            # -----------------------------------------------------
            # CREATE RECORD
            # -----------------------------------------------------

            records.append(
                {
                    # ---------------------------------------------
                    # IDENTIFICATION
                    # ---------------------------------------------

                    "trip_id": str(
                        dispatch.id
                    ),

                    "waybill_number": (
                        dispatch.waybill_number
                    ),

                    # ---------------------------------------------
                    # ROUTE
                    # ---------------------------------------------

                    "origin_terminal": (
                        dispatch.origin_terminal.name
                    ),

                    "destination": (
                        route_destination
                    ),

                    "destination_address": (
                        destination_address
                    ),

                    "route": str(route),

                    "distance_km": round(
                        distance_km,
                        2,
                    ),

                    "distance_source": (
                        distance_source
                    ),

                    # ---------------------------------------------
                    # ROUTE BASELINE
                    # ---------------------------------------------

                    "expected_tat_hours": round(
                        expected_tat_hours,
                        2,
                    ),

                    "base_eta_minutes": round(
                        base_eta_minutes,
                        2,
                    ),

                    # ---------------------------------------------
                    # TIME FEATURES
                    # ---------------------------------------------

                    "departure_hour": (
                        hour_of_day
                    ),

                    "day_of_week": (
                        day_of_week
                    ),

                    "is_weekend": (
                        is_weekend
                    ),

                    "is_peak_hour": (
                        is_peak_hour
                    ),

                    # ---------------------------------------------
                    # PRODUCT
                    # ---------------------------------------------

                    "product_name": (
                        product_name
                    ),

                    "quantity_litres": round(
                        quantity,
                        2,
                    ),

                    # ---------------------------------------------
                    # TRUCK
                    # ---------------------------------------------

                    "truck_type": (
                        truck.truck_type
                    ),

                    "truck_capacity_litres": (
                        truck_capacity
                    ),

                    "load_utilization": (
                        round(
                            load_utilization,
                            4,
                        )
                        if load_utilization is not None
                        else None
                    ),

                    # ---------------------------------------------
                    # TRIP METADATA
                    # ---------------------------------------------

                    "tare_weight_tonnes": (
                        tare_weight
                    ),

                    "gross_weight_tonnes": (
                        gross_weight
                    ),

                    "net_weight_tonnes": (
                        net_weight
                    ),

                    "loading_temperature_c": (
                        loading_temp
                    ),

                    "fuel_at_departure_litres": (
                        fuel_intank
                    ),

                    # ---------------------------------------------
                    # CUSTOMER
                    # ---------------------------------------------

                    "customer": (
                        customer_name
                    ),

                    # ---------------------------------------------
                    # TARGET
                    # ---------------------------------------------

                    "actual_duration_minutes": round(
                        actual_duration_minutes,
                        2,
                    ),

                    "actual_arrival": (
                        dispatch.eta.isoformat()
                    ),
                }
            )

        # ---------------------------------------------------------
        # DATAFRAME
        # ---------------------------------------------------------

        if not records:

            self.stdout.write(
                self.style.ERROR(
                    "No valid records could be generated."
                )
            )

            return

        output_df = pd.DataFrame(records)

        # ---------------------------------------------------------
        # SHUFFLE
        # ---------------------------------------------------------

        output_df = (
            output_df
            .sample(
                frac=1,
                random_state=self.RANDOM_SEED,
            )
            .reset_index(drop=True)
        )

        # ---------------------------------------------------------
        # SAVE
        # ---------------------------------------------------------

        output_df.to_csv(
            output_path,
            index=False,
        )

        # ---------------------------------------------------------
        # SUMMARY
        # ---------------------------------------------------------

        self.stdout.write("")
        self.stdout.write("=" * 70)

        self.stdout.write(
            self.style.SUCCESS(
                "ETA TRAINING DATASET GENERATED"
            )
        )

        self.stdout.write(
            f"Organization: {organization.name}"
        )

        self.stdout.write(
            f"Records generated: {len(output_df)}"
        )

        self.stdout.write(
            f"Records skipped: {skipped}"
        )

        self.stdout.write(
            f"Routes represented: "
            f"{output_df['destination'].nunique()}"
        )

        self.stdout.write(
            f"Products represented: "
            f"{output_df['product_name'].nunique()}"
        )

        self.stdout.write(
            f"Terminals represented: "
            f"{output_df['origin_terminal'].nunique()}"
        )

        self.stdout.write(
            f"Mean trip duration: "
            f"{output_df['actual_duration_minutes'].mean():.2f} minutes"
        )

        self.stdout.write(
            f"Mean distance: "
            f"{output_df['distance_km'].mean():.2f} km"
        )

        self.stdout.write(
            f"Dataset saved to: {output_path}"
        )

        self.stdout.write("=" * 70)
