import os
from django.http import JsonResponse
from django.conf import settings
import logging
from pathlib import Path
from typing import Dict, Any
from .data_processor import RentalDataProcessor, DataProcessingError

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

def rental_data_json(request):
    """API endpoint for rental trend data."""
    try:
        # Extract and validate parameters
        params = {
            'area': request.GET.get('area'),
            'bedrooms': request.GET.get('bedrooms', 'All'),
            'data_type': request.GET.get('data', 'median'),
            'seasonal': request.GET.get('seasonal', 'false').lower() == 'true'
        }
        
        validate_parameters(params)
        
        # Construct file path
        filename = (
            f"{'rentalInventory' if params['data_type'] == 'inventory' else 'medianAskingRent'}"
            f"_{params['bedrooms']}_SeasonallyAdjusted.csv"
        )
        file_path = Path(settings.BASE_DIR) / 'static' / 'data' / filename
        
        # Process data
        processor = RentalDataProcessor(file_path)
        result = processor.process_data(params['area'], params['seasonal'])
        
        # Convert result to JSON-serializable format
        serialized_result = {
            area: data.to_dict() 
            for area, data in result.items()
        }
        
        return JsonResponse(serialized_result)

    except InvalidParameterError as e:
        logger.warning(f"Invalid parameters: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)
    except DataProcessingError as e:
        logger.error(f"Data processing error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)