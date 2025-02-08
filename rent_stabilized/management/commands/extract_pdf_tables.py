import os
import pandas as pd
from tabula import read_pdf
from django.core.management.base import BaseCommand
from django.conf import settings
# If needed, uncomment and adjust the following line to start the JVM:
# import jpype
# jpype.startJVM("C:/Program Files/Java/jdk1.8.0_391/jre/bin/server/jvm.dll")

class Command(BaseCommand):
    help = "Extract tables from all saved PDFs in myproject/static/data and save them as CSV files."

    def extract_tables_from_pdf(self, pdf_path, output_csv_path):
        """
        Extract tables from the given PDF using Tabula, then concatenate all
        found tables into a single DataFrame and save as a CSV file.
        """
        lattice = False
        guess = True

        try:
            # Read all tables from the PDF (you might need to adjust parameters)
            dfs = read_pdf(pdf_path, pages='all', multiple_tables=True, guess=guess, lattice=lattice)
            if not dfs:
                self.stdout.write(self.style.WARNING(f"No tables found in {pdf_path}."))
                return
            # Concatenate all tables into one DataFrame
            df = pd.concat(dfs, ignore_index=True)
            df.to_csv(output_csv_path, index=False)
            self.stdout.write(self.style.SUCCESS(f"Extracted tables saved to {output_csv_path}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error processing {pdf_path}: {e}"))

    def handle(self, *args, **options):
        # Define the folder where PDFs are stored.
        # This assumes that your project's BASE_DIR (the directory where manage.py lives)
        # contains a folder 'static/data'
        data_dir = os.path.join(settings.BASE_DIR, 'static', 'data')

        if not os.path.exists(data_dir):
            self.stdout.write(self.style.ERROR(f"Data directory does not exist: {data_dir}"))
            return

        # Find all PDF files in the data directory.
        pdf_files = [f for f in os.listdir(data_dir) if f.lower().endswith('.pdf')]
        if not pdf_files:
            self.stdout.write(self.style.WARNING("No PDF files found in the data directory."))
            return

        # Process each PDF file.
        for pdf_file in pdf_files:
            pdf_path = os.path.join(data_dir, pdf_file)
            # Define the CSV output file name (e.g., Manhattan.pdf -> Manhattan.csv)
            csv_file_name = os.path.splitext(pdf_file)[0] + '.csv'
            csv_path = os.path.join(data_dir, csv_file_name)
            self.stdout.write(f"Processing {pdf_file}...")
            self.extract_tables_from_pdf(pdf_path, csv_path)
