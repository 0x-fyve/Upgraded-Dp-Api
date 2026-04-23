import json
from django.core.management.base import BaseCommand
from Dp_Api.models import Profile

class Command(BaseCommand):
    help = "Seed profiles into database"

    def handle(self, *args, **kwargs):
        with open("profiles.json") as f:
            data = json.load(f)["profiles"]

        count = 0

        for item in data:
            obj, created = Profile.objects.get_or_create(
                name=item["name"],
                defaults={
                    "gender": item["gender"],
                    "gender_probability": item["gender_probability"],
                    "age": item["age"],
                    "age_group": item["age_group"],
                    "country_id": item["country_id"],
                    "country_name": item["country_name"],
                    "country_probability": item["country_probability"],
                }
            )
            if created:
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {count} new profiles"))