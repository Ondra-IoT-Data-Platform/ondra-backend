from django.core.management.base import BaseCommand, CommandError
from organization.models import Organizations
from eta.trainer import train_eta_model


class Command(BaseCommand):
    help = "Trains or retrains the XGBoost ETA model for one or all organizations"

    def add_arguments(self, parser):
        parser.add_argument(
            "--org-id",
            type=str,
            help="UUID of a specific organization to train for. Omit to train all.",
        )

    def handle(self, *args, **options):
        org_id = options.get("org_id")

        if org_id:
            orgs = Organizations.objects.filter(id=org_id, is_active=True)
        else:
            orgs = Organizations.objects.filter(is_active=True)

        if not orgs.exists():
            raise CommandError("No matching active organizations found.")

        for org in orgs:
            self.stdout.write(f"\nTraining ETA model for: {org.name}")
            result = train_eta_model(org.id)

            if result["status"] == "skipped":
                self.stdout.write(
                    self.style.WARNING(f"  Skipped — {result['reason']}")
                )
            elif result["status"] == "success":
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Version {result['version']} trained successfully\n"
                        f"  Records used: {result['records_used']}\n"
                        f"  MAE: {result['mae_minutes']} min\n"
                        f"  RMSE: {result['rmse_minutes']} min\n"
                        f"  MAPE: {result['mape_percentage']}%"
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"  Failed — {result.get('reason', 'unknown error')}")
                )
