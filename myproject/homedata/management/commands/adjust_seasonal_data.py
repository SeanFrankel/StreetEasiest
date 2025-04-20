import os
import pandas as pd
import statsmodels.api as sm
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import numpy as np
from pathlib import Path

class Command(BaseCommand):
    help = 'Applies seasonal adjustment to rental data CSV files.'

    def handle(self, *args, **options):
        data_dir = os.path.join(settings.BASE_DIR, 'myproject', 'homedata', 'data')
        self.stdout.write(f"Using data directory: {data_dir}")

        # List of CSV files to process
        csv_files = [
            "medianAskingRent_All.csv",
            "rentalInventory_All.csv",
            "medianAskingRent_Studio.csv",
            "rentalInventory_Studio.csv",
            "medianAskingRent_OneBd.csv",
            "rentalInventory_OneBd.csv",
            "medianAskingRent_TwoBd.csv",
            "rentalInventory_TwoBd.csv",
            "medianAskingRent_ThreePlusBd.csv",
            "rentalInventory_ThreePlusBd.csv",
        ]

        for csv_file in csv_files:
            input_path = os.path.join(data_dir, csv_file)
            if not os.path.exists(input_path):
                self.stdout.write(self.style.WARNING(f"File not found: {csv_file}. Skipping..."))
                continue

            try:
                # Read the CSV without parsing 'Date' as there's no such column
                df = pd.read_csv(input_path)

                # Assume first three columns are metadata: AreaName, Borough, AreaType
                metadata_cols = ['AreaName', 'Borough', 'AreaType']
                data_cols = df.columns[3:]

                # Extract date information from column headers
                try:
                    # Ensure that the data columns are in 'YYYY-MM' format
                    date_range = pd.to_datetime(data_cols, format='%Y-%m')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error parsing dates from headers in {csv_file}: {e}"))
                    continue

                # Rename data columns to standardized date format if necessary
                df = df.rename(columns=dict(zip(data_cols, date_range.strftime('%Y-%m'))))

                # List of new adjusted column names
                adjusted_cols = [f"{date}_adj" for date in date_range.strftime('%Y-%m')]

                # Initialize adjusted columns with NaN
                for adj_col in adjusted_cols:
                    df[adj_col] = np.nan

                # Process each row independently
                for idx, row in df.iterrows():
                    # Extract the time series data for the row
                    ts = row[date_range.strftime('%Y-%m')].astype(float)

                    # Handle missing or zero data by interpolation or filling
                    ts = ts.replace(0, np.nan).interpolate(method='linear').fillna(method='bfill').fillna(method='ffill')

                    # Check if enough data points are available for seasonal decomposition
                    if ts.isnull().any() or len(ts.dropna()) < 24:  # Require at least 2 years of data
                        self.stdout.write(self.style.WARNING(f"Insufficient data for seasonal adjustment in row {idx} of {csv_file}. Skipping..."))
                        continue

                    # Apply seasonal decomposition
                    try:
                        decomposition = sm.tsa.seasonal_decompose(ts, model='multiplicative', period=12)
                        seasonal = decomposition.seasonal
                        adj = ts / seasonal

                        # Assign adjusted values back to the DataFrame
                        df.loc[idx, adjusted_cols] = adj.values
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error decomposing time series for row {idx} in {csv_file}: {e}"))
                        continue

                # Save the adjusted data
                adjusted_file = csv_file.replace('.csv', '_SeasonallyAdjusted.csv')
                df.to_csv(os.path.join(data_dir, adjusted_file), index=False)
                self.stdout.write(self.style.SUCCESS(f"Seasonally adjusted data saved to {adjusted_file}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing {csv_file}: {e}"))

        self.stdout.write(self.style.SUCCESS("Seasonal adjustment process completed.")) 