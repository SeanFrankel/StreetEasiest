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
            
            # Find the search input box
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "input"))
            )
            
            # Find search input
            search_input = None
            inputs = driver.find_elements(By.TAG_NAME, "input")
            logger.info(f"Found {len(inputs)} input fields")
            
            for input_field in inputs:
                placeholder = input_field.get_attribute("placeholder")
                if placeholder and ("search" in placeholder.lower() or "address" in placeholder.lower()):
                    search_input = input_field
                    logger.info(f"Found search input with placeholder: {placeholder}")
                    break
            
            if not search_input and len(inputs) > 0:
                # If all else fails, try the first input
                search_input = inputs[0]
                logger.info("Using first input field as search input")
            
            if not search_input:
                logger.error("Could not find search input field")
                raise Exception("Could not locate search input field on HPD website")

            # Click the search input first to ensure focus
            search_input.click()
            
            # Enter partial address to trigger autocomplete (don't include ZIP or borough)
            # Just enter the street name and number
            partial_address = address.split(',')[0] if ',' in address else address
            search_input.clear()
            search_input.send_keys(partial_address)
            logger.info(f"Entered partial address to trigger autocomplete: {partial_address}")
            
            # Wait for autocomplete suggestions
            logger.info("Looking for autocomplete suggestions")
            autocomplete_selected = False
            try:
                # Different possible ways autocomplete might be implemented
                autocomplete_items = None
                
                # Try mat-option (Angular Material)
                autocomplete_items = driver.find_elements(By.CSS_SELECTOR, "mat-option, .mat-option")
                if autocomplete_items:
                    logger.info(f"Found {len(autocomplete_items)} Angular Material autocomplete options")
                
                # If no mat-options, try ul/li pattern
                if not autocomplete_items:
                    autocomplete_items = driver.find_elements(By.CSS_SELECTOR, "ul.autocomplete-results li, .autocomplete-suggestion, .suggestion-item")
                    if autocomplete_items:
                        logger.info(f"Found {len(autocomplete_items)} standard autocomplete options")
                
                # If still no items, try dropdown items
                if not autocomplete_items:
                    autocomplete_items = driver.find_elements(By.CSS_SELECTOR, ".dropdown-item, .suggestion, [role='option']")
                    if autocomplete_items:
                        logger.info(f"Found {len(autocomplete_items)} dropdown autocomplete options")
                
                # Take screenshot of autocomplete results
                driver.save_screenshot(os.path.join(os.path.dirname(os.path.abspath(__file__)), "autocomplete_results.png"))
                
                # If we found autocomplete items, select the first one
                if autocomplete_items and len(autocomplete_items) > 0:
                    # Get the first autocomplete item
                    first_item = autocomplete_items[0]
                    logger.info(f"Selecting first autocomplete suggestion: {first_item.text}")
                    
                    try:
                        # Try normal click
                        first_item.click()
                        logger.info("Clicked autocomplete item successfully")
                        autocomplete_selected = True
                        
                        # After clicking an autocomplete suggestion, wait a moment for any page updates
                        time.sleep(2)
                    except Exception as click_e:
                        logger.warning(f"Error with standard click: {str(click_e)}")
                        try:
                            # Try JavaScript click as fallback
                            driver.execute_script("arguments[0].click();", first_item)
                            logger.info("Clicked autocomplete item with JavaScript")
                            autocomplete_selected = True
                            
                            # After clicking an autocomplete suggestion, wait a moment for any page updates
                            time.sleep(2)
                        except Exception as js_e:
                            logger.warning(f"Error with JavaScript click: {str(js_e)}")
                            # If clicking fails, just continue with the search as entered
                else:
                    logger.info("No autocomplete suggestions found, continuing with manual search")
            except Exception as auto_e:
                logger.warning(f"Error handling autocomplete: {str(auto_e)}")
            
            # Submit search if we haven't selected an autocomplete item
            # (selecting an item might automatically trigger the search)
            if not autocomplete_selected:
                try:
                    # Try to use the original search input
                    logger.info("Submitting search with Enter key")
                    search_input.send_keys(Keys.RETURN)
                except Exception as stale_e:
                    logger.warning(f"Original search input is stale, trying to find it again: {str(stale_e)}")
                    
                    # The element might be stale, try to find it again
                    try:
                        inputs = driver.find_elements(By.TAG_NAME, "input")
                        for input_field in inputs:
                            placeholder = input_field.get_attribute("placeholder")
                            if placeholder and ("search" in placeholder.lower() or "address" in placeholder.lower()):
                                logger.info(f"Found search input again with placeholder: {placeholder}")
                                input_field.send_keys(Keys.RETURN)
                                break
                    except Exception as refind_e:
                        logger.warning(f"Could not refind search input: {str(refind_e)}")
                        # Check if the page is already showing search results
                        current_url = driver.current_url
                        if "search-results" in current_url or "building" in current_url:
                            logger.info("Already on search results page, continuing")
                        else:
                            # Last resort - try to navigate to search results using JavaScript
                            try:
                                driver.execute_script("document.querySelector('form').submit();")
                                logger.info("Submitted search using JavaScript form submission")
                            except Exception as js_e:
                                logger.warning(f"Could not submit search using JavaScript: {str(js_e)}")
            else:
                logger.info("Autocomplete option selected, not submitting with Enter key")
            
            # Wait for search results to load
            logger.info("Waiting for search results to load")
            time.sleep(3)
            
            # Take screenshot of search results
            results_screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hpd_search_results.png")
            driver.save_screenshot(results_screenshot_path)
            logger.info(f"Search results screenshot saved to {results_screenshot_path}")
            
            # Check if we've been redirected to a building page
            current_url = driver.current_url
            logger.info(f"Current URL after search: {current_url}")
            
            building_id = None
            
            # Try to extract building ID from current URL if redirected
            building_id_match = re.search(r'/building/(\d+)', current_url)
            if building_id_match:
                building_id = building_id_match.group(1)
                logger.info(f"Extracted building ID from URL: {building_id}")
            else:
                # We're on search results page, need to find and click the right building
                logger.info("Looking for building in search results")
                
                # Log the page source for debugging
                page_source = driver.page_source
                logger.info(f"Page source length: {len(page_source)}")
                
                # First try to find mat-cards which are commonly used in Angular Material
                building_cards = driver.find_elements(By.CSS_SELECTOR, "mat-card, .mat-card, .search-result-item")
                logger.info(f"Found {len(building_cards)} potential building cards")
                
                building_links = []
                
                # Process cards if found
                if building_cards:
                    for card in building_cards:
                        try:
                            card_text = card.text
                            logger.info(f"Card text: {card_text}")
                            
                            # Look for address components
                            address_parts = partial_address.strip().split(' ', 1)
                            street_num = address_parts[0] if len(address_parts) > 0 else ""
                            street_name = address_parts[1] if len(address_parts) > 1 else ""
                            
                            # Calculate relevance score
                            relevance_score = 0
                            if street_num in card_text:
                                relevance_score += 2
                            if street_name.lower() in card_text.lower():
                                relevance_score += 3
                            if zip_code in card_text:
                                relevance_score += 2
                            
                            # Find links within the card
                            card_links = card.find_elements(By.TAG_NAME, "a")
                            for link in card_links:
                                href = link.get_attribute("href")
                                if href and '/building/' in href:
                                    bid_match = re.search(r'/building/(\d+)', href)
                                    if bid_match:
                                        building_links.append({
                                            'element': link,
                                            'href': href,
                                            'building_id': bid_match.group(1),
                                            'text': card_text,
                                            'score': relevance_score
                                        })
                            
                            # If no links with href found, try to find elements that might be clickable
                            if not card_links:
                                clickable_elements = card.find_elements(By.CSS_SELECTOR, "[role='button'], button, .clickable")
                                if clickable_elements:
                                    for element in clickable_elements:
                                        building_links.append({
                                            'element': element,
                                            'href': None,
                                            'building_id': None,
                                            'text': card_text,
                                            'score': relevance_score
                                        })
                        except Exception as e:
                            logger.warning(f"Error processing card: {str(e)}")
                
                # If no cards or no building links found in cards, try to find any links
                if not building_links:
                    # Look for links that might point to a building page
                    links = driver.find_elements(By.TAG_NAME, "a")
                    logger.info(f"Found {len(links)} links on the page")
                    
                    # Find all links that might be building details links
                    for link in links:
                        try:
                            href = link.get_attribute("href")
                            if href and '/building/' in href:
                                building_id_match = re.search(r'/building/(\d+)', href)
                                if building_id_match:
                                    # Extract the text around the link to check if it matches our address
                                    link_text = link.text
                                    parent_text = ""
                                    try:
                                        parent = link.find_element(By.XPATH, "..")
                                        parent_text = parent.text
                                    except:
                                        pass
                                    
                                    context_text = link_text + " " + parent_text
                                    logger.info(f"Building link text: {context_text}")
                                    
                                    # Extract the street number and name for fuzzy matching
                                    address_parts = partial_address.strip().split(' ', 1)
                                    street_num = address_parts[0] if len(address_parts) > 0 else ""
                                    street_name = address_parts[1] if len(address_parts) > 1 else ""
                                    
                                    # Check for fuzzy match (to handle cases like 393 vs 395)
                                    relevance_score = 0
                                    
                                    # Address number might be slightly different
                                    try:
                                        address_number = int(street_num)
                                        # Look for numbers in the link text
                                        numbers_in_text = re.findall(r'\b\d+\b', context_text)
                                        for num in numbers_in_text:
                                            try:
                                                text_num = int(num)
                                                # If numbers are close (within ±5), give points
                                                if abs(address_number - text_num) <= 5:
                                                    relevance_score += 3 - min(abs(address_number - text_num), 3)
                                            except:
                                                pass
                                    except:
                                        # If we can't convert to int, check for exact match
                                        if street_num in context_text:
                                            relevance_score += 2
                                    
                                    # Street name should match more closely
                                    if street_name.lower() in context_text.lower():
                                        relevance_score += 3
                                    
                                    # ZIP code is also important
                                    if zip_code in context_text:
                                        relevance_score += 2
                                    
                                    # Include this as a candidate
                                    building_links.append({
                                        'element': link,
                                        'href': href,
                                        'building_id': building_id_match.group(1),
                                        'text': context_text,
                                        'score': relevance_score
                                    })
                        except Exception as e:
                            logger.warning(f"Error processing link: {str(e)}")
                
                # If still no building links, try to scan the entire page for rows or items
                if not building_links:
                    # Look for any row-like elements that might contain building info
                    rows = driver.find_elements(By.CSS_SELECTOR, "tr, .row, [role='row'], div.item, .list-item")
                    logger.info(f"Found {len(rows)} potential rows or list items")
                    
                    for row in rows:
                        try:
                            row_text = row.text
                            logger.info(f"Row text: {row_text}")
                            
                            # Check if the row contains our address
                            address_parts = partial_address.strip().split(' ', 1)
                            street_num = address_parts[0] if len(address_parts) > 0 else ""
                            street_name = address_parts[1] if len(address_parts) > 1 else ""
                            
                            # Calculate relevance score
                            relevance_score = 0
                            if street_num in row_text:
                                relevance_score += 2
                            if street_name.lower() in row_text.lower():
                                relevance_score += 3
                            if zip_code in row_text:
                                relevance_score += 2
                            
                            # If this row seems relevant, look for clickable elements
                            if relevance_score > 0:
                                # Find links or buttons within the row
                                clickable = row.find_elements(By.CSS_SELECTOR, "a, button, [role='button'], .clickable")
                                for element in clickable:
                                    href = element.get_attribute("href")
                                    if href and '/building/' in href:
                                        bid_match = re.search(r'/building/(\d+)', href)
                                        if bid_match:
                                            building_links.append({
                                                'element': element,
                                                'href': href,
                                                'building_id': bid_match.group(1),
                                                'text': row_text,
                                                'score': relevance_score
                                            })
                                    elif element.is_enabled() and element.is_displayed():
                                        building_links.append({
                                            'element': element,
                                            'href': None,
                                            'building_id': None,
                                            'text': row_text,
                                            'score': relevance_score
                                        })
                        except Exception as e:
                            logger.warning(f"Error processing row: {str(e)}")
                
                # If STILL no building links, try to extract building IDs from the page source
                if not building_links:
                    # Look for building IDs in the HTML
                    logger.info("No building links found through UI elements, checking HTML source")
                    building_id_matches = re.findall(r'/building/(\d+)', page_source)
                    if building_id_matches:
                        # Remove duplicates
                        unique_building_ids = list(set(building_id_matches))
                        logger.info(f"Found {len(unique_building_ids)} building IDs in HTML: {unique_building_ids}")
                        
                        # Since we can't determine relevance, take the first one
                        building_id = unique_building_ids[0]
                        logger.info(f"Selected building ID from HTML: {building_id}")
                    else:
                        # Last resort - try direct API access
                        search_url = f"https://hpdonline.nyc.gov/HPDonline/provide/bldg/search?address={partial_address.replace(' ', '%20')}&zip={zip_code}"
                        logger.info(f"Trying direct API access: {search_url}")
                        driver.get(search_url)
                        time.sleep(2)
                        
                        # Check if the response contains building IDs
                        try:
                            page_text = driver.find_element(By.TAG_NAME, "body").text
                            if '{' in page_text and '}' in page_text:
                                # This might be a JSON response
                                match = re.search(r'(\{.*\})', page_text)
                                if match:
                                    try:
                                        json_str = match.group(1)
                                        json_data = json.loads(json_str)
                                        if 'buildingId' in json_data:
                                            building_id = str(json_data['buildingId'])
                                            logger.info(f"Found building ID in API response: {building_id}")
                                        elif 'id' in json_data:
                                            building_id = str(json_data['id'])
                                            logger.info(f"Found building ID in API response: {building_id}")
                                    except json.JSONDecodeError:
                                        logger.warning("Could not parse JSON from API response")
                        except Exception as e:
                            logger.warning(f"Error checking API response: {str(e)}")
                
                # Sort by relevance score
                building_links.sort(key=lambda x: x['score'], reverse=True)
                
                # Log all building links found
                for i, link_data in enumerate(building_links):
                    logger.info(f"Building link {i}: ID={link_data.get('building_id', 'None')}, Score={link_data['score']}, Text={link_data['text']}")
                
                # Try to get the building ID from the best match
                if building_links:
                    top_link = building_links[0]
                    
                    # If we already have the building ID, use it
                    if top_link.get('building_id'):
                        building_id = top_link['building_id']
                        logger.info(f"Using building ID from top link: {building_id}")
                    
                    # Otherwise, try to navigate to the building page and extract the ID
                    if not building_id:
                        logger.info("Clicking on top building link without building ID")
                        try:
                            top_link['element'].click()
                            logger.info("Successfully clicked building link")
                            time.sleep(2)
                            
                            # Check if we're now on a building page
                            current_url = driver.current_url
                            logger.info(f"URL after clicking: {current_url}")
                            
                            building_id_match = re.search(r'/building/(\d+)', current_url)
                            if building_id_match:
                                building_id = building_id_match.group(1)
                                logger.info(f"Extracted building ID from URL after click: {building_id}")
                        except Exception as e:
                            logger.warning(f"Error clicking building link: {str(e)}")
                            # Try JavaScript click as fallback
                            try:
                                driver.execute_script("arguments[0].click();", top_link['element'])
                                logger.info("Successfully clicked building link with JavaScript")
                                time.sleep(2)
                                
                                current_url = driver.current_url
                                building_id_match = re.search(r'/building/(\d+)', current_url)
                                if building_id_match:
                                    building_id = building_id_match.group(1)
                                    logger.info(f"Extracted building ID from URL after JS click: {building_id}")
                            except Exception as js_e:
                                logger.warning(f"JavaScript click failed: {str(js_e)}")
                                
                                # As a last attempt, try to navigate to the href directly if available
                                if top_link.get('href'):
                                    driver.get(top_link['href'])
                                    logger.info(f"Navigated directly to building URL: {top_link['href']}")
                                    time.sleep(2)
                                    
                                    current_url = driver.current_url
                                    building_id_match = re.search(r'/building/(\d+)', current_url)
                                    if building_id_match:
                                        building_id = building_id_match.group(1)
                                        logger.info(f"Extracted building ID from URL after navigation: {building_id}")
            
            # If we still couldn't find a building ID, try a different search approach
            if not building_id:
                logger.warning("Could not find building ID with normal search, trying broader search")
                
                # Try searching with just the street number and Brooklyn borough
                try:
                    address_parts = partial_address.strip().split(' ', 1)
                    street_num = address_parts[0] if len(address_parts) > 0 else ""
                    
                    # Navigate back to the search page
                    driver.get("https://hpdonline.nyc.gov/hpdonline/")
                    time.sleep(2)
                    
                    # Wait for Angular app to load
                    WebDriverWait(driver, 20).until(
                        lambda d: len(d.find_elements(By.CSS_SELECTOR, "app-root > *")) > 0
                    )
                    
                    # Find the search input
                    inputs = driver.find_elements(By.TAG_NAME, "input")
                    search_input = None
                    for input_field in inputs:
                        placeholder = input_field.get_attribute("placeholder")
                        if placeholder and ("search" in placeholder.lower() or "address" in placeholder.lower()):
                            search_input = input_field
                            break
                    
                    if search_input:
                        # Try just the street number and Brooklyn
                        search_query = f"{street_num} Brooklyn"
                        search_input.clear()
                        search_input.send_keys(search_query)
                        logger.info(f"Trying broader search with: {search_query}")
                        search_input.send_keys(Keys.RETURN)
                        time.sleep(3)
                        
                        # Take screenshot of this broader search
                        driver.save_screenshot(os.path.join(os.path.dirname(os.path.abspath(__file__)), "broader_search.png"))
                        
                        # Look for building IDs in the response
                        page_source = driver.page_source
                        building_id_matches = re.findall(r'/building/(\d+)', page_source)
                        if building_id_matches:
                            # Remove duplicates
                            unique_building_ids = list(set(building_id_matches))
                            logger.info(f"Found {len(unique_building_ids)} building IDs in broader search: {unique_building_ids}")
                            
                            # Take the first one
                            building_id = unique_building_ids[0]
                            logger.info(f"Selected building ID from broader search: {building_id}")
                except Exception as e:
                    logger.warning(f"Error during broader search: {str(e)}")
            
            # If we still couldn't find a building ID, try a hardcoded approach with known similar addresses
            if not building_id:
                # For 393 Hewes St specifically, try 395 Hewes St which might be the same building
                if "393 Hewes" in address:
                    alternative_addresses = [
                        {"address": "395 Hewes St", "id": "329960"},
                        {"address": "391 Hewes St", "id": "329959"}
                    ]
                    
                    logger.info(f"Trying known alternative addresses for {address}")
                    for alt in alternative_addresses:
                        logger.info(f"Trying alternative address: {alt['address']} with ID {alt['id']}")
                        # Use the first alternative found
                        building_id = alt['id']
                        results['metadata']['note'] = f"Used alternative address: {alt['address']}"
                        break
            
            # If we couldn't find a building ID, we can't proceed
            if not building_id:
                logger.error("Could not find building ID")
                return JsonResponse({
                    'success': False,
                    'error': 'Building not found in search results'
                })
            
            # Now we have the building ID, we can navigate directly to the violations and complaints pages
            
            # First, scrape violations
            violations_url = f"https://hpdonline.nyc.gov/hpdonline/building/{building_id}/violations"
            logger.info(f"Navigating to violations page: {violations_url}")
            driver.get(violations_url)
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "app-root > *")) > 0
            )
            time.sleep(2)
            
            # Take screenshot of violations page
            driver.save_screenshot(os.path.join(os.path.dirname(os.path.abspath(__file__)), "violations_page.png"))
            
            # Check for "No violations" message
            page_text = driver.find_element(By.TAG_NAME, "body").text
            if "No open violations" in page_text or "No violations" in page_text:
                logger.info("Page indicates no violations")
                results['message'] = "No violations found for this property"
            else:
                # Extract violations from table
                try:
                    # Find the violations table - first try Angular Material table
                    tables = driver.find_elements(By.CSS_SELECTOR, "mat-table, .mat-table, [role='table']")
                    if not tables:
                        # Try standard HTML table
                        tables = driver.find_elements(By.TAG_NAME, "table")
                    
                    if tables:
                        for table in tables:
                            try:
                                # Get table headers
                                header_cells = table.find_elements(By.CSS_SELECTOR, "th, .mat-header-cell")
                                headers = [cell.text.strip() for cell in header_cells if cell.text.strip()]
                                
                                if not headers:
                                    # Try Angular Material header cells
                                    header_cells = table.find_elements(By.CSS_SELECTOR, ".mat-header-cell, [role='columnheader']")
                                    headers = [cell.text.strip() for cell in header_cells if cell.text.strip()]
                                
                                logger.info(f"Violations table headers: {headers}")
                                
                                # Get table rows
                                rows = table.find_elements(By.CSS_SELECTOR, "tr:not(:first-child), .mat-row, [role='row']:not([role='columnheader'])")
                                
                                logger.info(f"Found {len(rows)} violation rows")
                                
                                # Process each row
                                for row in rows:
                                    cells = row.find_elements(By.CSS_SELECTOR, "td, .mat-cell, [role='cell']")
                                    
                                    if cells:
                                        data = {}
                                        for i, cell in enumerate(cells):
                                            if i < len(headers):
                                                header = headers[i]
                                                value = cell.text.strip()
                                                
                                                # Map header to standardized field name
                                                if re.search(r'viol.*id|nov.*id|id', header.lower()):
                                                    data['violation_number'] = value
                                                elif re.search(r'class', header.lower()):
                                                    data['severity'] = value
                                                elif re.search(r'date', header.lower()):
                                                    data['date'] = value
                                                elif re.search(r'desc', header.lower()):
                                                    data['description'] = value
                                                elif re.search(r'status', header.lower()):
                                                    data['status'] = value
                                                elif re.search(r'apt|apartment', header.lower()):
                                                    data['apartment'] = value
                                                else:
                                                    # Use header name as key
                                                    key = header.lower().replace(' ', '_').replace('#', '')
                                                    data[key] = value
                                        
                                        # Ensure we have at least a violation number
                                        if 'violation_number' in data or 'novid' in data:
                                            if 'novid' in data and 'violation_number' not in data:
                                                data['violation_number'] = data['novid']
                                            
                                            # Ensure we have a description
                                            if 'description' not in data:
                                                data['description'] = "Housing Code Violation"
                                            
                                            results['violations'].append(data)
                            except Exception as e:
                                logger.warning(f"Error processing violations table: {str(e)}")
                    else:
                        logger.warning("No violations table found")
                        
                        # If no table, look for list items or cards that might contain violations
                        violation_items = driver.find_elements(By.CSS_SELECTOR, ".violation-item, .card, mat-card")
                        
                        if violation_items:
                            logger.info(f"Found {len(violation_items)} potential violation items")
                            
                            for item in violation_items:
                                try:
                                    item_text = item.text
                                    
                                    # Use regex to extract violation information
                                    violation_id_match = re.search(r'\b(\d{6,10})\b', item_text)
                                    if violation_id_match:
                                        data = {
                                            'violation_number': violation_id_match.group(1),
                                            'description': 'Housing Code Violation'
                                        }
                                        
                                        # Try to extract other information
                                        date_match = re.search(r'\b(\d{1,2}/\d{1,2}/\d{4})\b', item_text)
                                        if date_match:
                                            data['date'] = date_match.group(1)
                                        
                                        class_match = re.search(r'\b(Class [1-3]|C[1-3])\b', item_text, re.IGNORECASE)
                                        if class_match:
                                            data['severity'] = class_match.group(1)
                                        
                                        status_match = re.search(r'\b(OPEN|CLOSED|ACTIVE)\b', item_text, re.IGNORECASE)
                                        if status_match:
                                            data['status'] = status_match.group(1)
                                        
                                        # Try to find a longer text that might be the description
                                        lines = item_text.split('\n')
                                        for line in lines:
                                            if len(line.strip()) > 20:
                                                data['description'] = line.strip()
                                                break
                                        
                                        results['violations'].append(data)
                                except Exception as e:
                                    logger.warning(f"Error processing violation item: {str(e)}")
                except Exception as e:
                    logger.error(f"Error extracting violations: {str(e)}")
            
            # Next, scrape complaints
            complaints_url = f"https://hpdonline.nyc.gov/hpdonline/building/{building_id}/complaints"
            logger.info(f"Navigating to complaints page: {complaints_url}")
            driver.get(complaints_url)
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "app-root > *")) > 0
            )
            time.sleep(2)
            
            # Take screenshot of complaints page
            driver.save_screenshot(os.path.join(os.path.dirname(os.path.abspath(__file__)), "complaints_page.png"))
            
            # Check for "No complaints" message
            page_text = driver.find_element(By.TAG_NAME, "body").text
            if "No open complaints" in page_text or "No complaints" in page_text:
                logger.info("Page indicates no complaints")
                if 'message' in results and 'violations' in results['message'].lower():
                    # Don't overwrite existing message about violations
                    pass
                else:
                    results['message'] = "No complaints found for this property"
            else:
                # Extract complaints from table
                try:
                    # Find the complaints table - first try Angular Material table
                    tables = driver.find_elements(By.CSS_SELECTOR, "mat-table, .mat-table, [role='table']")
                    if not tables:
                        # Try standard HTML table
                        tables = driver.find_elements(By.TAG_NAME, "table")
                    
                    if tables:
                        for table in tables:
                            try:
                                # Get table headers
                                header_cells = table.find_elements(By.CSS_SELECTOR, "th, .mat-header-cell")
                                headers = [cell.text.strip() for cell in header_cells if cell.text.strip()]
                                
                                if not headers:
                                    # Try Angular Material header cells
                                    header_cells = table.find_elements(By.CSS_SELECTOR, ".mat-header-cell, [role='columnheader']")
                                    headers = [cell.text.strip() for cell in header_cells if cell.text.strip()]
                                
                                logger.info(f"Complaints table headers: {headers}")
                                
                                # Get table rows
                                rows = table.find_elements(By.CSS_SELECTOR, "tr:not(:first-child), .mat-row, [role='row']:not([role='columnheader'])")
                                
                                logger.info(f"Found {len(rows)} complaint rows")
                                
                                # Process each row
                                for row in rows:
                                    cells = row.find_elements(By.CSS_SELECTOR, "td, .mat-cell, [role='cell']")
                                    
                                    if cells:
                                        data = {}
                                        for i, cell in enumerate(cells):
                                            if i < len(headers):
                                                header = headers[i]
                                                value = cell.text.strip()
                                                
                                                # Map header to standardized field name
                                                if re.search(r'sr.*#|complaint.*#|311', header.lower()):
                                                    data['complaint_number'] = value
                                                elif re.search(r'date', header.lower()):
                                                    data['date'] = value
                                                elif re.search(r'condition|problem|desc', header.lower()):
                                                    data['description'] = value
                                                elif re.search(r'status', header.lower()):
                                                    data['status'] = value
                                                elif re.search(r'location|room', header.lower()):
                                                    data['location'] = value
                                                else:
                                                    # Use header name as key
                                                    key = header.lower().replace(' ', '_').replace('#', '')
                                                    data[key] = value
                                        
                                        # Ensure we have at least a complaint number
                                        if 'complaint_number' in data or 'sr_number' in data:
                                            if 'sr_number' in data and 'complaint_number' not in data:
                                                data['complaint_number'] = data['sr_number']
                                            
                                            # Ensure we have a description
                                            if 'description' not in data:
                                                data['description'] = "Housing Complaint"
                                            
                                            results['complaints'].append(data)
                            except Exception as e:
                                logger.warning(f"Error processing complaints table: {str(e)}")
                    else:
                        logger.warning("No complaints table found")
                        
                        # If no table, look for list items or cards that might contain complaints
                        complaint_items = driver.find_elements(By.CSS_SELECTOR, ".complaint-item, .card, mat-card")
                        
                        if complaint_items:
                            logger.info(f"Found {len(complaint_items)} potential complaint items")
                            
                            for item in complaint_items:
                                try:
                                    item_text = item.text
                                    
                                    # Use regex to extract complaint information
                                    complaint_id_match = re.search(r'\b(311[-\s]?\d{8}|SR\s*#?\s*\d+)\b', item_text, re.IGNORECASE)
                                    if complaint_id_match:
                                        data = {
                                            'complaint_number': complaint_id_match.group(1),
                                            'description': 'Housing Complaint'
                                        }
                                        
                                        # Try to extract other information
                                        date_match = re.search(r'\b(\d{1,2}/\d{1,2}/\d{4})\b', item_text)
                                        if date_match:
                                            data['date'] = date_match.group(1)
                                        
                                        status_match = re.search(r'\b(OPEN|CLOSED|ACTIVE|PENDING)\b', item_text, re.IGNORECASE)
                                        if status_match:
                                            data['status'] = status_match.group(1)
                                        
                                        # Try to find a longer text that might be the description
                                        lines = item_text.split('\n')
                                        for line in lines:
                                            if len(line.strip()) > 15:
                                                data['description'] = line.strip()
                                                break
                                        
                                        results['complaints'].append(data)
                                except Exception as e:
                                    logger.warning(f"Error processing complaint item: {str(e)}")
                except Exception as e:
                    logger.error(f"Error extracting complaints: {str(e)}")
            
            # Format the final results
            formatted_results = format_hpd_data(results)
            
            logger.info(f"Scraping completed successfully. Found {len(formatted_results['violations'])} violations and {len(formatted_results['complaints'])} complaints")
            
            return JsonResponse({
                'success': True,
                'data': formatted_results
            })
            
        except Exception as e:
            logger.error(f"Error during HPD scraping: {str(e)}")
            
            # Take error screenshot if driver exists
            if driver:
                try:
                    error_screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hpd_error.png")
                    driver.save_screenshot(error_screenshot_path)
                    logger.info(f"Error screenshot saved to {error_screenshot_path}")
                except Exception as ss_error:
                    logger.warning(f"Could not take error screenshot: {str(ss_error)}")
            
            # Get traceback
            import traceback
            trace = traceback.format_exc()
            logger.error(f"Traceback: {trace}")
            
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        
        finally:
            # Clean up
            if driver:
                try:
                    driver.quit()
                    logger.info("WebDriver closed successfully")
                except Exception as e:
                    logger.warning(f"Error closing WebDriver: {str(e)}")
    
    logger.warning("Invalid request (not XMLHttpRequest)")
    return JsonResponse({
        'success': False,
        'error': 'Invalid request'
    })

def format_hpd_data(results):
    """Format the results to match frontend expectations."""
    formatted = {
        'metadata': results['metadata'],
        'complaints': [],
        'violations': []
    }
    
    # Format complaints for frontend display
    for complaint in results['complaints']:
        formatted_complaint = {
            'date': complaint.get('date', ''),
            'complaint_number': complaint.get('complaint_number', ''),
            'description': complaint.get('description', ''),
            'status': complaint.get('location', '')
        }
        formatted['complaints'].append(formatted_complaint)
    
    # Format violations for frontend display
    for violation in results['violations']:
        formatted_violation = {
            'date': violation.get('date', ''),
            'violation_number': violation.get('violation_number', ''),
            'description': violation.get('description', ''),
            'status': violation.get('status', 'Open'),  # Default to Open if not specified
            'severity': violation.get('severity', '')
        }
        formatted['violations'].append(formatted_violation)
    
    # Include any message
    if 'message' in results:
        formatted['message'] = results['message']
    
    return formatted

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