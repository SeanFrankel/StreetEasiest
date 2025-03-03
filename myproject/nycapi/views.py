import json
import logging
import os
import re
import requests
from datetime import datetime, timedelta
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import urllib.parse

logger = logging.getLogger(__name__)

# Hardcoded API credentials from NYC Developer Portal
NYC_APP_ID = '04304356a107449aa1656f9e6be87533'  # Geoclient User Primary Key
NYC_APP_KEY = 'f35ede6b69904a1fb4f9180c0408a3fb'  # Geoclient User Secondary Key
NYC_311_API_KEY = os.environ.get('NYC_311_API_KEY', getattr(settings, '311_API_KEY', 'your_311_api_key'))

def get_borough_from_zip(zip_code):
    borough_map = {
        'MANHATTAN': list(range(10001, 10283)) + [10292],
        'BRONX': list(range(10451, 10476)),
        'BROOKLYN': list(range(11201, 11257)) + [11351],
        'QUEENS': list(range(11004, 11110)) + list(range(11351, 11698)),
        'STATEN ISLAND': list(range(10301, 10315))
    }
    try:
        zip_num = int(zip_code)
        for borough, zip_list in borough_map.items():
            if zip_num in zip_list:
                return borough.title()
    except ValueError:
        return None

def get_building_id_from_nyc_api(address, zip_code, api_key=None):
    """
    Get the building ID (BIN) from the NYC GeoClient API.
    Returns the BIN if found, None otherwise.
    """
    # Use hardcoded API key if none provided
    if not api_key:
        api_key = NYC_APP_KEY

    # First, try to parse the address
    address_parts = address.strip().split()
    
    if len(address_parts) < 2:
        logger.error(f"Invalid address format: {address}")
        return None
    
    # Extract house number and street
    house_number = address_parts[0]
    street = ' '.join(address_parts[1:])
    
    # Get borough code from ZIP
    borough = get_borough_from_zip(zip_code)
    if not borough:
        logger.error(f"Could not determine borough for ZIP: {zip_code}")
        return None
    
    # Borough codes for Geoclient API
    borough_codes = {
        "Manhattan": "1",
        "Bronx": "2",
        "Brooklyn": "3",
        "Queens": "4",
        "Staten Island": "5"
    }
    
    borough_code = borough_codes.get(borough)
    if not borough_code:
        logger.error(f"Invalid borough: {borough}")
        return None
    
    try:
        # Prepare API URL for Geoclient
        geoclient_url = f"https://api.nyc.gov/geo/geoclient/v2/address?houseNumber={urllib.parse.quote(house_number)}&street={urllib.parse.quote(street)}&borough={urllib.parse.quote(borough)}&zip={urllib.parse.quote(zip_code)}"
        
        headers = {
            "Ocp-Apim-Subscription-Key": api_key,
            "X-App-ID": NYC_APP_ID
        }
        
        response = requests.get(geoclient_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if 'address' in data and 'buildingIdentificationNumber' in data['address']:
                return data['address']['buildingIdentificationNumber']
            else:
                logger.error(f"BIN not found in Geoclient response: {data}")
                return None
        else:
            logger.error(f"Geoclient API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error retrieving building ID: {str(e)}")
        return None

def get_hpd_data(building_id):
    """
    Fetch Housing Preservation and Development (HPD) data for a specific building ID.
    Returns a list of violations for the building.
    """
    if not building_id:
        logger.error("No building ID provided")
        return []
    
    try:
        # According to NYC documentation, the correct endpoint format is:
        hpd_url = f"https://data.cityofnewyork.us/resource/wvxf-dwi5.json"
        
        # Query parameters - filter by building ID (BIN)
        params = {
            "$where": f"bin='{building_id}'",
            "$order": "inspectiondate DESC",
            "$limit": 100
        }
        
        response = requests.get(hpd_url, params=params)
        
        if response.status_code == 200:
            violations_data = response.json()
            
            # Process the response data
            violations = []
            
            for violation in violations_data:
                violations.append({
                    "violation_number": violation.get("violationid"),
                    "class": violation.get("class"),
                    "order": violation.get("ordernumber"),
                    "apartment": violation.get("apartment"),
                    "story": violation.get("story"),
                    "date": violation.get("inspectiondate"),
                    "description": violation.get("novdescription")
                })
            
            # Sort violations by date (most recent first)
            violations.sort(key=lambda x: x.get("date", ""), reverse=True)
            
            return violations
        else:
            logger.error(f"HPD API error: {response.status_code} - {response.text}")
            
            # If this endpoint fails, try alternate NYC Open Data HPD endpoint
            alternate_url = "https://data.cityofnewyork.us/resource/b2iz-pps8.json"
            
            params = {
                "$where": f"buildingid='{building_id}'",
                "$order": "inspectiondate DESC",
                "$limit": 100
            }
            
            alt_response = requests.get(alternate_url, params=params)
            
            if alt_response.status_code == 200:
                alt_violations_data = alt_response.json()
                
                alt_violations = []
                for violation in alt_violations_data:
                    alt_violations.append({
                        "violation_number": violation.get("violationid") or violation.get("novid"),
                        "class": violation.get("class") or violation.get("novclass"),
                        "order": violation.get("ordernumber") or violation.get("novorder"),
                        "apartment": violation.get("apartment") or violation.get("apt"),
                        "story": violation.get("story") or "",
                        "date": violation.get("inspectiondate") or violation.get("novissuedate"),
                        "description": violation.get("novdescription") or violation.get("description")
                    })
                
                alt_violations.sort(key=lambda x: x.get("date", ""), reverse=True)
                return alt_violations
            else:
                logger.error(f"Alternate HPD API error: {alt_response.status_code} - {alt_response.text}")
                return []
            
    except Exception as e:
        logger.error(f"Error fetching HPD data: {str(e)}")
        return []

def get_311_complaints(address, zip_code, building_id=None):
    """
    Fetch 311 complaints related to a specific address/building.
    Returns a list of recent complaints for that location.
    """
    if not address or not zip_code:
        logger.error("Address or ZIP code missing")
        return []
    
    try:
        # Try multiple approaches to find complaints
        
        # 1. First approach - direct query with ZIP and address number
        complaints = query_311_by_address(address, zip_code)
        if complaints:
            logger.info(f"Found {len(complaints)} complaints via address query")
            return complaints
            
        # 2. Second approach - broader query with just ZIP code
        complaints = query_311_by_zip(zip_code)
        if complaints:
            logger.info(f"Found {len(complaints)} complaints via ZIP query")
            return complaints
            
        # 3. Third approach - try the NYC 311 service request endpoint
        complaints = query_311_service_requests(zip_code)
        if complaints:
            logger.info(f"Found {len(complaints)} complaints via service requests query")
            return complaints
        
        logger.warning(f"No 311 complaints found for {address}, {zip_code} using any method")
        return []
            
    except Exception as e:
        logger.error(f"Error fetching 311 complaints: {str(e)}", exc_info=True)
        return []
        
def query_311_by_address(address, zip_code):
    """Query 311 complaints by address"""
    # Extract address components
    address_parts = address.strip().split()
    if not address_parts:
        return []
        
    street_number = address_parts[0]
    
    # The 311 endpoint
    url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
    
    # Query by incident address starting with the number and ZIP
    params = {
        "incident_zip": zip_code,
        "$where": f"starts_with(incident_address, '{street_number}')",
        "$order": "created_date DESC",
        "$limit": 100
    }
    
    logger.info(f"Querying 311 by address with params: {params}")
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        complaints_data = response.json()
        logger.info(f"Received {len(complaints_data)} complaints for address query")
        
        return process_complaint_results(complaints_data)
    else:
        logger.error(f"311 address query failed: {response.status_code} - {response.text}")
        return []

def query_311_by_zip(zip_code):
    """Query 311 complaints by ZIP code only and filter to housing types"""
    url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
    
    # Housing-related complaint types
    housing_categories = [
        'HEAT/HOT WATER', 'PLUMBING', 'PAINT/PLASTER', 'WATER LEAK', 
        'DOOR/WINDOW', 'ELECTRIC', 'ELEVATOR', 'BUILDING/USE', 
        'GENERAL CONSTRUCTION', 'LEAD'
    ]
    
    # Format the query for complaint types
    complaint_type_query = " OR ".join([f"complaint_type='{category}'" for category in housing_categories])
    
    params = {
        "incident_zip": zip_code,
        "$where": f"({complaint_type_query})",
        "$order": "created_date DESC",
        "$limit": 100
    }
    
    logger.info(f"Querying 311 by ZIP with params: {params}")
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        complaints_data = response.json()
        logger.info(f"Received {len(complaints_data)} complaints for ZIP query")
        
        return process_complaint_results(complaints_data)
    else:
        logger.error(f"311 ZIP query failed: {response.status_code} - {response.text}")
        return []

def query_311_service_requests(zip_code):
    """Query the 311 service requests endpoint"""
    url = "https://data.cityofnewyork.us/resource/fhrw-4uyv.json"
    
    params = {
        "incident_zip": zip_code,
        "$order": "created_date DESC",
        "$limit": 100
    }
    
    logger.info(f"Querying 311 service requests with params: {params}")
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        complaints_data = response.json()
        logger.info(f"Received {len(complaints_data)} service requests")
        
        return process_complaint_results(complaints_data)
    else:
        logger.error(f"311 service requests query failed: {response.status_code} - {response.text}")
        return []
        
def process_complaint_results(data):
    """Process 311 complaint results into a standard format"""
    complaints = []
    for complaint in data:
        complaints.append({
            "unique_key": complaint.get("unique_key"),
            "complaint_type": complaint.get("complaint_type"),
            "status": complaint.get("status"),
            "created_date": complaint.get("created_date"),
            "closed_date": complaint.get("closed_date", ""),
            "description": complaint.get("descriptor", "")
        })
    
    # Sort by date (most recent first)
    complaints.sort(key=lambda x: x.get("created_date", ""), reverse=True)
    
    # Limit to 50 results
    return complaints[:50]

def building_lookup_view(request):
    """
    View to handle the HPD lookup form and API requests.
    This can be called via AJAX or direct page load.
    """
    if request.method == "GET" and "address" in request.GET and "zip_code" in request.GET:
        address = request.GET.get("address")
        zip_code = request.GET.get("zip_code")
        
        # Check if this is an AJAX request
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        
        if is_ajax:
            try:
                # Step 1: Get the building ID using the Geoclient API
                logger.info(f"Fetching building ID for {address}, {zip_code}")
                building_id = get_building_id_from_nyc_api(address, zip_code)
                
                if not building_id:
                    return JsonResponse({
                        "success": False, 
                        "error": "Could not find a matching building. Please verify the address and ZIP code."
                    })
                
                logger.info(f"Building ID found: {building_id}")
                
                # Step 2: Get HPD violations using the building ID
                logger.info(f"Fetching HPD violations for building ID {building_id}")
                hpd_violations = get_hpd_data(building_id)
                logger.info(f"Found {len(hpd_violations)} HPD violations")
                
                # Step 3: Get 311 complaints for the address
                logger.info(f"Fetching 311 complaints for {address}, {zip_code}")
                complaints_311 = get_311_complaints(address, zip_code, building_id)
                logger.info(f"Found {len(complaints_311)} 311 complaints")
                
                # Step 4: Compile all data for response
                borough = get_borough_from_zip(zip_code) or "N/A"
                
                data = {
                    "metadata": {
                        "address": address,
                        "zip_code": zip_code,
                        "borough": borough,
                        "building_id": building_id,
                        "data_source": "NYC Open Data APIs"
                    },
                    "violations": hpd_violations,
                    "complaints": [],  # Placeholder for additional HPD complaints if needed
                    "complaints_311": complaints_311,
                }
                
                return JsonResponse({"success": True, "data": data})
                
            except Exception as e:
                logger.error(f"Error in building lookup: {str(e)}", exc_info=True)
                return JsonResponse({
                    "success": False, 
                    "error": f"An error occurred while retrieving data: {str(e)}"
                })
        else:
            # Direct page load with query parameters
            return render(request, "nycapi/hpd_lookup_page.html")
    else:
        # Just load the form page
        return render(request, "nycapi/hpd_lookup_page.html")
