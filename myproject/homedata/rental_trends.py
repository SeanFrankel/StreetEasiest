import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
import logging
from .data_processor import DataProcessingError

logger = logging.getLogger(__name__)

class RentalTrendsProcessor:
    """Process rental trends data from CSV files"""
    
    def __init__(self, file_path: Path):
        """Initialize with the path to the CSV file"""
        self.file_path = file_path
        self.data = None
        self._load_data()
    
    def _load_data(self) -> None:
        """Load and validate the CSV data"""
        try:
            self.data = pd.read_csv(self.file_path)
            required_columns = ['areaName', 'Borough', 'areaType']
            if not all(col in self.data.columns for col in required_columns):
                raise DataProcessingError(f"Missing required columns: {required_columns}")
        except Exception as e:
            raise DataProcessingError(f"Error loading data: {str(e)}")
    
    def get_latest_trends(self, area: str) -> Dict[str, Any]:
        """Get the latest rental trends for a specific area"""
        try:
            if area not in self.data['areaName'].unique():
                raise DataProcessingError(f"Area not found: {area}")
            
            area_data = self.data[self.data['areaName'] == area].iloc[0]
            
            # Get the most recent year's data
            year_columns = [col for col in self.data.columns if col.startswith(('20', '19'))]
            latest_year = max(year_columns)
            
            # Calculate year-over-year change
            previous_year = str(int(latest_year) - 1)
            if previous_year in year_columns:
                yoy_change = ((float(area_data[latest_year]) - float(area_data[previous_year])) 
                            / float(area_data[previous_year]) * 100)
            else:
                yoy_change = None
            
            return {
                'areaName': area,
                'borough': area_data['Borough'],
                'areaType': area_data['areaType'],
                'latestValue': float(area_data[latest_year]),
                'yearOverYearChange': yoy_change,
                'latestYear': latest_year
            }
        except Exception as e:
            raise DataProcessingError(f"Error processing trends: {str(e)}")
    
    def get_comparable_areas(self, area: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get comparable areas based on latest rental values"""
        try:
            if area not in self.data['areaName'].unique():
                raise DataProcessingError(f"Area not found: {area}")
            
            # Get the most recent year's data
            year_columns = [col for col in self.data.columns if col.startswith(('20', '19'))]
            latest_year = max(year_columns)
            
            # Sort areas by their latest values
            sorted_areas = self.data.sort_values(by=latest_year)
            
            # Find the index of the target area
            area_index = sorted_areas[sorted_areas['areaName'] == area].index[0]
            
            # Get comparable areas (similar price range)
            start_idx = max(0, area_index - limit)
            end_idx = min(len(sorted_areas), area_index + limit + 1)
            
            comparable_areas = []
            for idx in range(start_idx, end_idx):
                if idx != area_index:  # Skip the target area
                    area_data = sorted_areas.iloc[idx]
                    comparable_areas.append({
                        'areaName': area_data['areaName'],
                        'borough': area_data['Borough'],
                        'areaType': area_data['areaType'],
                        'latestValue': float(area_data[latest_year])
                    })
            
            return comparable_areas
        except Exception as e:
            raise DataProcessingError(f"Error finding comparable areas: {str(e)}") 