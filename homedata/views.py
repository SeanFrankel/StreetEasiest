import csv
import os
from django.http import JsonResponse
from django.conf import settings

def rental_data_json(request):
    """
    Returns rental trend data in JSON format.
    Accepts optional GET parameters:
      - area: (if provided) only include data for the specified area.
      - data: which dataset to return. Either 'median' (default) or 'inventory'.
      - bedrooms: which bedroom type to use. Options are 'All' (default), 'Studio', 'OneBd', 'TwoBd', 'ThreePlusBd'.
    """
    area = request.GET.get('area')
    bedrooms = request.GET.get('bedrooms', 'All')
    data_type = request.GET.get('data', 'median')

    # Choose the file name based on data type and bedroom type.
    if data_type == 'inventory':
        filename = f"rentalInventory_{bedrooms}.csv"
    else:
        # Default to median asking rent.
        filename = f"medianAskingRent_{bedrooms}.csv"
        
    file_path = os.path.join(settings.BASE_DIR, 'static', 'data', filename)
    result = {}

    try:
        with open(file_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # If an 'area' GET parameter was provided, filter out rows that do not match.
                if area and row.get('areaName') != area:
                    continue

                # Build a dictionary of monthly data. We assume the keys like "2010-01", "2010-02", etc.
                monthly_data = {}
                for key, value in row.items():
                    # We assume any key with exactly one '-' is a monthly column.
                    if '-' in key and key.count('-') == 1:
                        try:
                            monthly_data[key] = float(value) if value else None
                        except ValueError:
                            monthly_data[key] = None

                result[row.get('areaName', 'Unknown')] = {
                    'Borough': row.get('Borough', ''),
                    'areaType': row.get('areaType', ''),
                    'monthly': monthly_data
                }
    except FileNotFoundError:
        return JsonResponse({"error": f"File {filename} not found."}, status=404)
    
    return JsonResponse(result)
