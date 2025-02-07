import os
import requests
import zipfile
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

class Command(BaseCommand):
    help = 'Downloads and extracts the StreetEasy rental data CSV files for various bedroom types and data types.'

    def handle(self, *args, **options):
        # Define the directory where the CSVs will be saved.
        save_dir = os.path.join(settings.BASE_DIR, 'static', 'data')
        os.makedirs(save_dir, exist_ok=True)

        # List of files to download.
        # Each entry defines the URL of the ZIP file and the target CSV file name.
        files_to_download = [
            {
                "url": "https://cdn-charts.streeteasy.com/rentals/All/medianAskingRent_All.zip",
                "target": "medianAskingRent_All.csv"
            },
            {
                "url": "https://cdn-charts.streeteasy.com/rentals/All/rentalInventory_All.zip",
                "target": "rentalInventory_All.csv"
            },
            {
                "url": "https://cdn-charts.streeteasy.com/rentals/Studio/medianAskingRent_Studio.zip",
                "target": "medianAskingRent_Studio.csv"
            },
            {
                "url": "https://cdn-charts.streeteasy.com/rentals/Studio/rentalInventory_Studio.zip",
                "target": "rentalInventory_Studio.csv"
            },
            {
                "url": "https://cdn-charts.streeteasy.com/rentals/OneBd/medianAskingRent_OneBd.zip",
                "target": "medianAskingRent_OneBd.csv"
            },
            {
                "url": "https://cdn-charts.streeteasy.com/rentals/OneBd/rentalInventory_OneBd.zip",
                "target": "rentalInventory_OneBd.csv"
            },
            {
                "url": "https://cdn-charts.streeteasy.com/rentals/TwoBd/medianAskingRent_TwoBd.zip",
                "target": "medianAskingRent_TwoBd.csv"
            },
            {
                "url": "https://cdn-charts.streeteasy.com/rentals/TwoBd/rentalInventory_TwoBd.zip",
                "target": "rentalInventory_TwoBd.csv"
            },
            {
                "url": "https://cdn-charts.streeteasy.com/rentals/ThreePlusBd/medianAskingRent_ThreePlusBd.zip",
                "target": "medianAskingRent_ThreePlusBd.csv"
            },
            {
                "url": "https://cdn-charts.streeteasy.com/rentals/ThreePlusBd/rentalInventory_ThreePlusBd.zip",
                "target": "rentalInventory_ThreePlusBd.csv"
            },
        ]

        # Loop through each file, download, extract, and rename.
        for file_info in files_to_download:
            url = file_info["url"]
            target_csv = file_info["target"]
            zip_filename = target_csv.replace('.csv', '.zip')
            zip_path = os.path.join(save_dir, zip_filename)
            csv_save_path = os.path.join(save_dir, target_csv)

            try:
                self.stdout.write(f"Downloading {url} ...")
                response = requests.get(url, stream=True)
                response.raise_for_status()

                # Write the ZIP file to disk.
                with open(zip_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                self.stdout.write(self.style.SUCCESS(f"Downloaded: {zip_path}"))

                # Extract the ZIP file (assumes one CSV file inside)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # Get the first file in the archive.
                    csv_inside = zip_ref.namelist()[0]
                    zip_ref.extract(csv_inside, save_dir)
                self.stdout.write(self.style.SUCCESS(f"Extracted: {csv_inside}"))

                # Rename the extracted CSV file to our target name.
                extracted_csv_path = os.path.join(save_dir, csv_inside)
                os.rename(extracted_csv_path, csv_save_path)
                self.stdout.write(self.style.SUCCESS(f"Saved CSV as: {csv_save_path}"))

                # Remove the temporary ZIP file.
                os.remove(zip_path)
                self.stdout.write(self.style.SUCCESS("Removed temporary ZIP file.\n"))

            except Exception as e:
                raise CommandError(f"Error processing {url}: {e}")

        self.stdout.write(self.style.SUCCESS("All files have been downloaded and extracted successfully."))
