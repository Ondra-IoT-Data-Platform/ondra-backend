from django.core.management.base import BaseCommand
from django.db import transaction

from organization.models import Organizations
from customers.models import Customer, DeliveryAddress


class Command(BaseCommand):
    help = (
        "Create synthetic customers and delivery addresses "
        "from the destinations in the logistics route sheet."
    )

    DESTINATIONS = [
        "PORT-HAROURT",
        "SAPELE",
        "ABIA",
        "ABUJA",
        "AKWAIBOM",
        "ANAMBRA",
        "BAUCHI",
        "BAYELSA",
        "BENUE",
        "BORNO",
        "RIVER",
        "EBONYI",
        "BIDA",
        "MINNA",
        "MOKWA",
        "JEBBA",
        "KAIAMA",
        "ABA",
        "UYO",
        "CALABAR",
        "OBURARA",
        "EKITI",
        "ADO-EKITI",
        "ENUGU",
        "GOMBE",
        "IMO",
        "JIGAWA",
        "KADUNA",
        "KANO",
        "KATSINA",
        "BIRNIN KEBBI",
        "KOGI",
        "KWARA",
        "LAGOS",
        "EPE",
        "NASARAWA",
        "KONTAGORA",
        "OGUN",
        "ONDO",
        "MOWE",
        "ABEOKUTA",
        "OSUN",
        "OYO",
        "OSOGBO",
        "ILORIN",
        "JOS",
        "RIVERS",
        "SOKOTO",
        "TARABA",
        "ZAMFARA",
        "JALINGO",
        "MAYO BELWA",
        "YOLA",
        "MUBI",
        "BIU",
        "MAIDUGURI",
        "DAMATURU",
        "DUTSE",
        "FUTUA",
        "GUSAU",
        "TALATA MAFARA",
        "UMUAHIA",
        "YENOGOA",
        "OKENE",
        "OGBOMOSO",
        "JOS",
        "GWAGWALADA",
    ]


    DESTINATION_DISPLAY = {
        "PORT-HAROURT": "Port Harcourt",
        "RIVER": "Rivers",
        "RIVERS": "Rivers",
        "AKWAIBOM": "Akwa Ibom",
        "ANAMBRA": "Anambra",
        "BAYELSA": "Bayelsa",
        "BENUE": "Benue",
        "BORNO": "Borno",
        "EBONYI": "Ebonyi",
        "ABIA": "Abia",
        "ABUJA": "Abuja",
        "BAUCHI": "Bauchi",
        "BIDA": "Bida",
        "MINNA": "Minna",
        "MOKWA": "Mokwa",
        "JEBBA": "Jebba",
        "KAIAMA": "Kaiama",
        "ABA": "Aba",
        "UYO": "Uyo",
        "CALABAR": "Calabar",
        "OBURARA": "Obubara",
        "EKITI": "Ekiti",
        "ADO-EKITI": "Ado-Ekiti",
        "ENUGU": "Enugu",
        "GOMBE": "Gombe",
        "IMO": "Imo",
        "JIGAWA": "Jigawa",
        "KADUNA": "Kaduna",
        "KANO": "Kano",
        "KATSINA": "Katsina",
        "BIRNIN KEBBI": "Birnin Kebbi",
        "KOGI": "Kogi",
        "KWARA": "Kwara",
        "LAGOS": "Lagos",
        "EPE": "Epe",
        "NASARAWA": "Nasarawa",
        "KONTAGORA": "Kontagora",
        "OGUN": "Ogun",
        "ONDO": "Ondo",
        "MOWE": "Mowe",
        "ABEOKUTA": "Abeokuta",
        "OSUN": "Osun",
        "OYO": "Oyo",
        "OSOGBO": "Osogbo",
        "ILORIN": "Ilorin",
        "JOS": "Jos",
        "SOKOTO": "Sokoto",
        "TARABA": "Taraba",
        "ZAMFARA": "Zamfara",
        "JALINGO": "Jalingo",
        "MAYO BELWA": "Mayo-Belwa",
        "YOLA": "Yola",
        "MUBI": "Mubi",
        "BIU": "Biu",
        "MAIDUGURI": "Maiduguri",
        "DAMATURU": "Damaturu",
        "DUTSE": "Dutse",
        "FUTUA": "Funtua",
        "GUSAU": "Gusau",
        "TALATA MAFARA": "Talata Mafara",
        "SAPELE": "Sapele",
        "UMUAHIA": "Umuahia",
        "YENOGOA": "Yenagoa",
        "OKENE": "Okene",
        "OGBOMOSO": "Ogbomoso",
        "GWAGWALADA": "Gwagwalada",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-id",
            required=True,
            help="Organization UUID.",
        )

    @staticmethod
    def normalize(value):
        return (
            str(value)
            .strip()
            .upper()
            .replace("–", "-")
            .replace("—", "-")
        )

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

        created_customers = 0
        updated_customers = 0
        created_addresses = 0
        updated_addresses = 0

        # Remove duplicate destination names while preserving
        # the order from the Excel-derived list.

        destinations = list(
            dict.fromkeys(
                self.normalize(destination)
                for destination in self.DESTINATIONS
            )
        )

        self.stdout.write(
            f"Creating customers for "
            f"{len(destinations)} unique destinations."
        )

        # -----------------------------------------------------
        # CREATE CUSTOMERS
        # -----------------------------------------------------

        for index, destination in enumerate(
            destinations,
            start=1,
        ):

            display_name = self.DESTINATION_DISPLAY.get(
                destination,
                destination.title(),
            )

            customer_name = (
                f"Synthetic Customer - {display_name}"
            )

            customer, created = (
                Customer.objects.update_or_create(
                    organization=organization,
                    name=customer_name,
                    defaults={
                        "email": (
                            f"customer{index}"
                            f"@synthetic.example"
                        ),
                        "phone_number": (
                            f"+234800000{index:04d}"
                        ),
                        "address": (
                            f"{display_name}, Nigeria"
                        ),
                        "is_active": True,
                    },
                )
            )

            if created:
                created_customers += 1
            else:
                updated_customers += 1

            # -------------------------------------------------
            # DELIVERY ADDRESS
            # -------------------------------------------------

            delivery_label = (
                f"{display_name} Delivery Site"
            )

            delivery_address, address_created = (
                DeliveryAddress.objects.update_or_create(
                    customer=customer,
                    label=delivery_label,
                    defaults={
                        "address": (
                            f"{display_name}, Nigeria"
                        ),
                        "latitude": None,
                        "longitude": None,
                        "is_default": True,
                        "is_active": True,
                    },
                )
            )

            if address_created:
                created_addresses += 1
            else:
                updated_addresses += 1

        # -----------------------------------------------------
        # SUMMARY
        # -----------------------------------------------------

        self.stdout.write("")
        self.stdout.write("=" * 60)

        self.stdout.write(
            self.style.SUCCESS(
                "CUSTOMER SEEDING COMPLETED"
            )
        )

        self.stdout.write(
            f"Organization: {organization.name}"
        )

        self.stdout.write(
            f"Unique destinations: {len(destinations)}"
        )

        self.stdout.write(
            f"Customers created: {created_customers}"
        )

        self.stdout.write(
            f"Customers updated: {updated_customers}"
        )

        self.stdout.write(
            f"Delivery addresses created: "
            f"{created_addresses}"
        )

        self.stdout.write(
            f"Delivery addresses updated: "
            f"{updated_addresses}"
        )

        self.stdout.write("=" * 60)
