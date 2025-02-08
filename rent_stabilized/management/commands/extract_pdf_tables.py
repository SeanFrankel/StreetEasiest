import os
import pandas as pd
import tabula
import requests

from django.conf import settings
from django.core.management.base import BaseCommand

def expand_building_ranges(df):
    """
    Look for rows where the BLDGNO1 column contains a range (e.g. "303 TO 309")
    and expand that row into multiple rows—one for each building number in the range.
    """
    new_rows = []
    for idx, row in df.iterrows():
        bldg_val = str(row.get("BLDGNO1", "")).strip()
        # Check if " TO " is present (you can adjust the delimiter if needed)
        if " TO " in bldg_val:
            parts = bldg_val.split("TO")
            try:
                start = int(parts[0].strip())
                end = int(parts[1].strip())
            except ValueError:
                # If conversion fails, just append the original row.
                new_rows.append(row)
                continue
            # Generate a new row for each building number in the range.
            for num in range(start, end + 1):
                new_row = row.copy()
                new_row["BLDGNO1"] = str(num)
                new_rows.append(new_row)
        else:
            new_rows.append(row)
    return pd.DataFrame(new_rows)

class Command(BaseCommand):
    help = "Download PDFs for each borough and extract tables to individual CSV files in static/data (expanding building ranges)."

    def handle(self, *args, **options):
        # Define the target folder relative to your project's BASE_DIR.
        data_dir = os.path.join(settings.BASE_DIR, 'static', 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            self.stdout.write(self.style.SUCCESS(f"Created directory: {data_dir}"))
        else:
            self.stdout.write(f"Using existing directory: {data_dir}")

        # Dictionary mapping borough names to their PDF URLs.
        pdf_urls = {
            'Manhattan': 'https://rentguidelinesboard.cityofnewyork.us/wp-content/uploads/2024/11/2023-DHCR-Bldg-File-Manhattan.pdf',
            'Brooklyn': 'https://rentguidelinesboard.cityofnewyork.us/wp-content/uploads/2024/11/2023-DHCR-Bldg-File-Brooklyn.pdf',
            'Bronx': 'https://rentguidelinesboard.cityofnewyork.us/wp-content/uploads/2024/11/2023-DHCR-Bldg-File-Bronx.pdf',
            'Queens': 'https://rentguidelinesboard.cityofnewyork.us/wp-content/uploads/2024/11/2023-DHCR-Bldg-File-Queens.pdf',
            'Staten_Island': 'https://rentguidelinesboard.cityofnewyork.us/wp-content/uploads/2024/11/2023-DHCR-Bldg-File-Staten-Island.pdf'
        }

        # Loop over each borough.
        for borough, url in pdf_urls.items():
            self.stdout.write(f"Processing {borough} PDF from {url}")
            pdf_filename = f"{borough}.pdf"
            pdf_path = os.path.join(data_dir, pdf_filename)

            # Remove any existing PDF file before downloading.
            if os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                    self.stdout.write(self.style.SUCCESS(f"Removed existing file: {pdf_path}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error removing existing PDF file {pdf_path}: {e}"))
                    continue

            # Download the PDF.
            try:
                response = requests.get(url)
                response.raise_for_status()
                with open(pdf_path, 'wb') as f:
                    f.write(response.content)
                self.stdout.write(self.style.SUCCESS(f"Downloaded {borough} PDF to {pdf_path}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error downloading {borough}: {e}"))
                continue

            # Extract tables using Tabula.
            try:
                # Adjust parameters as needed. Here we assume pages='all' and multiple_tables=True.
                dfs = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
                if not dfs:
                    self.stdout.write(self.style.WARNING(f"No tables found in {pdf_filename}"))
                    continue
                combined_df = pd.concat(dfs, ignore_index=True)
                
                # Expand rows where BLDGNO1 contains a range (e.g., "303 TO 309").
                expanded_df = expand_building_ranges(combined_df)
                
                csv_filename = f"{borough}.csv"
                csv_path = os.path.join(data_dir, csv_filename)
                # Remove any existing CSV file before writing.
                if os.path.exists(csv_path):
                    os.remove(csv_path)
                    self.stdout.write(self.style.SUCCESS(f"Removed existing file: {csv_path}"))
                expanded_df.to_csv(csv_path, index=False)
                self.stdout.write(self.style.SUCCESS(f"Extracted CSV for {borough} at {csv_path}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error extracting tables from {borough} PDF: {e}"))
                continue
