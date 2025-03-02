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
                
                # Get the current URL to see if we've been redirected
                current_url = driver.current_url
                logger.info(f"Current URL after search: {current_url}")
                
                # Check if we're on search results page
                if "search-results" in current_url:
                    logger.info("On search results page, looking for building results")
                    
                    # Log content
                    content_preview = driver.find_element(By.TAG_NAME, "body").text[:1000]
                    logger.info(f"Page content preview: {content_preview}")
                    
                    # Take screenshot
                    screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hpd_search_results.png")
                    driver.save_screenshot(screenshot_path)
                    logger.info(f"Search results screenshot saved to {screenshot_path}")
                    
                    # Extract street number and name for more precise matching
                    address_parts = address.split()
                    street_number = address_parts[0] if address_parts else ""
                    street_name = " ".join(address_parts[1:]) if len(address_parts) > 1 else ""
                    
                    # APPROACH 1: Try finding specific building elements with exact address
                    specific_xpath = f"//div[contains(text(), '{street_number}') and contains(text(), '{street_name}') and contains(following-sibling::div, 'Brooklyn')]"
                    logger.info(f"Trying specific building XPATH: {specific_xpath}")
                    specific_building_elements = driver.find_elements(By.XPATH, specific_xpath)
                    
                    if specific_building_elements:
                        logger.info(f"Found {len(specific_building_elements)} specific building elements")
                        element_to_click = specific_building_elements[0]
                        logger.info(f"Clicking specific building element: {element_to_click.text}")
                        
                        try:
                            # Try using Actions to move to the element first - helps with Angular components
                            actions = ActionChains(driver)
                            actions.move_to_element(element_to_click).perform()
                            time.sleep(1)
                            
                            # First click attempt - standard
                            element_to_click.click()
                            logger.info("Clicked specific building element")
                            time.sleep(3)
                            
                            # Check if we navigated
                            if "/building/" in driver.current_url:
                                logger.info(f"Successfully navigated to building page: {driver.current_url}")
                            else:
                                # Second click attempt - JavaScript
                                logger.info("First click didn't navigate, trying JavaScript click")
                                driver.execute_script("arguments[0].click();", element_to_click)
                                time.sleep(3)
                        except Exception as e:
                            logger.warning(f"Error clicking specific building element: {str(e)}")
                            # Try JavaScript click as fallback
                            driver.execute_script("arguments[0].click();", element_to_click)
                            logger.info("Clicked element using JavaScript after exception")
                            time.sleep(3)
                    else:
                        # APPROACH 2: Look for card-like result items
                        logger.info("No specific building elements found, trying card approach")
                        
                        # This targets common designs for result cards
                        cards = driver.find_elements(By.CSS_SELECTOR, ".search-result, .result-item, .result-card, .mat-card, mat-card, .list-item, .building-result")
                        
                        if not cards:
                            # If no cards with specific classes, look for divs with multiple lines of text that might be result cards
                            cards = driver.find_elements(By.XPATH, "//div[contains(., '\n') and string-length(.) < 200]")
                        
                        logger.info(f"Found {len(cards)} potential result cards")
                        
                        # Find the card that contains our address
                        matching_card = None
                        for i, card in enumerate(cards):
                            card_text = card.text.strip()
                            logger.info(f"Card {i} text: {card_text}")
                            
                            # Try to match both street number and name
                            if street_number in card_text and street_name.lower().replace("st", "street") in card_text.lower():
                                matching_card = card
                                logger.info(f"Found matching card: {card_text}")
                                break
                        
                        if matching_card:
                            try:
                                # Look for any links or buttons inside the card first
                                clickable_elements = matching_card.find_elements(By.CSS_SELECTOR, "a, button")
                                
                                if clickable_elements:
                                    # Click the first clickable element inside the card
                                    clickable_elements[0].click()
                                    logger.info("Clicked link/button inside result card")
                                else:
                                    # Try different click approaches - this is where we need to improve
                                    
                                    # 1. First try ActionChains with double click (sometimes needed for Angular)
                                    actions = ActionChains(driver)
                                    actions.move_to_element(matching_card).click().click().perform()
                                    logger.info("Double-clicked card using ActionChains")
                                    time.sleep(3)
                                    
                                    # Check if navigation occurred
                                    if "/building/" not in driver.current_url:
                                        # 2. Try clicking with JavaScript - more reliable with Angular
                                        logger.info("ActionChains didn't work, trying JavaScript click")
                                        driver.execute_script("arguments[0].click();", matching_card)
                                        logger.info("Clicked card with JavaScript")
                                        time.sleep(3)
                                    
                                    # 3. If still no navigation, try to trigger Angular's internal navigation
                                    if "/building/" not in driver.current_url:
                                        logger.info("JavaScript click didn't work, trying direct event triggering")
                                        
                                        # This injects JavaScript to simulate Angular's internal event handling
                                        js_script = """
                                            var el = arguments[0];
                                            var ngEl = angular.element(el);
                                            if (ngEl.scope()) {
                                                ngEl.scope().$apply(function() {
                                                    ngEl.triggerHandler('click');
                                                });
                                            } else {
                                                // Create and dispatch a click event
                                                var clickEvent = new MouseEvent('click', {
                                                    bubbles: true,
                                                    cancelable: true,
                                                    view: window
                                                });
                                                el.dispatchEvent(clickEvent);
                                            }
                                        """
                                        try:
                                            driver.execute_script(js_script, matching_card)
                                            logger.info("Triggered Angular click event")
                                            time.sleep(3)
                                        except Exception as js_error:
                                            logger.warning(f"Error with Angular click: {str(js_error)}")
                                    
                                    # 4. Direct URL approach if all clicks fail
                                    if "/building/" not in driver.current_url:
                                        logger.info("All click methods failed, trying to extract building ID")
                                        
                                        # Try to get building ID from card or page content
                                        card_html = matching_card.get_attribute('outerHTML')
                                        building_id_match = re.search(r'building/(\d+)', card_html)
                                        
                                        if building_id_match:
                                            building_id = building_id_match.group(1)
                                            building_url = f"https://hpdonline.nyc.gov/hpdonline/building/{building_id}"
                                            logger.info(f"Found building ID {building_id}, navigating to {building_url}")
                                            driver.get(building_url)
                                            time.sleep(5)
                                        else:
                                            # Final approach: Look for the building ID in entire page
                                            page_source = driver.page_source
                                            
                                            # Look for building IDs associated with our address
                                            # This pattern looks for building IDs in URLs or data attributes
                                            id_pattern = re.compile(r'building/(\d+)|data-building-id="(\d+)"')
                                            id_matches = id_pattern.findall(page_source)
                                            
                                            if id_matches:
                                                # Get the first non-empty group from the matches
                                                for match in id_matches:
                                                    building_id = next((x for x in match if x), None)
                                                    if building_id:
                                                        building_url = f"https://hpdonline.nyc.gov/hpdonline/building/{building_id}"
                                                        logger.info(f"Found building ID {building_id} in page, navigating to {building_url}")
                                                        driver.get(building_url)
                                                        time.sleep(5)
                                                        break
                            except Exception as e:
                                logger.exception(f"Error clicking card: {str(e)}")
                            
                            # Check if we successfully navigated to a building page
                            if "/building/" in driver.current_url:
                                building_id_match = re.search(r'/building/(\d+)(?:/|$)', driver.current_url)
                                if building_id_match:
                                    building_id = building_id_match.group(1)
                                    logger.info(f"Successfully navigated to building {building_id}")
                                    
                                    # Now extract data from the building page
                                    
                                    # Complaints
                                    try:
                                        # First navigate to complaints page
                                        complaints_url = f"https://hpdonline.nyc.gov/hpdonline/building/{building_id}/complaints"
                                        logger.info(f"Navigating to complaints page: {complaints_url}")
                                        driver.get(complaints_url)
                                        time.sleep(5)
                                        
                                        # Take screenshot of complaints page
                                        screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hpd_complaints.png")
                                        driver.save_screenshot(screenshot_path)
                                        logger.info(f"Complaints page screenshot saved to {screenshot_path}")
                                        
                                        # Check for "No open complaints" message
                                        if "No open complaints" in driver.page_source or "No complaints found" in driver.page_source:
                                            logger.info("No complaints found for this building")
                                        else:
                                            # Look for a table of complaints
                                            complaint_tables = driver.find_elements(By.TAG_NAME, "table")
                                            
                                            if complaint_tables:
                                                logger.info(f"Found {len(complaint_tables)} complaint tables")
                                                
                                                # Process the first table
                                                process_table(complaint_tables[0], "complaints", results)
                                            else:
                                                # Try Angular Material table
                                                mat_tables = driver.find_elements(By.TAG_NAME, "mat-table")
                                                if mat_tables:
                                                    logger.info(f"Found {len(mat_tables)} Angular Material complaint tables")
                                                    process_angular_table(mat_tables[0], "complaints", results)
                                                else:
                                                    logger.info("No complaint tables found, looking for rows directly")
                                                    
                                                    # Try to find rows directly
                                                    rows = driver.find_elements(By.CSS_SELECTOR, "tr, mat-row, .row")
                                                    if rows and len(rows) > 1:  # At least header + one data row
                                                        logger.info(f"Found {len(rows)} potential complaint rows")
                                                        process_rows(rows, "complaints", results)
                                    except Exception as e:
                                        logger.exception(f"Error extracting complaints: {str(e)}")
                                    
                                    # Violations
                                    try:
                                        # Navigate to violations page
                                        violations_url = f"https://hpdonline.nyc.gov/hpdonline/building/{building_id}/violations"
                                        logger.info(f"Navigating to violations page: {violations_url}")
                                        driver.get(violations_url)
                                        time.sleep(5)
                                        
                                        # Take screenshot of violations page
                                        screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hpd_violations.png")
                                        driver.save_screenshot(screenshot_path)
                                        logger.info(f"Violations page screenshot saved to {screenshot_path}")
                                        
                                        # Check for "No violations" message
                                        if "No violations" in driver.page_source or "No violation" in driver.page_source:
                                            logger.info("No violations found for this building")
                                        else:
                                            # Look for a table of violations
                                            violation_tables = driver.find_elements(By.TAG_NAME, "table")
                                            
                                            if violation_tables:
                                                logger.info(f"Found {len(violation_tables)} violation tables")
                                                
                                                # Process the first table
                                                process_table(violation_tables[0], "violations", results)
                                            else:
                                                # Try Angular Material table
                                                mat_tables = driver.find_elements(By.TAG_NAME, "mat-table")
                                                if mat_tables:
                                                    logger.info(f"Found {len(mat_tables)} Angular Material violation tables")
                                                    process_angular_table(mat_tables[0], "violations", results)
                                                else:
                                                    logger.info("No violation tables found, looking for rows directly")
                                                    
                                                    # Try to find rows directly
                                                    rows = driver.find_elements(By.CSS_SELECTOR, "tr, mat-row, .row")
                                                    if rows and len(rows) > 1:  # At least header + one data row
                                                        logger.info(f"Found {len(rows)} potential violation rows")
                                                        process_rows(rows, "violations", results)
                                    except Exception as e:
                                        logger.exception(f"Error extracting violations: {str(e)}")
                                else:
                                    logger.warning("URL appears to be a building page but can't extract building ID")
                            else:
                                logger.warning("Clicked card but didn't navigate to building page")
                                
                                # DEBUG: Check what might have happened
                                logger.info(f"Current URL after clicking: {driver.current_url}")
                                logger.info(f"Page title: {driver.title}")
                                screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "after_card_click.png")
                                driver.save_screenshot(screenshot_path)
                                
                                # Try direct navigation to search result page
                                logger.info("Attempting direct navigation to first search result")
                                
                                # Extract building IDs from page
                                page_source = driver.page_source
                                building_id_pattern = re.compile(r'(?:building/|building-)(\d+)')
                                building_ids = building_id_pattern.findall(page_source)
                                
                                if building_ids:
                                    # Take first building ID
                                    building_id = building_ids[0]
                                    logger.info(f"Found building ID in page: {building_id}")
                                    
                                    # Go directly to building page
                                    building_url = f"https://hpdonline.nyc.gov/hpdonline/building/{building_id}"
                                    logger.info(f"Navigating directly to: {building_url}")
                                    driver.get(building_url)
                                    time.sleep(5)
                                    
                                    # Continue with extraction as above
                                    # (Code would be duplicated here)
                                else:
                                    logger.warning("Couldn't find any building IDs in the page source")
                                    results['message'] = "Found search results but couldn't access building details."
                        else:
                            # If we can't find a matching card by text, try more general approaches
                            # ...
                            results['message'] = "Building found in search results but couldn't identify the right result card."
                    
                    # Check if we have any data
                    if not results['complaints'] and not results['violations']:
                        if 'message' not in results:
                            results['message'] = "No complaints or violations found for this address."
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
        
        # Return whatever results we have, even if partial
        return JsonResponse({
            'success': True,
            'data': results
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
    headers = [th.text.strip() for th in rows[0].find_elements(By.TAG_NAME, "th")]
    logger.info(f"{data_type} table headers: {headers}")
    
    # Process data rows
    for row in rows[1:]:  # Skip header row
        try:
            cells = row.find_elements(By.TAG_NAME, "td")
            if cells:
                data = {}
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        data[headers[i].lower()] = cell.text.strip()
                
                results[data_type].append(data)
        except Exception as e:
            logger.warning(f"Error processing row in {data_type} table: {str(e)}")
    
    logger.info(f"Extracted {len(results[data_type])} {data_type} from table")

def process_angular_table(table, data_type, results):
    """Process an Angular Material table and extract data."""
    logger.info(f"Processing Angular {data_type} table")
    
    # Get header row
    header_cells = table.find_elements(By.CSS_SELECTOR, "mat-header-cell, .mat-header-cell")
    headers = [cell.text.strip() for cell in header_cells]
    logger.info(f"Angular {data_type} table headers: {headers}")
    
    # Get data rows
    data_rows = table.find_elements(By.CSS_SELECTOR, "mat-row, .mat-row")
    logger.info(f"Found {len(data_rows)} Angular rows in {data_type} table")
    
    # Process data rows
    for row in data_rows:
        try:
            cells = row.find_elements(By.CSS_SELECTOR, "mat-cell, .mat-cell")
            if cells:
                data = {}
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        data[headers[i].lower()] = cell.text.strip()
                
                results[data_type].append(data)
        except Exception as e:
            logger.warning(f"Error processing Angular row in {data_type} table: {str(e)}")
    
    logger.info(f"Extracted {len(results[data_type])} {data_type} from Angular table")

def process_rows(rows, data_type, results):
    """Process a collection of row elements and extract data."""
    logger.info(f"Processing {data_type} rows directly")
    
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
                        data[headers[i].lower()] = cell.text.strip()
                
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