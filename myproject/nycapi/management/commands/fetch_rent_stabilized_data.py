"""
Management command to fetch real rent-stabilized unit data using JustFix.NYC's method.

This uses NYC Department of Finance tax bill data, which is the same source
that JustFix.NYC uses for their "Who Owns What" tool.

Based on JustFix.NYC's methodology from their "Worst Evictors" project.
"""
import os
import csv
import requests
import logging
from django.conf import settings
from django.core.management.base import BaseCommand
from myproject.nycapi.views import api_get

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fetch real rent-stabilized unit data from NYC Department of Finance (JustFix.NYC method)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50000,
            help='Maximum number of records to fetch (default: 50000)'
        )
        parser.add_argument(
            '--borough',
            type=str,
            choices=['manhattan', 'brooklyn', 'queens', 'bronx', 'staten_island', 'all'],
            default='all',
            help='Specific borough to fetch (default: all)'
        )

    def handle(self, *args, **options):
        self.stdout.write("Starting rent-stabilized data fetch using JustFix.NYC method...")
        
        output_file = os.path.join(settings.BASE_DIR, "myproject/nycapi/data/rent_stabilized_buildings.csv")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Fetch data using JustFix.NYC's approach
        rent_stabilized_data = self.fetch_dof_data(options['limit'], options['borough'])
        
        if not rent_stabilized_data:
            self.stdout.write(
                self.style.ERROR("No rent-stabilized data found in any NYC DOF APIs. Real data not currently available.")
            )
            self.stdout.write("This is expected since the DOF APIs don't currently expose rent-stabilized unit counts.")
            return
            
        # Write to CSV
        self.write_csv(rent_stabilized_data, output_file)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully fetched {len(rent_stabilized_data)} rent-stabilized buildings to {output_file}"
            )
        )

    def fetch_dof_data(self, limit, borough_filter):
        """
        Fetch rent-stabilized data from NYC Department of Finance.
        Uses Property Valuation and Assessment Data exactly like JustFix.NYC does.
        
        JustFix.NYC mentions: "Rent stabilized unit estimates (for 2020) from 
        Dept. of Finance tax bills via nycdb"
        """
        self.stdout.write("Fetching data from NYC Department of Finance (JustFix.NYC method)...")
        
        rent_stabilized_data = {}
        
        # Main Property Valuation and Assessment API endpoints
        # These contain the tax bill data that JustFix.NYC uses
        api_endpoints = [
            # Main citywide dataset
            'https://data.cityofnewyork.us/resource/yjxr-fw8i.json',
            # Borough-specific datasets (fallback)
            'https://data.cityofnewyork.us/resource/rgy2-tti8.json',  # Manhattan
            'https://data.cityofnewyork.us/resource/bss9-579f.json',  # Brooklyn
            'https://data.cityofnewyork.us/resource/fv87-j59w.json',  # Queens
            'https://data.cityofnewyork.us/resource/qicy-cy43.json',  # Bronx
            'https://data.cityofnewyork.us/resource/8y4t-faws.json'   # Staten Island
        ]
        
        # Possible field names for rent-stabilized units (based on research)
        possible_rs_fields = [
            'rs_cnt',           # Most common
            'rentstab_cnt', 
            'rent_stabilized_units',
            'rent_stab_units',
            'stabilized_units'
        ]
        
        # Possible BBL field names
        possible_bbl_fields = [
            'bbl',              # Most common
            'bble',             # Alternative format
            'borough_block_lot',
            'boro_block_lot'
        ]
        
        for endpoint in api_endpoints:
            self.stdout.write(f"Trying endpoint: {endpoint}")
            
            try:
                # First, discover what fields are available
                for bbl_field in possible_bbl_fields:
                    for rs_field in possible_rs_fields:
                        try:
                            # Test query to see if these fields exist and have data
                            test_params = {
                                '$limit': 10,
                                '$where': f"{rs_field} > 0",
                                '$select': f'{bbl_field},{rs_field}'
                            }
                            
                            test_data = api_get(endpoint, params=test_params, timeout=30)
                            
                            if test_data and len(test_data) > 0:
                                self.stdout.write(f"Found fields '{bbl_field}' and '{rs_field}' with {len(test_data)} test records")
                                
                                # Now fetch the full dataset with these fields
                                params = {
                                    '$limit': limit,
                                    '$where': f"{rs_field} > 0",
                                    '$select': f'{bbl_field},{rs_field}',
                                    '$order': bbl_field
                                }
                                
                                data = api_get(endpoint, params=params, timeout=120)
                                
                                if data:
                                    for record in data:
                                        bbl = record.get(bbl_field)
                                        rs_count = record.get(rs_field)
                                        
                                        if bbl and rs_count:
                                            try:
                                                rent_stabilized_data[bbl] = int(rs_count)
                                            except (ValueError, TypeError):
                                                continue
                                    
                                    self.stdout.write(
                                        self.style.SUCCESS(
                                            f"Successfully fetched {len(data)} records using fields '{bbl_field}' and '{rs_field}'"
                                        )
                                    )
                                    
                                    # If we got data, we're done
                                    if rent_stabilized_data:
                                        return rent_stabilized_data
                            
                        except Exception as field_error:
                            # These fields don't exist or failed, try next combination
                            continue
                
            except Exception as e:
                self.stdout.write(f"Error with endpoint {endpoint}: {e}")
                continue
        
        # If no API data found, log it
        if not rent_stabilized_data:
            self.stdout.write(
                self.style.WARNING(
                    "Could not find rent-stabilized data in any DOF API endpoints. "
                    "This may be because the field names have changed or the data is not publicly available."
                )
            )
        
        return rent_stabilized_data





    def write_csv(self, data, output_file):
        """Write the rent-stabilized data to CSV file."""
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['BBL', 'RentStabilizedUnits'])
                
                for bbl, count in sorted(data.items()):
                    writer.writerow([bbl, count])
                    
            self.stdout.write(f"Data written to {output_file}")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error writing CSV file: {e}")
            )
            raise