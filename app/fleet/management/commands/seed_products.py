from django.core.management.base import BaseCommand

from fleet.models import Product
from organization.models import Organizations


class Command(BaseCommand):
    help = "Create the standard petroleum products for an organization."

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-id",
            required=True,
            help="UUID of the organization to create products for.",
        )

    def handle(self, *args, **options):
        organization_id = options["organization_id"]

        try:
            organization = Organizations.objects.get(
                id=organization_id
            )
        except Organizations.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f"Organization {organization_id} was not found."
                )
            )
            return

        products = [
            (
                Product.ProductType.PREMIUM_MOTOR_SPIRIT,
                "Premium Motor Spirit (PMS)",
            ),
            (
                Product.ProductType.AUTOMOTIVE_GAS_OIL,
                "Automotive Gas Oil (AGO)",
            ),
            (
                Product.ProductType.DUAL_PURPOSE_KEROSENE,
                "Dual Purpose Kerosene (DPK)",
            ),
            (
                Product.ProductType.HOUSEHOLD_KEROSENE,
                "Household Kerosene (HHK)",
            ),
            (
                Product.ProductType.AVIATION_TURBINE_KEROSENE,
                "Aviation Turbine Kerosene (ATK/Jet A-1)",
            ),
            (
                Product.ProductType.LOW_POUR_FUEL_OIL,
                "Low Pour Fuel Oil (LPFO)",
            ),
            (
                Product.ProductType.HEAVY_FUEL_OIL,
                "Heavy Fuel Oil (HFO)",
            ),
            (
                Product.ProductType.LIQUEFIED_PETROLEUM_GAS,
                "Liquefied Petroleum Gas (LPG)",
            ),
            (
                Product.ProductType.COMPRESSED_NATURAL_GAS,
                "Compressed Natural Gas (CNG)",
            ),
            (
                Product.ProductType.LIQUEFIED_NATURAL_GAS,
                "Liquefied Natural Gas (LNG)",
            ),
            (
                Product.ProductType.NATURAL_GAS,
                "Natural Gas",
            ),
            (
                Product.ProductType.BITUMEN_60_70,
                "Bitumen 60/70",
            ),
            (
                Product.ProductType.BITUMEN_80_100,
                "Bitumen 80/100",
            ),
            (
                Product.ProductType.BITUMEN_40_50,
                "Bitumen 40/50",
            ),
            (
                Product.ProductType.POLYMER_MODIFIED_BITUMEN,
                "Polymer Modified Bitumen (PMB)",
            ),
            (
                Product.ProductType.CATIONIC_BITUMEN_EMULSION,
                "Cationic Bitumen Emulsion",
            ),
            (
                Product.ProductType.ANIONIC_BITUMEN_EMULSION,
                "Anionic Bitumen Emulsion",
            ),
            (
                Product.ProductType.CUTBACK_BITUMEN,
                "Cutback Bitumen",
            ),
            (
                Product.ProductType.CRUMB_RUBBER_MODIFIED_BITUMEN,
                "Crumb Rubber Modified Bitumen (CRMB)",
            ),
            (
                Product.ProductType.ENGINE_OIL,
                "Engine Oil",
            ),
            (
                Product.ProductType.GEAR_OIL,
                "Gear Oil",
            ),
            (
                Product.ProductType.HYDRAULIC_OIL,
                "Hydraulic Oil",
            ),
            (
                Product.ProductType.TRANSMISSION_FLUID,
                "Transmission Fluid",
            ),
            (
                Product.ProductType.GREASE,
                "Grease",
            ),
            (
                Product.ProductType.BASE_OIL,
                "Base Oil",
            ),
            (
                Product.ProductType.PARAFFIN_WAX,
                "Paraffin Wax",
            ),
            (
                Product.ProductType.SOLVENT,
                "Industrial Solvent",
            ),
            (
                Product.ProductType.MARINE_GAS_OIL,
                "Marine Gas Oil (MGO)",
            ),
            (
                Product.ProductType.MARINE_DIESEL_OIL,
                "Marine Diesel Oil (MDO)",
            ),
        ]

        created = 0
        existing = 0

        for product_type, description in products:

            product, was_created = Product.objects.get_or_create(
                name=product_type,
                organization=organization,
                defaults={
                    "description": description,
                    "unit": "litres",
                },
            )

            if was_created:
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created: {product.get_name_display()}"
                    )
                )
            else:
                existing += 1
                self.stdout.write(
                    f"Already exists: {product.get_name_display()}"
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created: {created}, "
                f"Already existed: {existing}"
            )
        )
