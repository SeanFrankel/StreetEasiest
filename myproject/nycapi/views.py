# views.py
import logging
import requests
import time
from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)

# NYC GeoClient API credentials (now using settings)
# These are kept for backward compatibility but should use settings instead


def get_borough_from_zip(zip_code):
    borough_map = {
        'MANHATTAN': list(range(10001, 10283)) + [10292],
        'BRONX': list(range(10451, 10476)),
        'BROOKLYN': list(range(11201, 11257)) + [11351],
        'QUEENS': list(range(11004, 11110)) + list(range(11351, 11698)),
        'STATEN ISLAND': list(range(10301, 10315))
    }
    try:
        z = int(zip_code)
        for borough, zips in borough_map.items():
            if z in zips:
                return borough.title()
    except Exception as e:
        logger.error(f"Error determining borough: {e}")
    return None


def api_get(url, params=None, headers=None, timeout=10, retries=2):
    """Helper for GET requests with error handling and retry logic."""
    headers = headers or {}
    # Add User-Agent to avoid being blocked
    headers["User-Agent"] = "StreetEasiest/1.0 (NYC Data Lookup Tool)"
    
    # NYC Open Data APIs work without authentication for basic queries
    # Commenting out API key authentication as it's causing 403 errors
    # Most NYC APIs have generous rate limits without requiring authentication
    logger.info(f"Making API call to {url} without authentication")
    
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            
            # Log details for debugging
            logger.info(f"API call to {url} - Status: {resp.status_code}, Attempt: {attempt + 1}")
            
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code in [503, 429]:  # Rate limited or service unavailable
                if attempt < retries:
                    wait_time = (2 ** attempt) + 1  # Exponential backoff: 2, 5, 9 seconds
                    logger.warning(f"Rate limited/throttled (HTTP {resp.status_code}) for {url} - Retrying in {wait_time}s (attempt {attempt + 1}/{retries + 1})")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Rate limited/throttled (HTTP {resp.status_code}) for {url} - Max retries exceeded")
                    return None
            else:
                logger.error(f"API call to {url} failed: {resp.status_code} - Response: {resp.text[:200]}")
                return None
                
        except Exception as e:
            if attempt < retries:
                wait_time = (2 ** attempt) + 1
                logger.warning(f"API exception for {url}: {e} - Retrying in {wait_time}s")
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"API exception for {url}: {e} - Max retries exceeded")
                return None
    
    return None


def get_building_id(address, zip_code):
    """
    Returns a tuple (BIN, BBL) for the given address via GeoClient,
    authenticating with the subscription key.
    """
    parts = address.strip().split()
    if len(parts) < 2:
        logger.error("Invalid address format")
        return None, None
    house_number = parts[0]
    street       = " ".join(parts[1:])
    borough      = get_borough_from_zip(zip_code)
    if not borough:
        logger.error("Cannot determine borough for ZIP %s", zip_code)
        return None, None

    url = "https://api.nyc.gov/geo/geoclient/v2/address"
    params = {
        "houseNumber": house_number,
        "street": street,
        "borough": borough,
        "zip": zip_code,
        "app_id": getattr(settings, 'NYC_GEOCLIENT_APP_ID', '')
    }
    # Geoclient requires the subscription key header
    headers = {"Ocp-Apim-Subscription-Key": getattr(settings, 'NYC_GEOCLIENT_APP_KEY', '')}
    data = api_get(url, params=params, headers=headers, timeout=10)
    if data and data.get("address"):
        addr = data["address"]
        bin_ = addr.get("buildingIdentificationNumber")
        bbl  = addr.get("bbl")
        return bin_, bbl
    return None, None


def get_hpd_violations(bin_number):
    if not bin_number:
        logger.warning("get_hpd_violations called with no bin_number")
        return [], 0
    url = "https://data.cityofnewyork.us/resource/wvxf-dwi5.json"
    
    # Get data first, then estimate count from results
    params = {
        "$where": f"bin='{bin_number}'",
        "$order": "inspectiondate DESC",
        "$limit": 1000  # Increased limit to get more comprehensive results
    }

    logger.info(f"Making HPD API call with BIN: {bin_number}, URL: {url}, params: {params}")
    data = api_get(url, params=params, timeout=30)  # Increased timeout
    logger.info(f"HPD API returned data: {data is not None}, length: {len(data) if data else 0}")
    if not data:
        logger.warning(f"No HPD data returned for BIN: {bin_number}")
        return [], 0
        
    # If we got exactly 1000 results, there might be more - do a separate count query
    if len(data) == 1000:
        count_params = {
            "$query": f"SELECT count(*) WHERE bin='{bin_number}'"
        }
        count_result = api_get(url, params=count_params, timeout=20)
        total_count = int(count_result[0]['count']) if count_result else len(data)
    else:
        total_count = len(data)
    
    # Return only the first 50 for display, but keep the accurate total count
    return data[:50], total_count


def get_311_complaints(bbl):
    """
    Fetch 311 complaints using only the BBL.
    """
    if not bbl:
        return [], 0
    url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"

    # Get data first with higher limit
    params = {
        "$where": f"bbl='{bbl}'",
        "$order": "created_date DESC",
        "$limit": 1000
    }

    data = api_get(url, params=params, timeout=30)
    if not data:
        return [], 0
        
    # If we got exactly 1000 results, there might be more
    if len(data) == 1000:
        count_params = {
            "$query": f"SELECT count(*) WHERE bbl='{bbl}'"
        }
        count_result = api_get(url, params=count_params, timeout=20)
        total_count = int(count_result[0]['count']) if count_result else len(data)
    else:
        total_count = len(data)
    
    return data[:50], total_count

def get_bedbug_reports(bin_number):
    if not bin_number:
        return [], 0
    url = "https://data.cityofnewyork.us/resource/wz6d-d3jb.json"
    
    # Get data first with higher limit
    params = {"$where": f"bin='{bin_number}'", "$order": "filing_date DESC", "$limit": 1000}
    data = api_get(url, params=params, timeout=30)
    if not data:
        return [], 0
        
    # If we got exactly 1000 results, there might be more
    if len(data) == 1000:
        count_params = {
            "$query": f"SELECT count(*) WHERE bin='{bin_number}'"
        }
        count_result = api_get(url, params=count_params, timeout=20)
        total_count = int(count_result[0]['count']) if count_result else len(data)
    else:
        total_count = len(data)
    
    return data[:50], total_count


def get_housing_litigation(bin_number):
    if not bin_number:
        return [], 0
    url = "https://data.cityofnewyork.us/resource/59kj-x8nc.json"
    
    # Get data first with higher limit
    params = {"$where": f"bin='{bin_number}'", "$order": "caseopendate DESC", "$limit": 1000}
    data = api_get(url, params=params, timeout=30)
    if not data:
        return [], 0
        
    # If we got exactly 1000 results, there might be more
    if len(data) == 1000:
        count_params = {
            "$query": f"SELECT count(*) WHERE bin='{bin_number}'"
        }
        count_result = api_get(url, params=count_params, timeout=20)
        total_count = int(count_result[0]['count']) if count_result else len(data)
    else:
        total_count = len(data)
    
    return data[:50], total_count


def get_lead_paint_violations(bin_number):
    """
    Fetch HPD Lead Paint Violations by filtering from the main HPD violations dataset.
    Try the dedicated lead paint API first, fall back to filtering if unavailable.
    """
    if not bin_number:
        return [], 0
    
    # First try the dedicated lead paint violations API
    lead_api_url = "https://data.cityofnewyork.us/resource/au8t-hgv2.json"
    
    # Try dedicated API first with optimized single request
    params = {
        "$where": f"bin='{bin_number}'",
        "$order": "inspectiondate DESC",
        "$limit": 1000
    }
    data = api_get(lead_api_url, params=params, timeout=30)
    
    if data:
        # Dedicated API is working - return results
        total_count = len(data) if len(data) < 1000 else 1000  # Estimate if we hit the limit
        return data[:50], total_count
    
    # Fall back to filtering main HPD violations dataset for lead-specific violations
    url = "https://data.cityofnewyork.us/resource/wvxf-dwi5.json"
    
    # More specific lead paint filter - focus on lead-based paint hazards
    lead_filter = (
        "upper(novdescription) like upper('%lead%paint%') OR "
        "upper(novdescription) like upper('%lead%based%') OR "
        "upper(novdescription) like upper('%lead%hazard%') OR "
        "upper(novdescription) like upper('%peeling%paint%') OR "
        "upper(novdescription) like upper('%deteriorated%paint%')"
    )
    
    # Get the actual lead-related violation data with optimized request
    params = {
        "$where": f"bin='{bin_number}' AND ({lead_filter})",
        "$order": "inspectiondate DESC",
        "$limit": 1000
    }
    
    data = api_get(url, params=params, timeout=30)
    if not data:
        return [], 0
    
    # If we got exactly 1000 results, there might be more
    if len(data) == 1000:
        count_params = {
            "$query": f"SELECT count(*) WHERE bin='{bin_number}' AND ({lead_filter})"
        }
        count_result = api_get(url, params=count_params, timeout=20)
        total_count = int(count_result[0]['count']) if count_result else len(data)
    else:
        total_count = len(data)
    
    return data[:50], total_count


def get_rent_stabilization_info(bbl, address=None, zip_code=None):
    """
    Get rent stabilization information using NYCDB CSV data (single-tier approach).
    
    Shows rent stabilized unit counts for 2018 and 2023 from NYCDB data.
    
    Args:
        bbl: Borough-Block-Lot number (e.g., "3024250032")
        
    Returns:
        dict: {
            "has_rent_stabilized": "Yes"/"No"/"N/A",
            "units_count_2023": int or None,
            "units_count_2018": int or None, 
            "units_difference": int or None,
            "source": "NYCDB", 
            "official_reason": str or None,
            "details": str or None
        }
    """
    if not bbl:
        return {
            "has_rent_stabilized": "N/A",
            "units_count_2023": None,
            "units_count_2018": None,
            "units_difference": None,
            "source": "error",
            "official_reason": None,
            "details": "No BBL provided"
        }
    
    # Get both 2023 and 2018 data from NYCDB CSV
    csv_result = get_rent_stabilized_data_from_csv(bbl)
    
    # Extract counts
    units_2023 = csv_result.get("units_count_2023")
    units_2018 = csv_result.get("units_count_2018")
    
    # Calculate difference
    units_difference = None
    if units_2023 is not None and units_2018 is not None:
        units_difference = units_2023 - units_2018
    elif units_2023 is not None and units_2018 is None:
        units_difference = units_2023  # New in 2023
    elif units_2023 is None and units_2018 is not None:
        units_difference = -units_2018  # Removed by 2023
    
    # Determine overall status based on either year having data
    has_rent_stabilized = "No"
    source = "NYCDB"
    official_reason = "No rent-stabilized units found in NYCDB data"
    
    if units_2023 or units_2018:
        has_rent_stabilized = "Yes"
        if units_2023 and units_2018:
            official_reason = f"Found in both 2023 ({units_2023} units) and 2018 ({units_2018} units) records"
        elif units_2023:
            official_reason = f"Found {units_2023} units in 2023 records (no 2018 data)"
        else:
            official_reason = f"Found {units_2018} units in 2018 records (no 2023 data)"
    elif csv_result["found"]:
        # Building was found but no rent stabilized units
        has_rent_stabilized = "No"
        official_reason = "Building found but no rent-stabilized units in available years"
    
    return {
        "has_rent_stabilized": has_rent_stabilized,
        "units_count_2023": units_2023,
        "units_count_2018": units_2018,
        "units_difference": units_difference,
        "source": source,
        "official_reason": official_reason,
        "details": csv_result.get("details")
    }





def get_ownership_info(bbl, bin_number=None):
    """
    Get building ownership information using NYC open data sources.
    Uses the same methodology as JustFix.NYC without relying on their API.
    
    Args:
        bbl: Borough-Block-Lot number 
        bin_number: Building Identification Number
        
    Returns:
        dict: {"owner_name": str, "owner_contact": str, "registration_info": dict}
    """
    if not bbl and not bin_number:
        return {
            "owner_name": None,
            "owner_contact": None, 
            "registration_info": None
        }
    
    try:
        # Method 1: HPD Registration data (most comprehensive for rental buildings)
        # This is the same source JustFix.NYC uses for ownership information
        hpd_registration_url = "https://data.cityofnewyork.us/resource/tesw-yqqr.json"
        
        # Try searching by BIN first, then BBL
        search_params = []
        if bin_number:
            search_params.append({"buildingid": bin_number})
        if bbl:
            search_params.append({"bbl": bbl})
            
        for params in search_params:
            params["$limit"] = 10
            params["$order"] = "lastregistrationdate DESC"  # Get most recent registration
            
            logger.info(f"Checking HPD registration data with params: {params}")
            response = api_get(hpd_registration_url, params=params, timeout=15)
            
            if response and len(response) > 0:
                # Get the most recent registration
                registration = response[0]
                
                # Extract ownership information
                owner_name = None
                owner_contact = None
                
                # Try different owner fields
                owner_fields = ['ownername', 'owner_name', 'businessname', 'business_name']
                for field in owner_fields:
                    if field in registration and registration[field]:
                        owner_name = registration[field].strip()
                        break
                
                # Extract contact information
                contact_parts = []
                if registration.get('owneraddress'):
                    contact_parts.append(registration['owneraddress'].strip())
                if registration.get('ownercity'):
                    contact_parts.append(registration['ownercity'].strip())
                if registration.get('ownerstate'):
                    contact_parts.append(registration['ownerstate'].strip())
                if registration.get('ownerzip'):
                    contact_parts.append(registration['ownerzip'].strip())
                    
                owner_contact = ", ".join(contact_parts) if contact_parts else None
                
                # Extract registration details
                registration_info = {
                    "registration_date": registration.get('lastregistrationdate'),
                    "contact_description": registration.get('contactdescription'),
                    "management_company": registration.get('managementcompany'),
                    "registration_id": registration.get('registrationid')
                }
                
                if owner_name or owner_contact:
                    logger.info(f"Found ownership info from HPD registration: {owner_name}")
                    return {
                        "owner_name": owner_name,
                        "owner_contact": owner_contact,
                        "registration_info": registration_info
                    }
        
        # Method 2: PLUTO data for basic ownership (fallback)
        # MapPLUTO contains owner information from Department of Finance
        pluto_url = "https://data.cityofnewyork.us/resource/64uk-42ks.json"  # MapPLUTO
        
        if bbl:
            params = {
                "bbl": bbl,
                "$limit": 1
            }
            
            logger.info(f"Checking PLUTO data for BBL {bbl}")
            response = api_get(pluto_url, params=params, timeout=15)
            
            if response and len(response) > 0:
                pluto_data = response[0]
                
                owner_name = pluto_data.get('ownername')
                
                # Extract address from PLUTO if available
                address_parts = []
                if pluto_data.get('address'):
                    address_parts.append(pluto_data['address'].strip())
                    
                owner_contact = ", ".join(address_parts) if address_parts else None
                
                if owner_name:
                    logger.info(f"Found ownership info from PLUTO: {owner_name}")
                    return {
                        "owner_name": owner_name.strip(),
                        "owner_contact": owner_contact,
                        "registration_info": {
                            "source": "PLUTO",
                            "year_built": pluto_data.get('yearbuilt'),
                            "building_class": pluto_data.get('bldgclass')
                        }
                    }
        
        logger.info(f"No ownership information found for BBL {bbl}, BIN {bin_number}")
        return {
            "owner_name": None,
            "owner_contact": None,
            "registration_info": None
        }
        
    except Exception as e:
        logger.error(f"Error getting ownership info for BBL {bbl}, BIN {bin_number}: {e}")
        return {
            "owner_name": None,
            "owner_contact": None,
            "registration_info": None
        }


def get_rent_stabilized_data_from_csv(bbl):
    """
    Get rent-stabilized unit count from NYCDB CSV data (2018 and 2023 data).
    
    This uses the NYCDB rent stabilization data which contains 2018-2023 
    rent stabilized unit counts from NYC tax bills.
    
    Args:
        bbl: Borough-Block-Lot number
        
    Returns:
        dict: {
            "units_count_2023": int or None,
            "units_count_2018": int or None,
            "found": bool, 
            "details": str
        }
    """
    if not bbl:
        return {
            "units_count_2023": None,
            "units_count_2018": None,
            "found": False,
            "details": "No BBL provided"
        }
        
    try:
        from django.conf import settings
        import csv
        import os
        
        csv_path = os.path.join(settings.BASE_DIR, "myproject/nycapi/management/data/rentstab_data_scraped.csv")
        
        if not os.path.exists(csv_path):
            logger.warning(f"CSV file not found at {csv_path}")
            return {
                "units_count_2023": None,
                "units_count_2018": None,
                "found": False,
                "details": "CSV data file not found"
            }
        
        logger.info(f"Checking NYCDB CSV data for BBL {bbl}")
        
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                if row.get('ucbbl') == str(bbl):
                    # Found the building! Extract both 2023 and 2018 unit counts
                    units_2023_str = row.get('uc2023', '').strip()
                    units_2018_str = row.get('uc2018', '').strip()
                    
                    units_2023 = None
                    units_2018 = None
                    
                    # Parse 2023 data
                    if units_2023_str and units_2023_str.upper() != 'NA':
                        try:
                            units_2023 = int(units_2023_str)
                            if units_2023 <= 0:
                                units_2023 = None
                        except (ValueError, TypeError):
                            units_2023 = None
                    
                    # Parse 2018 data
                    if units_2018_str and units_2018_str.upper() != 'NA':
                        try:
                            units_2018 = int(units_2018_str)
                            if units_2018 <= 0:
                                units_2018 = None
                        except (ValueError, TypeError):
                            units_2018 = None
                    
                    # Determine if we found valid data
                    if units_2023 or units_2018:
                        logger.info(f"Found rent-stabilized data for BBL {bbl}: 2023={units_2023}, 2018={units_2018}")
                        return {
                            "units_count_2023": units_2023,
                            "units_count_2018": units_2018,
                            "found": True,
                            "details": f"NYCDB data: {units_2023 or 0} units (2023), {units_2018 or 0} units (2018)"
                        }
                    else:
                        # Building found but no valid rent stabilized data
                        return {
                            "units_count_2023": None,
                            "units_count_2018": None,
                            "found": True,
                            "details": "Building found but no rent-stabilized units in available years"
                        }
            
            logger.info(f"BBL {bbl} not found in NYCDB CSV data")
            return {
                "units_count_2023": None,
                "units_count_2018": None,
                "found": False,
                "details": "Building not found in NYCDB data"
            }
        
    except Exception as e:
        logger.error(f"Error reading NYCDB CSV data for BBL {bbl}: {e}")
        return {
            "units_count_2023": None,
            "units_count_2018": None,
            "found": False,
            "details": f"Error reading CSV: {str(e)}"
        }

















def building_lookup_view(request):
    address  = request.GET.get("address", "").strip()
    zip_code = request.GET.get("zip_code", "").strip()
    if not address or not zip_code:
        return JsonResponse({"success": False, "error": "Address and ZIP code are required."})

    bin_number, bbl = get_building_id(address, zip_code)
    
    if not bin_number and not bbl:
        return JsonResponse({
            "success": False, 
            "error": "Unable to find building data for this address. Please verify the address and zip code."
        })

    # Log the retrieved identifiers for debugging
    logger.info(f"Found Building ID: {bin_number}, BBL: {bbl} for {address}, {zip_code}")

    violations, hpd_total = get_hpd_violations(bin_number)
    logger.info(f"HPD Violations: Found {hpd_total} violations, returned {len(violations)} results")
    time.sleep(0.5)  # Small delay to avoid rate limiting
    
    complaints, complaints_total = get_311_complaints(bbl)
    logger.info(f"311 Complaints: Found {complaints_total} complaints, returned {len(complaints)} results")
    time.sleep(0.5)
    
    bedbugs, bedbugs_total = get_bedbug_reports(bin_number)
    logger.info(f"Bedbug Reports: Found {bedbugs_total} reports, returned {len(bedbugs)} results")
    time.sleep(0.5)
    
    housing_lits, housing_total = get_housing_litigation(bin_number)
    logger.info(f"Housing Litigation: Found {housing_total} cases, returned {len(housing_lits)} results")
    time.sleep(0.5)
    
    lead_paint, lead_paint_total = get_lead_paint_violations(bin_number)
    logger.info(f"Lead Paint Violations: Found {lead_paint_total} violations, returned {len(lead_paint)} results")

    # Check if we got any data at all
    total_records = hpd_total + complaints_total + bedbugs_total + housing_total + lead_paint_total
    
    result = {
        "address": address,
        "zip_code": zip_code,
        "building_id": bin_number,
        "bbl": bbl,
        "hpd_violations": violations,
        "hpd_violations_total_count": hpd_total,
        "complaints": complaints,
        "complaints_total_count": complaints_total,
        "bedbug_reports": bedbugs,
        "bedbug_reports_total_count": bedbugs_total,
        "litigation": housing_lits,
        "litigation_total_count": housing_total,
        "lead_paint_violations": lead_paint,
        "lead_paint_violations_total_count": lead_paint_total,
        "api_status": "partial" if total_records == 0 else "ok"
    }
    
    if total_records == 0:
        logger.warning(f"No data returned for {address}, {zip_code} - APIs may be down")
    
    # Add rent stabilization information using taxbills.nyc comprehensive data
    stabilization_info = get_rent_stabilization_info(bbl, address, zip_code)
    
    # Log detailed info for debugging
    logger.info(f"Rent stabilization lookup for {address}, BBL {bbl}: {stabilization_info}")
    
    # Add ownership information using JustFix methodology
    ownership_info = get_ownership_info(bbl, bin_number)
    logger.info(f"Ownership lookup for {address}, BBL {bbl}: {ownership_info}")
    time.sleep(0.5)  # Small delay to avoid rate limiting
    
    # Include rent stabilization data in result (single-tier NYCDB approach)
    result["has_rent_stabilized"] = stabilization_info["has_rent_stabilized"]
    result["rent_stabilized_units_2023"] = stabilization_info["units_count_2023"] or 0
    result["rent_stabilized_units_2018"] = stabilization_info["units_count_2018"] or 0
    result["rent_stabilized_units_difference"] = stabilization_info["units_difference"]
    result["stabilization_source"] = stabilization_info["source"]
    result["stabilization_details"] = stabilization_info["details"]
    result["stabilization_reason"] = stabilization_info["official_reason"]
    
    # For backward compatibility, keep the original field but use 2023 data as primary
    result["rent_stabilized_units"] = stabilization_info["units_count_2023"] or 0
    
    # Include ownership data in result
    result["owner_name"] = ownership_info["owner_name"]
    result["owner_contact"] = ownership_info["owner_contact"]
    result["registration_info"] = ownership_info["registration_info"]
    
    return JsonResponse({"success": True, "data": result})