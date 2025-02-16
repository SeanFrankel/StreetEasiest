import csv
import os
from django.http import JsonResponse
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def rental_data_json(request):
    """
    Returns rental trend data in JSON format.
    Accepts optional GET parameters:
      - area: (if provided) only include data for the specified area.
      - data: which dataset to return. Either 'median' (default) or 'inventory'.
      - bedrooms: which bedroom type to use. Options are 'All' (default), 'Studio', 'OneBd', 'TwoBd', 'ThreePlusBd'.
      - seasonal: 'true' to include both raw and seasonally adjusted data.
    """
    area = request.GET.get('area')
    bedrooms = request.GET.get('bedrooms', 'All')
    data_type = request.GET.get('data', 'median')
    seasonal = request.GET.get('seasonal', 'false').lower() == 'true'

    # Determine filenames based on data type and bedroom type
    if data_type == 'inventory':
        filename = f"rentalInventory_{bedrooms}_SeasonallyAdjusted.csv"
    else:
        filename = f"medianAskingRent_{bedrooms}_SeasonallyAdjusted.csv"

    data_dir = os.path.join(settings.BASE_DIR, 'static', 'data')

    def read_csv(file_path):
        try:
            with open(file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                data = list(reader)
                if not data:
                    logger.warning(f"No data found in file: {file_path}")
                else:
                    logger.info(f"Headers in {file_path}: {reader.fieldnames}")
                return data
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return []

    try:
        # Load data
        file_path = os.path.join(data_dir, filename)
        data = read_csv(file_path)

        result = {}

        for row in data:
            if 'areaName' not in row:
                logger.error(f"Missing 'areaName' in row: {row}")
                continue

            if area and row.get('areaName') != area:
                continue

            area_name = row.get('areaName', 'Unknown')
            borough = row.get('Borough', '')
            area_type = row.get('areaType', '')

            # Initialize monthly data
            monthly_raw = {}
            monthly_adjusted = {}

            # Process each column in the row
            for key, value in row.items():
                if key in ['areaName', 'Borough', 'areaType']:
                    continue
                
                try:
                    # Raw data columns are just dates (YYYY-MM)
                    # Adjusted data columns end with '_adj'
                    if key.endswith('_adj'):
                        base_date = key[:-4]  # Remove '_adj' suffix
                        if value and value.strip():  # Check if value exists and isn't just whitespace
                            monthly_adjusted[base_date] = float(value)
                    else:
                        if value and value.strip():  # Check if value exists and isn't just whitespace
                            monthly_raw[key] = float(value)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error converting value '{value}' for {key} to float: {e}")
                    if key.endswith('_adj'):
                        monthly_adjusted[key[:-4]] = None
                    else:
                        monthly_raw[key] = None

            # Structure the response based on whether seasonal data was requested
            result[area_name] = {
                'Borough': borough,
                'AreaType': area_type,
                'monthly': {
                    'raw': monthly_raw,
                    'adjusted': monthly_adjusted if seasonal else None
                }
            }

        if not result:
            logger.warning(f"No data found for area: {area}")
            return JsonResponse({'error': 'No data found'}, status=404)

        logger.info(f"Successfully processed data for {len(result)} areas")
        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
