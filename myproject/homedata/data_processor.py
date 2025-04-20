from dataclasses import dataclass
from typing import Dict, Optional, List, Union
import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class DataProcessingError(Exception):
    """Custom exception for data processing errors"""
    pass

@dataclass
class MonthlyData:
    raw: Dict[str, float]
    adjusted: Optional[Dict[str, float]] = None

    def validate(self):
        """Validate monthly data structure"""
        if not self.raw:
            raise DataProcessingError("Raw data cannot be empty")
        if self.adjusted is not None and not self.adjusted:
            raise DataProcessingError("Adjusted data cannot be empty when provided")

    def to_dict(self) -> Dict:
        result = {'raw': self.raw}
        if self.adjusted is not None:
            result['adjusted'] = self.adjusted
        return result

@dataclass
class RentalData:
    area_name: str
    borough: str
    area_type: str
    monthly: MonthlyData

    def validate(self):
        """Validate rental data structure"""
        if not self.area_name:
            raise DataProcessingError("Area name is required")
        self.monthly.validate()

    def to_dict(self) -> Dict:
        return {
            'area_name': self.area_name,
            'borough': self.borough,
            'area_type': self.area_type,
            'monthly': self.monthly.to_dict()
        }
    
class RentalDataProcessor:
    REQUIRED_FIELDS = {'areaName', 'Borough', 'areaType'}
    
    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise DataProcessingError(f"File not found: {file_path}")

    def process_data(self, area: Optional[str] = None, include_seasonal: bool = False) -> Dict[str, RentalData]:
        try:
            data = self._read_csv()
            processed_data = self._process_rows(data, area, include_seasonal)
            self._validate_processed_data(processed_data)
            return processed_data
        except Exception as e:
            logger.error(f"Error processing data: {str(e)}")
            raise DataProcessingError(f"Failed to process data: {str(e)}")

    def _read_csv(self) -> List[Dict]:
        try:
            with self.file_path.open(newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                if not set(reader.fieldnames or []).issuperset(self.REQUIRED_FIELDS):
                    raise DataProcessingError(f"Missing required fields: {self.REQUIRED_FIELDS}")
                return list(reader)
        except csv.Error as e:
            raise DataProcessingError(f"CSV reading error: {str(e)}")

    def _process_rows(self, data: List[Dict], area: Optional[str], include_seasonal: bool) -> Dict[str, RentalData]:
        result = {}
        for row in data:
            try:
                if area and row['areaName'] != area:
                    continue
                
                monthly_data = self._extract_monthly_data(row, include_seasonal)
                rental_data = RentalData(
                    area_name=row['areaName'],
                    borough=row['Borough'],
                    area_type=row['areaType'],
                    monthly=monthly_data
                )
                rental_data.validate()
                result[row['areaName']] = rental_data
            except (ValueError, KeyError) as e:
                logger.warning(f"Skipping invalid row: {str(e)}")
                continue
        return result

    def _extract_monthly_data(self, row: Dict, include_seasonal: bool) -> MonthlyData:
        """Extract and validate monthly data from a row."""
        raw_data = {}
        adjusted_data = {} if include_seasonal else None

        for key, value in row.items():
            if key in self.REQUIRED_FIELDS:
                continue

            try:
                # Skip empty values
                if not value or str(value).strip() == '':
                    continue

                # Handle adjusted data
                if key.endswith('_adj'):
                    if include_seasonal and adjusted_data is not None:
                        base_date = key[:-4]
                        try:
                            adjusted_data[base_date] = float(value)
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid adjusted value '{value}' for {key}")
                            continue
                # Handle raw data
                else:
                    try:
                        raw_data[key] = float(value)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid raw value '{value}' for {key}")
                        continue

            except Exception as e:
                logger.warning(f"Error processing value '{value}' for {key}: {str(e)}")
                continue

        # Ensure we have at least some raw data
        if not raw_data:
            raise DataProcessingError("No valid raw data found in row")

        return MonthlyData(raw=raw_data, adjusted=adjusted_data)

    def _validate_processed_data(self, data: Dict[str, RentalData]) -> None:
        if not data:
            raise DataProcessingError("No valid data processed")
        for rental_data in data.values():
            rental_data.validate() 