import os
import requests
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = "Download NYC rent stabilized units PDF data for each borough and save to myproject/static/data."

    def handle(self, *args, **options):
        # Dictionary mapping borough names to their PDF URLs.
        pdf_urls = {
            'Manhattan': 'https://rentguidelinesboard.cityofnewyork.us/wp-content/uploads/2024/11/2023-DHCR-Bldg-File-Manhattan.pdf',
            'Brooklyn': 'https://rentguidelinesboard.cityofnewyork.us/wp-content/uploads/2024/11/2023-DHCR-Bldg-File-Brooklyn.pdf',
            'Bronx': 'https://rentguidelinesboard.cityofnewyork.us/wp-content/uploads/2024/11/2023-DHCR-Bldg-File-Bronx.pdf',
            'Queens': 'https://rentguidelinesboard.cityofnewyork.us/wp-content/uploads/2024/11/2023-DHCR-Bldg-File-Queens.pdf',
            'Staten_Island': 'https://rentguidelinesboard.cityofnewyork.us/wp-content/uploads/2024/11/2023-DHCR-Bldg-File-Staten-Island.pdf'
        }

        # Define the target folder using the BASE_DIR defined in settings.
        # This will resolve to 'myproject/static/data' (assuming BASE_DIR points to the myproject folder).
        data_dir = os.path.join(settings.BASE_DIR, 'static', 'data')

        # Create the directory if it doesn't exist.
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            self.stdout.write(self.style.SUCCESS(f"Created directory: {data_dir}"))
        else:
            self.stdout.write(f"Using existing directory: {data_dir}")

        # Loop over each borough and download the PDF.
        for borough, url in pdf_urls.items():
            self.stdout.write(f"Downloading {borough} data from: {url}")
            try:
                response = requests.get(url)
                response.raise_for_status()
            except requests.RequestException as e:
                self.stdout.write(self.style.ERROR(f"Error downloading {borough}: {e}"))
                continue

            # Save the PDF file.
            file_name = f"{borough}.pdf"
            file_path = os.path.join(data_dir, file_name)
            try:
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                self.stdout.write(self.style.SUCCESS(f"Saved {borough} data to {file_path}"))
            except IOError as e:
                self.stdout.write(self.style.ERROR(f"Error saving {borough} data: {e}"))
