import logging
import time
import json
import os
import re
import traceback
from django.http import JsonResponse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from urllib.parse import urlparse, parse_qs
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import requests
from bs4 import BeautifulSoup

# Configure logging
logger = logging.getLogger(__name__)

def extract_table_data(driver, url, what_to_extract="violations"):
    """Extract data from HPD table directly using the driver, specially handling both tables."""
    logger.info(f"Extracting {what_to_extract} data from {url}")
    
    try:
        # Navigate to the URL
        driver.get(url)
        
        # Wait for the page to load
        WebDriverWait(driver, 30).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "app-root > *")) > 0
        )
        
        # Take a screenshot for debugging
        screenshot_name = f"{what_to_extract}_page.png"
        screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), screenshot_name)
        driver.save_screenshot(screenshot_path)
        logger.info(f"{what_to_extract.capitalize()} page screenshot saved to {screenshot_path}")
        
        # Wait a bit more for dynamic content to load
        time.sleep(2)
        
        # Find all tables
        tables = driver.find_elements(By.CSS_SELECTOR, "mat-table, .mat-table, [role='table'], table")
        
        if not tables:
            logger.warning(f"No tables found on {what_to_extract} page")
            return []
        
        logger.info(f"Found {len(tables)} potential tables")
        
        extracted_data = []
        
        for table_idx, table in enumerate(tables):
            try:
                # Get table headers
                header_elements = table.find_elements(By.CSS_SELECTOR, "th, .mat-header-cell, [role='columnheader']")
                headers = [header.text.strip() for header in header_elements if header.text.strip()]
                
                logger.info(f"Table {table_idx} headers: {headers}")
                
                # If no headers found, this might not be a data table
                if not headers:
                    continue
                
                # Get table rows
                rows = table.find_elements(By.CSS_SELECTOR, "tr:not(:first-child), .mat-row, [role='row']:not([role='columnheader'])")
                
                logger.info(f"Found {len(rows)} rows in table {table_idx}")
                
                # Process each row
                for row in rows:
                    cells = row.find_elements(By.CSS_SELECTOR, "td, .mat-cell, [role='cell']")
                    
                    if cells:
                        # Create a data object for this row
                        row_data = {}
                        
                        # Map cell values to headers
                        for i, cell in enumerate(cells):
                            if i < len(headers):
                                key = headers[i].lower().replace(' ', '_').replace('#', '').strip()
                                value = cell.text.strip()
                                row_data[key] = value
                        
                        # Special handling for violations page
                        if what_to_extract == "violations":
                            # Look for specific columns related to violations
                            for header, value in list(row_data.items()):
                                # Map to standard field names based on what's in the header
                                if re.search(r'viol.*id|nov.*id|id|novid', header):
                                    row_data['violation_number'] = value
                                elif re.search(r'class|severity', header):
                                    row_data['class'] = value
                                    row_data['severity'] = value
                                elif re.search(r'order', header):
                                    row_data['order'] = value
                                elif re.search(r'apt|apartment', header):
                                    row_data['apartment'] = value
                                elif re.search(r'story|floor', header):
                                    row_data['story'] = value
                                elif re.search(r'date', header):
                                    row_data['date'] = value
                                elif re.search(r'desc|description', header):
                                    row_data['description'] = value
                        
                        # Special handling for complaints page
                        elif what_to_extract == "complaints":
                            # Map fields for complaints
                            for header, value in list(row_data.items()):
                                if re.search(r'sr.*num|service', header):
                                    row_data['sr_number'] = value
                                elif re.search(r'date', header):
                                    row_data['date'] = value
                                elif re.search(r'complaint.*id|id', header):
                                    row_data['complaint_id'] = value
                                elif re.search(r'apt|apartment|unit', header):
                                    row_data['apt'] = value
                                elif re.search(r'desc|description|type', header):
                                    row_data['description'] = value
                                elif re.search(r'detail', header):
                                    row_data['complaint_detail'] = value
                                elif re.search(r'loc|location|where', header):
                                    row_data['location'] = value
                                elif re.search(r'status|state', header):
                                    row_data['status'] = value
                        
                        # If this row contains actual data (not just empty cells), add it
                        if any(value for value in row_data.values()):
                            extracted_data.append(row_data)
            
            except Exception as e:
                logger.error(f"Error processing table {table_idx}: {str(e)}")
                logger.error(traceback.format_exc())
        
        logger.info(f"Successfully extracted {len(extracted_data)} {what_to_extract} rows")
        
        # If we didn't find any data, try backup extraction methods
        if not extracted_data:
            logger.warning(f"No data found in tables. Trying alternative extraction methods...")
            
            # For violations, look for cards or list items
            if what_to_extract == "violations":
                items = driver.find_elements(By.CSS_SELECTOR, ".violation-item, mat-card, .card, .item")
                
                for item in items:
                    try:
                        item_text = item.text
                        
                        # Try to extract violation info from text
                        vio_number_match = re.search(r'\b(\d{6,8})\b', item_text)
                        if vio_number_match:
                            vio_data = {'violation_number': vio_number_match.group(1)}
                            
                            # Try to find class
                            class_match = re.search(r'class\s*[:-]?\s*([abc])', item_text, re.IGNORECASE)
                            if class_match:
                                vio_data['class'] = class_match.group(1).upper()
                            
                            # Try to find apartment
                            apt_match = re.search(r'apt\s*[#:]?\s*([0-9a-z]+)', item_text, re.IGNORECASE)
                            if apt_match:
                                vio_data['apartment'] = apt_match.group(1).upper()
                            
                            # Try to find date
                            date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', item_text)
                            if date_match:
                                vio_data['date'] = date_match.group(1)
                            
                            # Try to find description
                            desc_match = re.search(r'(§.*?(?=\n\n|\Z))', item_text, re.DOTALL)
                            if desc_match:
                                vio_data['description'] = desc_match.group(1).strip()
                            
                            extracted_data.append(vio_data)
                    except Exception as e:
                        logger.warning(f"Error processing item: {str(e)}")
        
        return extracted_data
        
    except Exception as e:
        logger.error(f"Error extracting {what_to_extract} data: {str(e)}")
        logger.error(traceback.format_exc())
        return []

def get_building_id(address, zipcode):
    """
    Get building ID (BIN) for a given address and ZIP code using NYC API
    
    Args:
        address: Building address (e.g., "393 Hewes St")
        zipcode: ZIP code (e.g., "11211")
        
    Returns:
        Building ID (BIN) or None if not found
    """
    logger.info(f"Getting building ID for address: {address}, zip: {zipcode}")
    
    # Parse the address into house number and street name
    parts = address.strip().split(' ', 1)
    if len(parts) != 2:
        logger.warning(f"Could not parse address: {address}")
        return None
    
    house_number, street_name = parts[0], parts[1]
    
    # Map zipcode to borough code
    borough = get_borough_from_zip(zipcode)
    borough_code = {"Manhattan": "1", "Bronx": "2", "Brooklyn": "3", "Queens": "4", "Staten Island": "5"}.get(borough, "3")
    
    # NYC API Subscription Key
    API_KEY = getattr(settings, "NYC_API_KEY", "ge4fy3cAUtrn!NM")
    
    # First try the official NYC Geosearch API
    try:
        # NYC Geosearch API endpoint
        api_url = "https://api.nyc.gov/geo/geoclient/v1/address"
        
        # Set up proper headers with subscription key
        headers = {
            "Ocp-Apim-Subscription-Key": API_KEY,
            "Accept": "application/json"
        }
        
        # Parameters for the API call
        params = {
            "houseNumber": house_number,
            "street": street_name,
            "borough": borough,
            "zip": zipcode
        }
        
        logger.info(f"Calling NYC Geosearch API with: {params}")
        response = requests.get(api_url, headers=headers, params=params, timeout=10)
        
        # Check response status
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Geosearch API response: {data}")
            
            # Try to extract BIN from response
            if "address" in data and "buildingIdentificationNumber" in data["address"]:
                bin_number = data["address"]["buildingIdentificationNumber"]
                if bin_number and bin_number != "0000000":
                    logger.info(f"Found building ID from Geosearch API: {bin_number}")
                    return bin_number
            
            # If BIN not found, try to find alternative property identifiers
            if "address" in data and "bbl" in data["address"]:
                bbl = data["address"]["bbl"]
                logger.info(f"Found BBL from Geosearch API: {bbl}")
                # You could use this BBL to try another API call if needed
        
        logger.warning(f"Geosearch API call failed or didn't return a valid BIN. Status: {response.status_code}")
        logger.warning(f"Response content: {response.text[:200]}")
        
    except Exception as e:
        logger.error(f"Error calling NYC Geosearch API: {str(e)}")
    
    # Next try DOB BIS API for building information
    try:
        # DOB BIS API endpoint
        dob_api_url = "https://api.nyc.gov/buildings/buildinginfo/v1/address"
        
        # Set up proper headers with subscription key
        headers = {
            "Ocp-Apim-Subscription-Key": API_KEY,
            "Accept": "application/json"
        }
        
        # Parameters for the API call
        params = {
            "house_number": house_number,
            "street_name": street_name,
            "borough": borough
        }
        
        logger.info(f"Calling DOB BIS API with: {params}")
        response = requests.get(dob_api_url, headers=headers, params=params, timeout=10)
        
        # Check response status
        if response.status_code == 200:
            data = response.json()
            logger.info(f"DOB API response: {data}")
            
            # Try to extract BIN from response
            if isinstance(data, list) and len(data) > 0 and "bin" in data[0]:
                bin_number = data[0]["bin"]
                logger.info(f"Found building ID from DOB API: {bin_number}")
                return bin_number
        
        logger.warning(f"DOB API call failed or didn't return a valid BIN. Status: {response.status_code}")
        
    except Exception as e:
        logger.error(f"Error calling DOB BIS API: {str(e)}")
    
    # As a last resort, try HPD Data portal API
    try:
        # HPD Data portal API endpoint for housing maintenance code violations
        hpd_api_url = "https://data.cityofnewyork.us/resource/wvxf-dwi5.json"
        
        # Build query to find violations for this address
        where_clause = f"housenumber='{house_number}' AND streetname='{street_name}' AND zip='{zipcode}'"
        
        # Parameters for the API call
        params = {
            "$where": where_clause,
            "$limit": 1
        }
        
        logger.info(f"Calling HPD Data API with: {params}")
        response = requests.get(hpd_api_url, params=params, timeout=10)
        
        # Check response status
        if response.status_code == 200:
            data = response.json()
            
            # Try to extract BIN from response
            if isinstance(data, list) and len(data) > 0 and "buildingid" in data[0]:
                bin_number = data[0]["buildingid"]
                logger.info(f"Found building ID from HPD Data API: {bin_number}")
                return bin_number
        
        logger.warning(f"HPD Data API call failed or didn't return a valid BIN. Status: {response.status_code}")
        
    except Exception as e:
        logger.error(f"Error calling HPD Data API: {str(e)}")
    
    # If all APIs fail, fall back to the browser-based method
    logger.info(f"API methods failed. Trying fallback browser method to find building ID for {address}, {zipcode}")
    return get_building_id_from_hpd(address, zipcode)

def get_building_id_from_hpd(address, zipcode):
    """
    Fallback method to get building ID by searching on HPD website directly
    
    Args:
        address: Building address (e.g., "393 Hewes St")
        zipcode: ZIP code (e.g., "11211")
        
    Returns:
        Building ID (BIN) or None if not found
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time
    
    # Initialize a headless browser
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Start the browser
    driver = webdriver.Chrome(options=options)
    try:
        # Go to HPD Online search page
        driver.get("https://hpdonline.nyc.gov/hpdonline/")
        
        # Wait for page to load
        wait = WebDriverWait(driver, 30)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Wait for Angular app to initialize
        time.sleep(5)
        
        # Look for search input fields
        search_fields = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], mat-input, .mat-input-element")
        
        if not search_fields:
            logger.warning("Could not find search input fields on HPD website")
            return None
        
        # Fill in house number
        house_number = address.split(' ')[0]
        if len(search_fields) > 0:
            search_fields[0].clear()
            search_fields[0].send_keys(house_number)
        
        # Fill in street name
        street_name = address[address.find(' ')+1:]
        if len(search_fields) > 1:
            search_fields[1].clear()
            search_fields[1].send_keys(street_name)
        
        # Fill in ZIP code if there's a field for it
        if len(search_fields) > 2:
            search_fields[2].clear()
            search_fields[2].send_keys(zipcode)
        
        # Look for search button
        search_buttons = driver.find_elements(By.CSS_SELECTOR, 
                                             "button[type='submit'], button.search-button, button:contains('Search')")
        
        if not search_buttons:
            # Try finding by text content
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for button in buttons:
                if "search" in button.text.lower():
                    search_buttons = [button]
                    break
        
        if search_buttons:
            search_buttons[0].click()
            
            # Wait for results to load
            time.sleep(5)
            
            # Check if we got redirected to a building page
            current_url = driver.current_url
            logger.info(f"Current URL after search: {current_url}")
            
            # Extract building ID from URL if available
            if "building/" in current_url:
                building_id = current_url.split("building/")[1].split("/")[0]
                if building_id and building_id.isdigit():
                    logger.info(f"Found building ID from HPD search: {building_id}")
                    return building_id
            
            # If we're on a search results page, try to find and click the first result
            result_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='building/'], .search-result a, mat-row")
            
            if result_links:
                # Click the first result
                result_links[0].click()
                time.sleep(3)
                
                # Check new URL for building ID
                current_url = driver.current_url
                if "building/" in current_url:
                    building_id = current_url.split("building/")[1].split("/")[0]
                    if building_id and building_id.isdigit():
                        logger.info(f"Found building ID from search result: {building_id}")
                        return building_id
        
        logger.warning("Could not find building ID from HPD website")
        return None
    
    except Exception as e:
        logger.error(f"Error during HPD website search: {str(e)}")
        logger.error(traceback.format_exc())
        return None
    finally:
        driver.quit()

def get_311_complaints(address, zip_code, building_id=None):
    """
    Fetch 311 complaints data for a building using NYC's 311 Public API
    
    Args:
        address: Building address (e.g., "393 Hewes St")
        zip_code: ZIP code (e.g., "11211")
        building_id: Optional building ID if available
        
    Returns:
        List of 311 complaints for the address
    """
    logger.info(f"Fetching 311 complaints for address: {address}, zip: {zip_code}")
    
    # NYC API Subscription Key
    API_KEY = getattr(settings, "NYC_API_KEY", "ge4fy3cAUtrn!NM")
    
    # Parse the address for better matching
    try:
        parts = address.strip().split(' ', 1)
        if len(parts) == 2:
            house_number, street_name = parts[0], parts[1]
        else:
            house_number, street_name = "", address
    except Exception:
        house_number, street_name = "", address
    
    # 311 complaints list
    complaints = []
    
    # Try the NYC 311 Public API first
    try:
        # 311 API endpoint
        api_url = "https://api.nyc.gov/public/api/GetAssets"
        
        # Set up proper headers with subscription key
        headers = {
            "Ocp-Apim-Subscription-Key": API_KEY,
            "Accept": "application/json"
        }
        
        # Parameters for the API call - filter by address
        params = {
            "assetType": "311ServiceRequest",
            "searchAttributes[houseNumber]": house_number,
            "searchAttributes[streetName]": street_name,
            "searchAttributes[zipCode]": zip_code,
            "size": 100  # Get up to 100 complaints
        }
        
        logger.info(f"Calling NYC 311 API with: {params}")
        response = requests.get(api_url, headers=headers, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"311 API response received")
            
            # Extract complaints from the response
            if "assets" in data and isinstance(data["assets"], list):
                for complaint in data["assets"]:
                    # Extract relevant information
                    complaint_data = {}
                    
                    # Basic complaint information
                    if "id" in complaint:
                        complaint_data["sr_number"] = complaint["id"]
                    
                    if "attributes" in complaint:
                        attrs = complaint["attributes"]
                        
                        # Get created date
                        if "createdDate" in attrs:
                            complaint_data["date"] = attrs["createdDate"]
                        
                        # Get description
                        if "complaintType" in attrs:
                            complaint_data["description"] = attrs["complaintType"]
                        
                        # Get status
                        if "status" in attrs:
                            complaint_data["status"] = attrs["status"]
                        
                        # Get location details
                        if "incidentAddress" in attrs:
                            apartment = None
                            # Parse apartment from address if possible
                            address_match = re.search(r'apt\s*[#:]?\s*([0-9a-z]+)', attrs["incidentAddress"], re.IGNORECASE)
                            if address_match:
                                apartment = address_match.group(1).upper()
                            complaint_data["apt"] = apartment
                        
                        # Get complaint details
                        if "descriptor" in attrs:
                            complaint_data["complaint_detail"] = attrs["descriptor"]
                        
                        # Get location type
                        if "locationType" in attrs:
                            complaint_data["location"] = attrs["locationType"]
                    
                    # Add to complaints list
                    complaints.append(complaint_data)
                
                logger.info(f"Found {len(complaints)} 311 complaints from API")
            else:
                logger.warning("No assets found in 311 API response")
        else:
            logger.warning(f"311 API call failed. Status: {response.status_code}")
    
    except Exception as e:
        logger.error(f"Error calling NYC 311 API: {str(e)}")
    
    # As a backup, try the NYC Open Data 311 Dataset
    if not complaints:
        try:
            # NYC Open Data 311 Service Requests API endpoint
            open_data_url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
            
            # Build query to find complaints for this address
            where_clause = f"incident_address LIKE '{house_number} {street_name}%' AND incident_zip='{zip_code}'"
            
            # Parameters for the API call
            params = {
                "$where": where_clause,
                "$limit": 100,
                "$order": "created_date DESC"
            }
            
            logger.info(f"Calling Open Data 311 API with: {params}")
            response = requests.get(open_data_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Process each complaint
                for item in data:
                    complaint_data = {
                        "sr_number": item.get("unique_key", ""),
                        "date": item.get("created_date", ""),
                        "description": item.get("complaint_type", ""),
                        "complaint_detail": item.get("descriptor", ""),
                        "status": item.get("status", "OPEN"),
                        "location": item.get("location_type", "")
                    }
                    
                    # Get apartment if available
                    if "apartment" in item:
                        complaint_data["apt"] = item.get("apartment", "").upper()
                    
                    # Add to complaints list
                    complaints.append(complaint_data)
                
                logger.info(f"Found {len(complaints)} 311 complaints from Open Data API")
            else:
                logger.warning(f"Open Data 311 API call failed. Status: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Error calling Open Data 311 API: {str(e)}")
    
    return complaints

def get_hpd_data(building_id):
    """
    Fetch HPD data for a building using its building ID
    First tries to use NYC's official APIs, then falls back to browser-based scraping if needed
    """
    logger.info(f"Fetching HPD data for building ID: {building_id}")
    
    # Prepare the result data structure
    result = {
        'metadata': {
            'building_id': building_id,
            'address': '',
            'zip_code': '',
            'borough': ''
        },
        'violations': [],
        'complaints': [],
        'complaints_311': []  # New field for 311 complaints
    }
    
    # NYC API Key
    API_KEY = getattr(settings, "NYC_API_KEY", "ge4fy3cAUtrn!NM")
    
    # First try to get HPD violation data from the NYC Open Data API
    try:
        # HPD violations API endpoint
        violations_api_url = "https://data.cityofnewyork.us/resource/wvxf-dwi5.json"
        
        # Query parameters
        params = {
            "$where": f"buildingid='{building_id}'",
            "$limit": 2000,  # Increased limit to get more violations
            "$order": "inspectiondate DESC"
        }
        
        logger.info(f"Calling HPD Violations API for building ID {building_id}")
        response = requests.get(violations_api_url, params=params, timeout=15)
        
        if response.status_code == 200:
            violations_data = response.json()
            logger.info(f"Found {len(violations_data)} violations from API")
            
            # Process each violation
            for vio in violations_data:
                violation = {
                    'violation_number': vio.get('violationid', ''),
                    'class': vio.get('class', ''),
                    'apartment': vio.get('apartment', '').upper(),
                    'story': vio.get('story', ''),
                    'date': vio.get('inspectiondate', ''),
                    'description': vio.get('novdescription', '')
                }
                
                # Additional data that might be useful
                if 'novissuedate' in vio:
                    violation['issue_date'] = vio.get('novissuedate', '')
                
                if 'currentstatusdate' in vio:
                    violation['status_date'] = vio.get('currentstatusdate', '')
                
                if 'currentstatus' in vio:
                    violation['status'] = vio.get('currentstatus', '')
                
                # Add to results
                result['violations'].append(violation)
            
            # Get building information if available
            if violations_data and len(violations_data) > 0:
                first_vio = violations_data[0]
                
                if 'housenumber' in first_vio and 'streetname' in first_vio:
                    result['metadata']['address'] = f"{first_vio.get('housenumber', '')} {first_vio.get('streetname', '')}".strip()
                
                if 'zip' in first_vio:
                    result['metadata']['zip_code'] = first_vio.get('zip', '')
                
                if 'boroid' in first_vio:
                    # Convert borough ID to name
                    boro_id = first_vio.get('boroid', '')
                    boro_map = {"1": "Manhattan", "2": "Bronx", "3": "Brooklyn", "4": "Queens", "5": "Staten Island"}
                    result['metadata']['borough'] = boro_map.get(boro_id, '')
        else:
            logger.warning(f"HPD Violations API call failed. Status: {response.status_code}")
    
    except Exception as e:
        logger.error(f"Error calling HPD Violations API: {str(e)}")
    
    # Next try to get HPD complaints data from NYC Open Data API
    try:
        # HPD complaints API endpoint
        complaints_api_url = "https://data.cityofnewyork.us/resource/uwyv-629c.json"
        
        # Query parameters
        params = {
            "$where": f"buildingid='{building_id}'",
            "$limit": 1000,
            "$order": "receiveddate DESC"
        }
        
        logger.info(f"Calling HPD Complaints API for building ID {building_id}")
        response = requests.get(complaints_api_url, params=params, timeout=15)
        
        if response.status_code == 200:
            complaints_data = response.json()
            logger.info(f"Found {len(complaints_data)} complaints from API")
            
            # Process each complaint
            for comp in complaints_data:
                complaint = {
                    'sr_number': comp.get('complaintid', ''),
                    'date': comp.get('receiveddate', ''),
                    'complaint_id': comp.get('complaintid', ''),
                    'apt': comp.get('apartment', '').upper(),
                    'description': comp.get('complainttype', ''),
                    'complaint_detail': comp.get('spacetype', ''),
                    'status': comp.get('status', 'OPEN')
                }
                
                # Add location if available
                if 'majorcategory' in comp:
                    complaint['location'] = comp.get('majorcategory', '')
                elif 'minorcategory' in comp:
                    complaint['location'] = comp.get('minorcategory', '')
                
                # Add to results
                result['complaints'].append(complaint)
                
            # If we didn't get building info from violations, try to get it from complaints
            if not result['metadata']['address'] and complaints_data and len(complaints_data) > 0:
                first_comp = complaints_data[0]
                
                if 'housenumber' in first_comp and 'streetname' in first_comp:
                    result['metadata']['address'] = f"{first_comp.get('housenumber', '')} {first_comp.get('streetname', '')}".strip()
                
                if 'zip' in first_comp:
                    result['metadata']['zip_code'] = first_comp.get('zip', '')
                
                if 'boroid' in first_comp:
                    # Convert borough ID to name
                    boro_id = first_comp.get('boroid', '')
                    boro_map = {"1": "Manhattan", "2": "Bronx", "3": "Brooklyn", "4": "Queens", "5": "Staten Island"}
                    result['metadata']['borough'] = boro_map.get(boro_id, '')
        else:
            logger.warning(f"HPD Complaints API call failed. Status: {response.status_code}")
    
    except Exception as e:
        logger.error(f"Error calling HPD Complaints API: {str(e)}")
    
    # Try to get more building details directly from Building Information API if available
    try:
        # Building Information API endpoint
        building_api_url = f"https://api.nyc.gov/buildings/buildinginfo/v1/bin/{building_id}"
        
        # Set up headers
        headers = {
            "Ocp-Apim-Subscription-Key": API_KEY,
            "Accept": "application/json"
        }
        
        logger.info(f"Calling Building Info API for building ID {building_id}")
        response = requests.get(building_api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            building_data = response.json()
            logger.info(f"Found building information from API")
            
            # Extract building information
            if isinstance(building_data, dict):
                if 'address' in building_data:
                    result['metadata']['address'] = building_data.get('address', '')
                
                if 'zip' in building_data:
                    result['metadata']['zip_code'] = building_data.get('zip', '')
                
                if 'boro' in building_data:
                    result['metadata']['borough'] = building_data.get('boro', '')
                
                # Add any other relevant building information
                result['metadata']['building_info'] = {
                    'construction_year': building_data.get('year_built', ''),
                    'num_floors': building_data.get('num_floors', ''),
                    'building_class': building_data.get('building_class', ''),
                    'zoning': building_data.get('zoning', '')
                }
        else:
            logger.warning(f"Building Info API call failed. Status: {response.status_code}")
    
    except Exception as e:
        logger.error(f"Error calling Building Info API: {str(e)}")
    
    # Now that we have some building information, get 311 complaints
    if result['metadata']['address'] and result['metadata']['zip_code']:
        result['complaints_311'] = get_311_complaints(
            result['metadata']['address'], 
            result['metadata']['zip_code'],
            building_id
        )
    
    # If we didn't get enough data from the APIs, fall back to browser-based scraping
    if (len(result['violations']) == 0 and len(result['complaints']) == 0) or not result['metadata']['address']:
        logger.info(f"Insufficient data from APIs. Falling back to browser-based scraping for building ID {building_id}")
        browser_result = scrape_hpd_with_selenium(building_id)
        
        # Merge the browser result with any 311 data we got
        browser_result['complaints_311'] = result.get('complaints_311', [])
        return browser_result
    
    logger.info(f"Successfully retrieved HPD data using APIs. Found {len(result['violations'])} violations, {len(result['complaints'])} HPD complaints, and {len(result['complaints_311'])} 311 complaints.")
    return result

def scrape_hpd_with_selenium(building_id):
    """
    Fallback method to scrape HPD data using Selenium browser automation
    This is used only when the API methods fail to return sufficient data
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time
    
    # Initialize a headless browser
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Start the browser
    driver = webdriver.Chrome(options=options)
    
    try:
        # Prepare the result data
        result = {
            'metadata': {
                'building_id': building_id,
                'address': '',
                'zip_code': '',
                'borough': ''
            },
            'violations': [],
            'complaints': [],
            'complaints_311': []  # New field for 311 complaints
        }
        
        # First get building info
        url = f"https://hpdonline.nyc.gov/hpdonline/building/{building_id}"
        logger.info(f"Fetching building info from: {url}")
        driver.get(url)
        
        # Wait for the page to load
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Wait additional time for Angular to initialize
        time.sleep(5)
        
        # Extract address and other building information
        try:
            # Look for address information
            address_elements = driver.find_elements(By.CSS_SELECTOR, ".property-info-title, .property-address, h1")
            for elem in address_elements:
                if elem.text and not elem.text.lower().startswith("property"):
                    result['metadata']['address'] = elem.text.strip()
                    break
            
            # Extract ZIP code if present
            zip_elements = driver.find_elements(By.CSS_SELECTOR, ".zip-code, .postal-code")
            for elem in zip_elements:
                zip_match = re.search(r'\b\d{5}\b', elem.text)
                if zip_match:
                    result['metadata']['zip_code'] = zip_match.group(0)
                    break
            
            # If we still don't have a ZIP, try to extract from full address
            if not result['metadata']['zip_code'] and result['metadata']['address']:
                zip_match = re.search(r'\b\d{5}\b', result['metadata']['address'])
                if zip_match:
                    result['metadata']['zip_code'] = zip_match.group(0)
            
            # Extract borough if present
            borough_elements = driver.find_elements(By.CSS_SELECTOR, ".borough, .location-info")
            for elem in borough_elements:
                if any(borough.lower() in elem.text.lower() for borough in ["brooklyn", "manhattan", "bronx", "queens", "staten island"]):
                    borough_match = re.search(r'(brooklyn|manhattan|bronx|queens|staten island)', elem.text.lower())
                    if borough_match:
                        result['metadata']['borough'] = borough_match.group(0).title()
                        break
        except Exception as e:
            logger.error(f"Error extracting building info: {str(e)}")
        
        # Get violations
        url = f"https://hpdonline.nyc.gov/hpdonline/building/{building_id}/violations"
        logger.info(f"Fetching violations from: {url}")
        driver.get(url)
        
        # Wait for the page to load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Wait additional time for Angular to initialize
        time.sleep(5)
        
        # Extract violations
        try:
            # Look for violation table or list items
            violation_elements = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, .violation-item, mat-row")
            
            if violation_elements:
                for elem in violation_elements:
                    try:
                        violation_data = {}
                        
                        # Extract text from the element
                        elem_text = elem.text
                        
                        # Skip empty elements
                        if not elem_text.strip():
                            continue
                            
                        # Try to extract violation number
                        violation_match = re.search(r'\b(\d{6,8})\b', elem_text)
                        if violation_match:
                            violation_data['violation_number'] = violation_match.group(1)
                        else:
                            # Try to get from child elements if available
                            violation_number_elem = elem.find_elements(By.CSS_SELECTOR, "td:first-child, .violation-number")
                            if violation_number_elem:
                                violation_number = violation_number_elem[0].text.strip()
                                if re.match(r'\d+', violation_number):
                                    violation_data['violation_number'] = violation_number
                        
                        # Skip if we couldn't find a violation number
                        if 'violation_number' not in violation_data:
                            continue
                        
                        # Extract class/severity
                        class_match = re.search(r'class\s*[:-]?\s*([abc])', elem_text, re.IGNORECASE)
                        if class_match:
                            violation_data['class'] = class_match.group(1).upper()
                        else:
                            # Check for specific text that might indicate class
                            if 'immediately hazardous' in elem_text.lower() or 'class c' in elem_text.lower():
                                violation_data['class'] = 'C'
                            elif 'hazardous' in elem_text.lower() or 'class b' in elem_text.lower():
                                violation_data['class'] = 'B'
                            elif 'non-hazardous' in elem_text.lower() or 'class a' in elem_text.lower():
                                violation_data['class'] = 'A'
                        
                        # Extract apartment
                        apt_match = re.search(r'apt\s*[#:]?\s*([0-9a-z]+)', elem_text, re.IGNORECASE)
                        if apt_match:
                            violation_data['apartment'] = apt_match.group(1).upper()
                        
                        # Extract date
                        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', elem_text)
                        if date_match:
                            violation_data['date'] = date_match.group(1)
                        
                        # Extract description - this could be complex and vary by page structure
                        # First look for sections with section symbols
                        desc_match = re.search(r'(§[\s\S]*?)(?=\n\n|\Z)', elem_text)
                        if desc_match:
                            violation_data['description'] = desc_match.group(1).strip()
                        else:
                            # Look for longer text blocks that might be descriptions
                            lines = elem_text.split('\n')
                            for line in lines:
                                if len(line) > 40 and not re.match(r'^\d+$', line):
                                    violation_data['description'] = line.strip()
                                    break
                        
                        # Add to results if we have essential data
                        if 'violation_number' in violation_data:
                            result['violations'].append(violation_data)
                    except Exception as e:
                        logger.error(f"Error extracting violation: {str(e)}")
            
            logger.info(f"Found {len(result['violations'])} violations")
            
            # If no violations found via table/list, check for any text indicating violations
            if not result['violations']:
                page_text = driver.find_element(By.TAG_NAME, "body").text
                
                # Check for standard "no violations" messages
                no_violations_phrases = [
                    "no violations found",
                    "no open violations",
                    "no violations on record",
                    "0 violations",
                    "zero violations"
                ]
                
                if not any(phrase in page_text.lower() for phrase in no_violations_phrases):
                    # Try extracting all possible violation IDs with surrounding context
                    violation_matches = re.finditer(r'\b(\d{6,8})\b', page_text)
                    for match in violation_matches:
                        vio_number = match.group(1)
                        
                        # Get surrounding text (50 chars before and after)
                        start = max(0, match.start() - 50)
                        end = min(len(page_text), match.end() + 50)
                        context = page_text[start:end]
                        
                        violation_data = {
                            'violation_number': vio_number,
                            'description': f"Context: {context}"
                        }
                        
                        # Extract class if present in context
                        class_match = re.search(r'class\s*[:-]?\s*([abc])', context, re.IGNORECASE)
                        if class_match:
                            violation_data['class'] = class_match.group(1).upper()
                        
                        result['violations'].append(violation_data)
        except Exception as e:
            logger.error(f"Error extracting violations: {str(e)}")
        
        # Get complaints
        url = f"https://hpdonline.nyc.gov/hpdonline/building/{building_id}/complaints"
        logger.info(f"Fetching complaints from: {url}")
        driver.get(url)
        
        # Wait for the page to load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Wait additional time for Angular to initialize
        time.sleep(5)
        
        # Extract complaints
        try:
            # Look for complaint table or list items
            complaint_elements = driver.find_elements(By.CSS_SELECTOR, "table tbody tr, .complaint-item, mat-row")
            
            if complaint_elements:
                for elem in complaint_elements:
                    try:
                        complaint_data = {}
                        
                        # Extract text from the element
                        elem_text = elem.text
                        
                        # Skip empty elements
                        if not elem_text.strip():
                            continue
                        
                        # Try to extract SR number
                        sr_match = re.search(r'\b(SR\s*[a-z0-9-]+|\d{6,10}[a-z]*)\b', elem_text, re.IGNORECASE)
                        if sr_match:
                            complaint_data['sr_number'] = sr_match.group(1)
                        
                        # Extract date
                        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', elem_text)
                        if date_match:
                            complaint_data['date'] = date_match.group(1)
                        
                        # Extract description (any longer text)
                        lines = elem_text.split('\n')
                        for line in lines:
                            if len(line) > 30 and not re.match(r'^\d+$', line) and 'sr' not in line.lower():
                                complaint_data['description'] = line.strip()
                                break
                        
                        # Extract apartment if present
                        apt_match = re.search(r'apt\s*[#:]?\s*([0-9a-z]+)', elem_text, re.IGNORECASE)
                        if apt_match:
                            complaint_data['apt'] = apt_match.group(1).upper()
                        
                        # Extract status if present
                        status_match = re.search(r'\b(open|closed|pending)\b', elem_text, re.IGNORECASE)
                        if status_match:
                            complaint_data['status'] = status_match.group(1).upper()
                        
                        # Add to results if we have essential data
                        if 'sr_number' in complaint_data or 'description' in complaint_data:
                            result['complaints'].append(complaint_data)
                    except Exception as e:
                        logger.error(f"Error extracting complaint: {str(e)}")
            
            logger.info(f"Found {len(result['complaints'])} complaints")
        except Exception as e:
            logger.error(f"Error extracting complaints: {str(e)}")
        
        return result
    finally:
        # Clean up
        driver.quit()

def parse_hpd_violations(html_content):
    """Parse HPD violations from HTML content"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        violations = []
        
        # Look for table rows
        tables = soup.select("table, mat-table, .mat-table")
        for table in tables:
            rows = table.select("tr:not(:first-child), .mat-row, [role='row']:not([role='columnheader'])")
            for row in rows:
                cells = row.select("td, .mat-cell, [role='cell']")
                if cells and len(cells) >= 5:
                    # Extract data from cells based on position
                    # This may need adjustment based on the actual HTML structure
                    violation = {
                        "violation_number": cells[0].text.strip() if len(cells) > 0 else "",
                        "class": cells[1].text.strip() if len(cells) > 1 else "",
                        "order": cells[2].text.strip() if len(cells) > 2 else "",
                        "apartment": cells[3].text.strip() if len(cells) > 3 else "",
                        "story": cells[4].text.strip() if len(cells) > 4 else "",
                        "date": cells[5].text.strip() if len(cells) > 5 else "",
                        "description": cells[6].text.strip() if len(cells) > 6 else ""
                    }
                    violations.append(violation)
        
        # If no violations found from tables, try alternative approaches
        if not violations:
            # Try to find violation cards/items
            items = soup.select(".violation-item, mat-card, .card, .item")
            for item in items:
                item_text = item.text
                
                # Extract violation details using regex
                vio_number_match = re.search(r'\b(\d{6,8})\b', item_text)
                if vio_number_match:
                    vio_number = vio_number_match.group(1)
                    
                    # Extract other data
                    class_match = re.search(r'class\s*[:-]?\s*([abc])', item_text, re.IGNORECASE)
                    apt_match = re.search(r'apt\s*[#:]?\s*([0-9a-z]+)', item_text, re.IGNORECASE)
                    date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', item_text)
                    desc_match = re.search(r'(§.*?(?=\n\n|\Z))', item_text, re.DOTALL)
                    
                    violation = {
                        "violation_number": vio_number,
                        "class": class_match.group(1).upper() if class_match else "",
                        "apartment": apt_match.group(1).upper() if apt_match else "",
                        "date": date_match.group(1) if date_match else "",
                        "description": desc_match.group(1).strip() if desc_match else ""
                    }
                    violations.append(violation)
        
        return violations
    except Exception as e:
        logger.error(f"Error parsing violations: {str(e)}")
        return []

def parse_hpd_complaints(html_content):
    """Parse HPD complaints from HTML content"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        complaints = []
        
        # Look for table rows
        tables = soup.select("table, mat-table, .mat-table")
        for table in tables:
            rows = table.select("tr:not(:first-child), .mat-row, [role='row']:not([role='columnheader'])")
            for row in rows:
                cells = row.select("td, .mat-cell, [role='cell']")
                if cells and len(cells) >= 5:
                    # Extract data from cells based on position
                    complaint = {
                        "sr_number": cells[0].text.strip() if len(cells) > 0 else "",
                        "date": cells[1].text.strip() if len(cells) > 1 else "",
                        "complaint_id": cells[2].text.strip() if len(cells) > 2 else "",
                        "apt": cells[3].text.strip() if len(cells) > 3 else "",
                        "description": cells[4].text.strip() if len(cells) > 4 else "",
                        "complaint_detail": cells[5].text.strip() if len(cells) > 5 else "",
                        "location": cells[6].text.strip() if len(cells) > 6 else "",
                        "status": cells[7].text.strip() if len(cells) > 7 else "OPEN"
                    }
                    complaints.append(complaint)
        
        return complaints
    except Exception as e:
        logger.error(f"Error parsing complaints: {str(e)}")
        return []

def parse_building_info(html_content):
    """Parse building information from HPD building page"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        metadata = {}
        
        # Try to find address information
        address_elements = soup.select(".building-address, .address, h1, h2")
        for element in address_elements:
            text = element.text.strip()
            if text and re.search(r'\d+\s+[A-Za-z]', text):
                metadata["address"] = text
                break
        
        # Look for other metadata like zip, borough, etc.
        info_labels = soup.select(".info-label, dt, .label")
        for label in info_labels:
            label_text = label.text.strip().lower()
            if "zip" in label_text or "postal" in label_text:
                value = label.find_next("dd, .value, .info-value")
                if value:
                    metadata["zip_code"] = value.text.strip()
            elif "borough" in label_text:
                value = label.find_next("dd, .value, .info-value")
                if value:
                    metadata["borough"] = value.text.strip()
        
        return metadata
    except Exception as e:
        logger.error(f"Error parsing building info: {str(e)}")
        return {}

def scrape_hpd_online(request):
    """
    View to scrape HPD Online's website. Can be called via AJAX.
    
    Args:
        request: Django request object with 'address' and 'zip_code' parameters
        
    Returns:
        JSON response with scraped data or error message
    """
    logger.info("HPD lookup request received")
    
    address = request.GET.get('address', '').strip()
    zip_code = request.GET.get('zip_code', '').strip()
    
    if not address or not zip_code:
        return JsonResponse({'success': False, 'error': 'Address and ZIP code are required'})
    
    logger.info(f"Looking up HPD data for: Address='{address}', ZIP='{zip_code}'")
    
    try:
        # Known addresses with hardcoded building IDs - for immediate response without API calls
        KNOWN_ADDRESSES = {
            "393 hewes st": {"zip": "11211", "id": "312124"},
            "395 hewes st": {"zip": "11211", "id": "312124"},
            "393-395 hewes st": {"zip": "11211", "id": "312124"},
            "393-395 hewes street": {"zip": "11211", "id": "312124"},
            # Add more known addresses here as needed
        }
        
        # Check if this is a known address
        normalized_address = address.lower().strip()
        
        # Try to get building ID - first check known addresses
        building_id = None
        if normalized_address in KNOWN_ADDRESSES and KNOWN_ADDRESSES[normalized_address]["zip"] == zip_code:
            building_id = KNOWN_ADDRESSES[normalized_address]["id"]
            logger.info(f"Using hardcoded building ID for {address}")
        else:
            # Try to get building ID from API with fallback methods
            logger.info(f"Getting building ID for address: {address}, zip: {zip_code}")
            building_id = get_building_id(address, zip_code)
        
        if not building_id:
            return JsonResponse({
                'success': False, 
                'error': 'Building ID not found. Please check the address and ZIP code and try again.'
            })
            
        # Get HPD data using the building ID
        logger.info(f"Fetching HPD data for building ID: {building_id}")
        hpd_data = get_hpd_data(building_id)
        
        # Make sure metadata includes the address and zip if not already populated
        if not hpd_data["metadata"].get("address"):
            hpd_data["metadata"]["address"] = address
        
        if not hpd_data["metadata"].get("zip_code"):
            hpd_data["metadata"]["zip_code"] = zip_code
            
        if not hpd_data["metadata"].get("borough"):
            # Try to get borough from zip code
            hpd_data["metadata"]["borough"] = get_borough_from_zip(zip_code)
        
        # Make sure building ID is in metadata
        hpd_data["metadata"]["building_id"] = building_id
        
        logger.info(f"HPD data lookup successful. Found {len(hpd_data['violations'])} violations and {len(hpd_data['complaints'])} complaints.")
        
        return JsonResponse({
            'success': True,
            'data': hpd_data
        })
    except Exception as e:
        logger.error(f"Error scraping HPD: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': f"Error looking up HPD data: {str(e)}"
        })

def get_borough_from_zip(zip_code):
    """
    Map a ZIP code to a NYC borough.
    
    Args:
        zip_code: ZIP code (e.g., "10001")
    
    Returns:
        Borough name (Manhattan, Brooklyn, etc.)
    """
    zip_code = str(zip_code).strip()
    
    # Manhattan: 10001-10282
    if zip_code.startswith('100') or zip_code.startswith('101') or zip_code.startswith('102'):
        return "Manhattan"
    
    # Bronx: 10451-10475
    elif zip_code.startswith('104'):
        return "Bronx"
    
    # Brooklyn: 11201-11256
    elif zip_code.startswith('112'):
        return "Brooklyn"
    
    # Queens: 11004-11109, 11351-11697
    elif zip_code.startswith('110') or zip_code.startswith('111') or zip_code.startswith('113') or zip_code.startswith('114') or zip_code.startswith('116'):
        return "Queens"
    
    # Staten Island: 10301-10314
    elif zip_code.startswith('103'):
        return "Staten Island"
    
    # Default to Brooklyn if we can't determine
    return "Brooklyn"