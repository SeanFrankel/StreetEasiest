import os
import requests
import zipfile
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

class Command(BaseCommand):
    help = 'Downloads and extracts the median asking rent data CSV file'

    def handle(self, *args, **options):
        # Define the directory where the CSV will be saved.
        # Here we use the project's BASE_DIR and put the file in static/data.
        save_dir = os.path.join(settings.BASE_DIR, 'static', 'data')
        os.makedirs(save_dir, exist_ok=True)

        # URL of the ZIP file from StreetEasy
        url = "https://cdn-charts.streeteasy.com/rentals/All/medianAskingRent_All.zip"
        
        # Define file paths
        zip_path = os.path.join(save_dir, "medianAskingRent_All.zip")
        csv_save_path = os.path.join(save_dir, "medianAskingRent_latest.csv")

        try:
            self.stdout.write("Downloading ZIP file...")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(zip_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            self.stdout.write(self.style.SUCCESS(f"ZIP file downloaded: {zip_path}"))

            # Extract the ZIP file (assuming it contains one CSV file)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                csv_name = zip_ref.namelist()[0]
                zip_ref.extract(csv_name, save_dir)

            # Rename the extracted CSV to a consistent filename
            extracted_csv_path = os.path.join(save_dir, csv_name)
            os.rename(extracted_csv_path, csv_save_path)
            self.stdout.write(self.style.SUCCESS(f"CSV file saved: {csv_save_path}"))

            # Clean up by removing the ZIP file
            os.remove(zip_path)
            self.stdout.write(self.style.SUCCESS("Temporary ZIP file removed."))

        except Exception as e:
            raise CommandError(f"Error during file download or extraction: {e}")
