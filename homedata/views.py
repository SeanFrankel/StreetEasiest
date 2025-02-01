import csv
import os
from django.http import JsonResponse
from django.conf import settings

def rental_data_json(request):
    """
    Returns rental trend data in JSON format.
    If an 'area' GET parameter is provided, returns data for that area;
    otherwise returns data for all areas.
    """
    area = request.GET.get('area')
    file_path = os.path.join(settings.BASE_DIR, 'static', 'data', 'medianAskingRent_latest.csv')
    result = {}
    
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if area and row['areaName'] != area:
                continue  # skip rows that don't match the selected area
            # Build a dictionary of monthly data
            monthly_data = {}
            for key, value in row.items():
                # Assume keys like "2010-01", "2010-02", etc. are your monthly data columns.
                if '-' in key and key.count('-') == 1:
                    try:
                        monthly_data[key] = float(value) if value else None
                    except ValueError:
                        monthly_data[key] = None
            result[row['areaName']] = {
                'Borough': row['Borough'],
                'areaType': row['areaType'],
                'monthly': monthly_data
            }
    return JsonResponse(result)
