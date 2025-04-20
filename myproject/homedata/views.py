import os
from django.http import JsonResponse
from django.conf import settings
import logging
from pathlib import Path
from typing import Dict, Any
from .data_processor import RentalDataProcessor, DataProcessingError
from .rental_trends import RentalTrendsProcessor
from myproject.utils.cache import get_default_cache_control_decorator
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)

class InvalidParameterError(Exception):
    """Custom exception for invalid parameters"""
    pass

def validate_parameters(params: Dict[str, Any]) -> None:
    """Validate request parameters"""
    valid_bedrooms = {'All', 'Studio', 'OneBd', 'TwoBd', 'ThreePlusBd'}
    valid_data_types = {'median', 'inventory'}
    
    if params['bedrooms'] not in valid_bedrooms:
        raise InvalidParameterError(f"Invalid bedroom type: {params['bedrooms']}")
    
    if params['data_type'] not in valid_data_types:
        raise InvalidParameterError(f"Invalid data type: {params['data_type']}")

@require_GET
def rental_data_json(request):
    """Return rental data as JSON"""
    try:
        area = request.GET.get('area')
        bedrooms = request.GET.get('bedrooms', 'All')
        data_type = request.GET.get('data', 'median')
        seasonal = request.GET.get('seasonal', 'false').lower() == 'true'
        
        if not area:
            raise InvalidParameterError("Area parameter is required")
            
        # Map UI bedroom types to file names
        bedroom_map = {
            'All': 'All',
            'Studio': 'Studio',
            'OneBd': 'OneBd',
            'TwoBd': 'TwoBd',
            'ThreePlusBd': 'ThreePlusBd'
        }
        
        # Map UI data types to file names
        data_map = {
            'median': 'medianAskingRent',
            'inventory': 'rentalInventory'
        }
        
        if bedrooms not in bedroom_map:
            raise InvalidParameterError(f"Invalid bedroom type: {bedrooms}")
        if data_type not in data_map:
            raise InvalidParameterError(f"Invalid data type: {data_type}")
            
        # Construct file path based on data type and bedrooms
        file_name = f"{data_map[data_type]}_{bedroom_map[bedrooms]}.csv"
        file_path = Path(settings.BASE_DIR) / 'myproject' / 'homedata' / 'data' / file_name
        
        if not file_path.exists():
            raise DataProcessingError(f"Data file not found: {file_name}")
        
        # If seasonal data is requested, try to use the seasonally adjusted file
        if seasonal:
            seasonal_file = file_path.parent / file_name.replace('.csv', '_SeasonallyAdjusted.csv')
            if seasonal_file.exists():
                file_path = seasonal_file
        
        processor = RentalDataProcessor(file_path)
        result = processor.process_data(area, seasonal)
        
        # Restructure the data to match expected format
        response_data = {}
        for area_name, rental_data in result.items():
            monthly_data = rental_data.monthly.to_dict()
            response_data[area_name] = {
                'monthly': {
                    'raw': monthly_data['raw'],
                    'adjusted': monthly_data['adjusted'] if seasonal else None
                },
                'metadata': {
                    'borough': rental_data.borough,
                    'areaType': rental_data.area_type
                }
            }
        
        return JsonResponse(response_data)
        
    except (InvalidParameterError, DataProcessingError) as e:
        logger.error(f"Data processing error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error processing rental data: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

@get_default_cache_control_decorator()
def rental_trends_json(request):
    """API endpoint for rental trends data."""
    try:
        # Extract and validate parameters
        params = {
            'area': request.GET.get('area'),
        }
        
        # Construct file path
        file_path = Path(settings.BASE_DIR) / 'myproject' / 'homedata' / 'data' / 'medianAskingRent_All.csv'
        
        # Process trends data
        processor = RentalTrendsProcessor(file_path)
        result = processor.get_latest_trends(params['area'])
        
        # Convert result to JSON-serializable format
        serialized_result = {
            area: trend.to_dict() 
            for area, trend in result.items()
        }
        
        return JsonResponse(serialized_result)

    except DataProcessingError as e:
        logger.error(f"Data processing error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500) 