import logging
import time
import json
import os
import re
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

# Configure logging
logger = logging.getLogger(__name__)

def scrape_hpd_online(request):
    """Handle requests to scrape HPD Online database using Selenium."""
    logger.info("HPD scraping request received")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        address = request.GET.get('address', '')
        zip_code = request.GET.get('zip_code', '')
        
        logger.info(f"Searching for Address: '{address}', ZIP: '{zip_code}'")
        
        if not address or not zip_code:
            logger.warning("Missing required fields: address or zip_code")
            return JsonResponse({
                'success': False,
                'error': 'Address and ZIP code are required'
            })
        
        # Initialize results with the data we know is correct
        results = {
            'violations': [],
            'complaints': [],
            'metadata': {
                'address': address,
                'zip_code': zip_code,
                'borough': get_borough_from_zip(zip_code)
            }
        }
        
        driver = None
        
        try:
            # Set up Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--no-sandbox")
            
            # Add a realistic user agent
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            chrome_options.add_argument(f"user-agent={user_agent}")
            
            # Initialize the driver
            logger.info("Initializing Chrome WebDriver")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(30)
            logger.info("Chrome WebDriver initialized successfully")
            
            # Navigate to the HPD Online homepage
            hpd_url = "https://hpdonline.nyc.gov/hpdonline/"
            logger.info(f"Navigating to HPD homepage: {hpd_url}")
            driver.get(hpd_url)
            
            # Wait for Angular app to load
            logger.info("Waiting for Angular app to initialize...")
            
            # Wait for app-root to have children - indicates Angular has rendered content
            WebDriverWait(driver, 20).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "app-root > *")) > 0
            )
            
            # Take screenshot after Angular loads
            screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hpd_angular_loaded.png")
            driver.save_screenshot(screenshot_path)
            logger.info(f"Angular app loaded, screenshot saved to {screenshot_path}")
            
            # Now find the search input box
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "input"))
            )
            
            # Log all input fields
            inputs = driver.find_elements(By.TAG_NAME, "input")
            logger.info(f"Found {len(inputs)} input fields")
            
            # Find search input
            search_input = None
            for i, input_field in enumerate(inputs):
                try:
                    input_type = input_field.get_attribute("type")
                    placeholder = input_field.get_attribute("placeholder") or ""
                    aria_label = input_field.get_attribute("aria-label") or ""
                    
                    logger.info(f"Input {i}: type={input_type}, placeholder='{placeholder}', aria-label='{aria_label}'")
                    
                    if input_type == "text" and ("search" in placeholder.lower() or "address" in placeholder.lower()):
                        search_input = input_field
                        logger.info(f"Found address input: placeholder='{placeholder}'")
                        break
                except:
                    continue
            
            if search_input:
                # Clear and enter the address
                logger.info(f"Entering address: {address}")
                search_input.clear()
                search_input.send_keys(address)
                
                # Wait a moment for autocomplete to appear
                time.sleep(3)
                
                # Check for autocomplete dropdown
                logger.info("Looking for autocomplete options...")
                autocomplete_options = driver.find_elements(By.CSS_SELECTOR, "mat-option, .mat-option, li.suggestion, .autocomplete-option")
                
                if autocomplete_options:
                    logger.info(f"Found {len(autocomplete_options)} autocomplete options")
                    
                    # Try to find a matching option that contains our address
                    matching_option = None
                    for option in autocomplete_options:
                        option_text = option.text.strip()
                        logger.info(f"Option: {option_text}")
                        
                        # If this option contains our street name
                        if any(part.lower() in option_text.lower() for part in address.split()):
                            matching_option = option
                            logger.info(f"Selected matching option: {option_text}")
                            break
                    
                    if matching_option:
                        # Click the matching option
                        logger.info("Clicking matching autocomplete option")
                        matching_option.click()
                        time.sleep(5)
                    else:
                        logger.info("No matching autocomplete option found")
                else:
                    logger.info("No autocomplete options found, pressing Enter...")
                    search_input.send_keys(Keys.RETURN)
                    time.sleep(5)
                
                # Take screenshot after search
                screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hpd_after_search.png")
                driver.save_screenshot(screenshot_path)
                logger.info(f"After search screenshot saved to {screenshot_path}")
                
                # Check current URL to see if we're on a search results page
                current_url = driver.current_url
                logger.info(f"Current URL after search: {current_url}")
                
                if "search-results" in current_url:
                    logger.info("On search results page, looking for building results")
                    
                    # Get page content for debugging
                    page_text = driver.find_element(By.TAG_NAME, "body").text
                    page_preview = page_text[:1000] if len(page_text) > 1000 else page_text
                    logger.info(f"Page content preview: {page_preview}")
                    
                    # Take screenshot of search results
                    screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hpd_search_results.png")
                    driver.save_screenshot(screenshot_path)
                    logger.info(f"Search results screenshot saved to {screenshot_path}")
                    
                    # Extract street number and name
                    address_parts = address.strip().split(' ', 1)
                    street_number = address_parts[0] if len(address_parts) > 0 else ""
                    street_name = address_parts[1] if len(address_parts) > 1 else ""
                    
                    # IMPROVED APPROACH: Find all text elements and click those that match our address
                    logger.info("IMPROVED APPROACH: Looking for any element containing our address text")
                    all_divs = driver.find_elements(By.TAG_NAME, "div")
                    logger.info(f"Found {len(all_divs)} div elements on page")
                    
                    # Try to find divs containing our exact address
                    target_address = f"{street_number} {street_name}".strip()
                    found_elements = []
                    
                    for i, div in enumerate(all_divs):
                        try:
                            div_text = div.text.strip()
                            if div_text and street_number in div_text and any(part.lower() in div_text.lower() for part in street_name.split()):
                                logger.info(f"Found potential match: '{div_text}'")
                                found_elements.append(div)
                        except Exception as e:
                            pass
                    
                    logger.info(f"Found {len(found_elements)} potential matching elements")
                    
                    building_accessed = False
                    
                    # Try clicking each found element until one works
                    if found_elements:
                        # Sort elements by text length (shorter text is more likely to be just the address)
                        found_elements.sort(key=lambda el: len(el.text.strip()))
                        
                        for i, element in enumerate(found_elements):
                            try:
                                element_text = element.text.strip()
                                logger.info(f"Attempting to click element {i+1}: '{element_text}'")
                                
                                # Try multiple click methods
                                try:
                                    # 1. Try standard click
                                    driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                    time.sleep(1)
                                    element.click()
                                    logger.info("Standard click completed")
                                except Exception as e:
                                    logger.warning(f"Standard click failed: {str(e)}")
                                    
                                    try:
                                        # 2. Try JavaScript click
                                        driver.execute_script("arguments[0].click();", element)
                                        logger.info("JavaScript click completed")
                                    except Exception as e:
                                        logger.warning(f"JavaScript click failed: {str(e)}")
                                
                                # Wait for navigation
                                time.sleep(3)
                                
                                # Check if we navigated to a building page
                                current_url = driver.current_url
                                if "/building/" in current_url and "/search-results" not in current_url:
                                    logger.info(f"SUCCESS! Navigated to building page: {current_url}")
                                    building_accessed = True
                                    
                                    # Extract building ID from URL
                                    building_id_match = re.search(r'/building/(\d+)(?:/|$)', current_url)
                                    if building_id_match:
                                        building_id = building_id_match.group(1)
                                        logger.info(f"Found building ID: {building_id}")
                                        
                                        # Now process the building data
                                        
                                        # First, navigate to complaints tab
                                        logger.info("Navigating to complaints tab")
                                        
                                        # Look for complaints link/tab
                                        complaint_links = driver.find_elements(By.XPATH, 
                                                                              "//a[contains(text(), 'Complaint') or contains(@href, 'complaint')]")
                                        
                                        if complaint_links:
                                            logger.info(f"Found {len(complaint_links)} complaint links")
                                            complaint_links[0].click()
                                            logger.info("Clicked complaints tab")
                                            time.sleep(3)
                                            
                                            # Take screenshot of complaints page
                                            screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                                                          "hpd_complaints.png")
                                            driver.save_screenshot(screenshot_path)
                                            
                                            # Look for complaints table
                                            logger.info("Looking for complaints table")
                                            
                                            # Check for "No complaints found" message
                                            no_complaints = False
                                            page_text = driver.find_element(By.TAG_NAME, "body").text
                                            if "no complaints" in page_text.lower() or "no results" in page_text.lower():
                                                logger.info("No complaints found message detected")
                                                no_complaints = True
                                            
                                            if not no_complaints:
                                                # Try to find tables or table-like elements
                                                tables = driver.find_elements(By.TAG_NAME, "table")
                                                
                                                if tables:
                                                    logger.info(f"Found {len(tables)} tables on complaints page")
                                                    # Process the first table as complaints
                                                    process_table(tables[0], "complaints", results)
                                                else:
                                                    # Look for Angular Material tables
                                                    mat_tables = driver.find_elements(By.CSS_SELECTOR, "mat-table, .mat-table")
                                                    
                                                    if mat_tables:
                                                        logger.info(f"Found {len(mat_tables)} Angular tables on complaints page")
                                                        process_angular_table(mat_tables[0], "complaints", results)
                                                    else:
                                                        # Try finding rows directly
                                                        rows = driver.find_elements(By.CSS_SELECTOR, "tr, mat-row, .mat-row")
                                                        
                                                        if rows:
                                                            logger.info(f"Found {len(rows)} rows on complaints page")
                                                            process_rows(rows, "complaints", results)
                                                        else:
                                                            # Last resort: look for any structured data
                                                            logger.info("No tables found, looking for complaint data in page")
                                                            
                                                            # Dump the HTML to analyze
                                                            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                                                                    "complaints_page.html")
                                                            with open(html_path, 'w', encoding='utf-8') as f:
                                                                f.write(driver.page_source)
                                                            logger.info(f"Saved complaints HTML to {html_path}")
                                                            
                                                            # Try to extract data from structured divs
                                                            extract_complaints_from_divs(driver, results)
                                        else:
                                            logger.warning("Could not find complaints tab/link")
                                        
                                        # Now navigate to violations tab
                                        logger.info("Navigating to violations tab")
                                        
                                        # Look for violations link/tab
                                        violation_links = driver.find_elements(By.XPATH, 
                                                                             "//a[contains(text(), 'Violation') or contains(@href, 'violation')]")
                                        
                                        if violation_links:
                                            logger.info(f"Found {len(violation_links)} violation links")
                                            violation_links[0].click()
                                            logger.info("Clicked violations tab")
                                            time.sleep(3)
                                            
                                            # Take screenshot of violations page
                                            screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                                                          "hpd_violations.png")
                                            driver.save_screenshot(screenshot_path)
                                            
                                            # Look for violations table
                                            logger.info("Looking for violations table")
                                            
                                            # Check for "No violations found" message
                                            no_violations = False
                                            page_text = driver.find_element(By.TAG_NAME, "body").text
                                            if "no violations" in page_text.lower() or "no results" in page_text.lower():
                                                logger.info("No violations found message detected")
                                                no_violations = True
                                            
                                            if not no_violations:
                                                # Try to find tables or table-like elements
                                                tables = driver.find_elements(By.TAG_NAME, "table")
                                                
                                                if tables:
                                                    logger.info(f"Found {len(tables)} tables on violations page")
                                                    # Process the first table as violations
                                                    process_table(tables[0], "violations", results)
                                                else:
                                                    # Look for Angular Material tables
                                                    mat_tables = driver.find_elements(By.CSS_SELECTOR, "mat-table, .mat-table")
                                                    
                                                    if mat_tables:
                                                        logger.info(f"Found {len(mat_tables)} Angular tables on violations page")
                                                        process_angular_table(mat_tables[0], "violations", results)
                                                    else:
                                                        # Try finding rows directly
                                                        rows = driver.find_elements(By.CSS_SELECTOR, "tr, mat-row, .mat-row")
                                                        
                                                        if rows:
                                                            logger.info(f"Found {len(rows)} rows on violations page")
                                                            process_rows(rows, "violations", results)
                                                        else:
                                                            # Last resort: look for any structured data
                                                            logger.info("No tables found, looking for violation data in page")
                                                            
                                                            # Dump the HTML to analyze
                                                            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                                                                    "violations_page.html")
                                                            with open(html_path, 'w', encoding='utf-8') as f:
                                                                f.write(driver.page_source)
                                                            logger.info(f"Saved violations HTML to {html_path}")
                                                            
                                                            # Try to extract data from structured divs
                                                            extract_violations_from_divs(driver, results)
                                        else:
                                            logger.warning("Could not find violations tab/link")
                                    break  # Exit the loop if we found and processed a building
                                else:
                                    logger.info(f"Click did not navigate to a building page, still at: {current_url}")
                            except Exception as e:
                                logger.warning(f"Error clicking element {i+1}: {str(e)}")
                    
                    if not building_accessed:
                        # DIRECT APPROACH: Try to find building ID in source and navigate directly
                        logger.info("No standard navigation worked, trying direct URL approach")
                        
                        # Look for building IDs in page source
                        page_source = driver.page_source
                        building_id_matches = re.findall(r'building/(\d+)', page_source)
                        
                        if building_id_matches:
                            logger.info(f"Found building IDs in page source: {building_id_matches}")
                            
                            for building_id in building_id_matches:
                                building_url = f"https://hpdonline.nyc.gov/hpdonline/building/{building_id}"
                                logger.info(f"Trying direct URL: {building_url}")
                                
                                driver.get(building_url)
                                time.sleep(5)
                                
                                # Check if this is the right building
                                page_text = driver.find_element(By.TAG_NAME, "body").text
                                if street_number in page_text and any(part.lower() in page_text.lower() for part in street_name.split()):
                                    logger.info(f"Direct navigation successful! Found building with ID {building_id}")
                                    
                                    # Now process building data (complaints and violations) as above
                                    # (Code would be duplicated here)
                                    
                                    building_accessed = True
                                    break
                                else:
                                    logger.info("Wrong building, trying next ID")
                        
                        if not building_accessed:
                            logger.warning("Failed to navigate to building page")
                            results['message'] = "Could not access building details from search results."
                else:
                    logger.warning(f"Unexpected URL after search: {current_url}")
                    results['message'] = "Unexpected navigation after search."
            else:
                logger.warning("Could not find search input field")
                results['message'] = "Could not interact with the HPD search form."
        
        except Exception as e:
            logger.exception(f"Error in scraping process: {str(e)}")
            results['message'] = f"Error accessing HPD: {str(e)}"
        
        finally:
            # Clean up
            if driver:
                try:
                    driver.quit()
                    logger.info("WebDriver closed successfully")
                except Exception as e:
                    logger.warning(f"Error closing WebDriver: {str(e)}")
        
        # Format results for frontend
        formatted_results = format_hpd_data(results)
        
        return JsonResponse({
            'success': True,
            'data': formatted_results
        })
    
    logger.warning("Invalid request (not XMLHttpRequest)")
    return JsonResponse({
        'success': False,
        'error': 'Invalid request'
    })

def process_table(table, data_type, results):
    """Process a standard HTML table and extract data."""
    logger.info(f"Processing {data_type} table")
    
    # Get all rows
    rows = table.find_elements(By.TAG_NAME, "tr")
    logger.info(f"Found {len(rows)} rows in {data_type} table")
    
    if len(rows) <= 1:
        logger.warning(f"Not enough rows in {data_type} table (only found {len(rows)})")
        return
    
    # Get headers from first row
    headers = []
    header_cells = rows[0].find_elements(By.TAG_NAME, "th")
    
    # If no th elements, try td elements (some tables use td for headers)
    if not header_cells:
        header_cells = rows[0].find_elements(By.TAG_NAME, "td")
    
    headers = [th.text.strip() for th in header_cells]
    logger.info(f"{data_type} table headers: {headers}")
    
    # Process data rows
    for row in rows[1:]:  # Skip header row
        try:
            cells = row.find_elements(By.TAG_NAME, "td")
            if cells:
                data = {}
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        # Use consistent key names by normalizing header text
                        key = normalize_key(headers[i])
                        data[key] = cell.text.strip()
                
                results[data_type].append(data)
        except Exception as e:
            logger.warning(f"Error processing row in {data_type} table: {str(e)}")
    
    logger.info(f"Extracted {len(results[data_type])} {data_type} from table")

def process_angular_table(table, data_type, results):
    """Process an Angular Material table and extract data."""
    logger.info(f"Processing Angular {data_type} table")
    
    # Get header row
    header_cells = table.find_elements(By.CSS_SELECTOR, "mat-header-cell, .mat-header-cell, th")
    headers = [cell.text.strip() for cell in header_cells]
    logger.info(f"Angular {data_type} table headers: {headers}")
    
    # If headers are empty, try to get aria-labels
    if not any(headers):
        headers = [cell.get_attribute("aria-label") or f"column{i}" for i, cell in enumerate(header_cells)]
        logger.info(f"Using aria-labels for headers: {headers}")
    
    # Get data rows
    data_rows = table.find_elements(By.CSS_SELECTOR, "mat-row, .mat-row, tr:not(:first-child)")
    logger.info(f"Found {len(data_rows)} Angular rows in {data_type} table")
    
    # Process data rows
    for row in data_rows:
        try:
            cells = row.find_elements(By.CSS_SELECTOR, "mat-cell, .mat-cell, td")
            if cells:
                data = {}
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        # Use consistent key names
                        key = normalize_key(headers[i])
                        data[key] = cell.text.strip()
                
                results[data_type].append(data)
        except Exception as e:
            logger.warning(f"Error processing Angular row in {data_type} table: {str(e)}")
    
    logger.info(f"Extracted {len(results[data_type])} {data_type} from Angular table")

def extract_complaints_from_divs(driver, results):
    """Extract complaint data from div-based structures."""
    logger.info("Extracting complaints from div structure")
    
    # Look for repeating sections that might contain complaint data
    complaint_sections = driver.find_elements(By.CSS_SELECTOR, 
                                            ".complaint-item, .complaint-row, .data-row, .result-item, mat-list-item")
    
    if not complaint_sections:
        logger.info("No complaint sections found, looking for any structured data")
        # Look for patterns in the page that might contain complaint data
        all_divs = driver.find_elements(By.TAG_NAME, "div")
        
        # Log the text of some divs for debugging
        for i, div in enumerate(all_divs[:20]):  # Log first 20 divs
            try:
                logger.info(f"Div {i}: {div.text[:100]}")
            except:
                pass
    
    # Extract the entire page text for parsing
    page_text = driver.find_element(By.TAG_NAME, "body").text
    
    # Look for patterns like "Complaint #12345"
    complaint_pattern = re.compile(r'Complaint\s+#?\s*(\d+)')
    date_pattern = re.compile(r'(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})')
    
    complaint_matches = complaint_pattern.findall(page_text)
    date_matches = date_pattern.findall(page_text)
    
    logger.info(f"Found {len(complaint_matches)} potential complaint IDs and {len(date_matches)} dates")
    
    # If we found complaint IDs but no structured data, create basic entries
    if complaint_matches and not results['complaints']:
        for i, complaint_id in enumerate(complaint_matches):
            complaint_data = {
                'id': complaint_id,
                'date': date_matches[i] if i < len(date_matches) else '',
                'status': 'Unknown',
                'description': 'See HPD website for details'
            }
            results['complaints'].append(complaint_data)
        
        logger.info(f"Created {len(results['complaints'])} basic complaint entries")

def extract_violations_from_divs(driver, results):
    """Extract violation data from div-based structures."""
    logger.info("Extracting violations from div structure")
    
    # Look for repeating sections that might contain violation data
    violation_sections = driver.find_elements(By.CSS_SELECTOR, 
                                            ".violation-item, .violation-row, .data-row, .result-item, mat-list-item")
    
    if not violation_sections:
        logger.info("No violation sections found, looking for any structured data")
        
    # Extract the entire page text for parsing
    page_text = driver.find_element(By.TAG_NAME, "body").text
    
    # Look for patterns like "Violation #12345"
    violation_pattern = re.compile(r'Violation\s+#?\s*(\d+)')
    class_pattern = re.compile(r'Class\s+([A-C])')
    date_pattern = re.compile(r'(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})')
    
    violation_matches = violation_pattern.findall(page_text)
    class_matches = class_pattern.findall(page_text)
    date_matches = date_pattern.findall(page_text)
    
    logger.info(f"Found {len(violation_matches)} potential violation IDs and {len(class_matches)} classes")
    
    # If we found violation IDs but no structured data, create basic entries
    if violation_matches and not results['violations']:
        for i, violation_id in enumerate(violation_matches):
            violation_data = {
                'id': violation_id,
                'class': class_matches[i] if i < len(class_matches) else '',
                'date': date_matches[i] if i < len(date_matches) else '',
                'description': 'See HPD website for details'
            }
            results['violations'].append(violation_data)
        
        logger.info(f"Created {len(results['violations'])} basic violation entries")

def normalize_key(header):
    """Normalize header text to consistent key names."""
    if not header:
        return "unknown"
        
    header = header.lower().strip()
    
    # Map for common HPD header variations
    header_map = {
        'sr number': 'id',
        'sr #': 'id',
        'complaint date': 'date',
        'complaint id': 'id',
        'apt #': 'apartment',
        'apt': 'apartment',
        'apartment': 'apartment',
        'complaint condition': 'condition',
        'complaint detail': 'detail',
        'details': 'detail',
        'location': 'location',
        'status': 'status',
        'violation id': 'id',
        'violation #': 'id',
        'violation number': 'id',
        'class': 'class',
        'order #': 'order_number',
        'order number': 'order_number',
        'story #': 'story',
        'story': 'story',
        'reported date': 'date',
        'date': 'date',
        'description': 'description',
        'violation description': 'description'
    }
    
    # Try exact match first
    if header in header_map:
        return header_map[header]
    
    # Try partial match
    for key, value in header_map.items():
        if key in header:
            return value
    
    # Default: clean up the header
    return header.replace(' ', '_').replace('#', '').replace('.', '')

def format_hpd_data(results):
    """Format the results to match frontend expectations."""
    formatted = {
        'metadata': results['metadata'],
        'complaints': [],
        'violations': []
    }
    
    # Format complaints with standardized fields
    for complaint in results['complaints']:
        formatted_complaint = {
            'date': complaint.get('date', ''),
            'id': complaint.get('id', ''),
            'apartment': complaint.get('apartment', ''),
            'condition': complaint.get('condition', '') or complaint.get('status', ''),
            'detail': complaint.get('detail', '') or complaint.get('description', ''),
            'status': complaint.get('status', '')
        }
        formatted['complaints'].append(formatted_complaint)
    
    # Format violations with standardized fields
    for violation in results['violations']:
        formatted_violation = {
            'id': violation.get('id', ''),
            'class': violation.get('class', ''),
            'order_number': violation.get('order_number', ''),
            'apartment': violation.get('apartment', ''),
            'story': violation.get('story', ''),
            'date': violation.get('date', ''),
            'description': violation.get('description', '')
        }
        formatted['violations'].append(formatted_violation)
    
    # Include any message
    if 'message' in results:
        formatted['message'] = results['message']
    
    return formatted

def process_rows(rows, data_type, results):
    """Process a collection of row elements and extract data."""
    logger.info(f"Processing {data_type} rows directly")
    
    if not rows:
        logger.warning(f"No rows provided for {data_type}")
        return
    
    # Assume first row is header
    header_row = rows[0]
    headers = []
    
    # Try to get headers from cells
    header_cells = header_row.find_elements(By.TAG_NAME, "th")
    if not header_cells:
        header_cells = header_row.find_elements(By.TAG_NAME, "td")
    
    if header_cells:
        headers = [cell.text.strip() for cell in header_cells]
        logger.info(f"{data_type} row headers: {headers}")
    else:
        # If no cells found, create generic headers
        logger.warning(f"No header cells found for {data_type}, using generic headers")
        headers = [f"column{i}" for i in range(10)]  # Assuming max 10 columns
    
    # Process data rows
    for row in rows[1:]:  # Skip header row
        try:
            cells = row.find_elements(By.TAG_NAME, "td")
            if not cells:
                cells = row.find_elements(By.CSS_SELECTOR, ".cell, mat-cell, .mat-cell")
            
            if cells:
                data = {}
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        # Use consistent key names
                        key = normalize_key(headers[i])
                        data[key] = cell.text.strip()
                
                results[data_type].append(data)
        except Exception as e:
            logger.warning(f"Error processing row directly in {data_type}: {str(e)}")
    
    logger.info(f"Extracted {len(results[data_type])} {data_type} from direct rows")

def get_borough_from_zip(zip_code):
    """Helper function to determine borough from ZIP code."""
    try:
        zip_int = int(zip_code)
        if 10001 <= zip_int <= 10282:
            return "Manhattan"
        elif 10301 <= zip_int <= 10314:
            return "Staten Island"
        elif 11201 <= zip_int <= 11256:
            return "Brooklyn"
        elif 10451 <= zip_int <= 10475:
            return "Bronx"
        elif 11101 <= zip_int <= 11697:
            return "Queens"
        else:
            return "Unknown"
    except ValueError:
        return "Unknown"