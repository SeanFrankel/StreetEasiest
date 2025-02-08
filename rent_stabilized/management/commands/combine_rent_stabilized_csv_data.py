import os
import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Combine individual borough CSV files into a single all_boroughs.csv file in static/data."

    def handle(self, *args, **options):
        # Define the data directory (where the individual CSVs are stored).
        data_dir = os.path.join(settings.BASE_DIR, "static", "data")
        self.stdout.write(f"Using data directory: {data_dir}")

        # List of expected CSV files (one for each borough).
        borough_files = [
            "Manhattan.csv",
            "Brooklyn.csv",
            "Bronx.csv",
            "Queens.csv",
            "Staten_Island.csv",
        ]
        csv_files = []
        for filename in borough_files:
            file_path = os.path.join(data_dir, filename)
            if os.path.exists(file_path):
                csv_files.append(file_path)
                self.stdout.write(self.style.SUCCESS(f"Found {filename}"))
            else:
                self.stdout.write(self.style.WARNING(f"File not found: {filename}"))

        if not csv_files:
            self.stdout.write(self.style.ERROR("No individual CSV files found."))
            return

        # Read each CSV file into a DataFrame.
        try:
            df_list = [pd.read_csv(csv_file) for csv_file in csv_files]
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV files: {e}"))
            return

        # Combine the DataFrames.
        try:
            combined_df = pd.concat(df_list, ignore_index=True)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error combining CSV files: {e}"))
            return

        # Define the path for the final combined CSV.
        final_csv_path = os.path.join(data_dir, "all_boroughs.csv")
        # Remove the existing final CSV file if it exists.
        if os.path.exists(final_csv_path):
            try:
                os.remove(final_csv_path)
                self.stdout.write(self.style.SUCCESS(f"Removed existing file: {final_csv_path}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error removing existing file: {e}"))
                return

        # Save the combined DataFrame as CSV.
        try:
            combined_df.to_csv(final_csv_path, index=False)
            self.stdout.write(self.style.SUCCESS(f"Final combined CSV saved at {final_csv_path}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error saving final CSV: {e}"))
