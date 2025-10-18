import requests
import time
import json
import logging
import re
import os

# --- CONFIGURATION ---
SITES_TO_MONITOR = [  
    {
         "name": "MachineWise",
         "target_url": "https://machinewise.store/collections/mojave-smart-inventory/products.json",
         "base_url": "https://machinewise.store",
         "method": "json", 
         "ntfy_topic_url": "",
     },
     {
        "name": "GrimsmoNorseman",
        "target_url": "https://grimsmoknives.com/collections/norseman-inventory/products.json",
        "base_url": "https://grimsmoknives.com",
        "method": "json",
        "ntfy_topic_url": "",
    },
    {
        "name": "GrimsmoRask",
        "target_url": "https://grimsmoknives.com/collections/rask-inventory/products.json",
        "base_url": "https://grimsmoknives.com",
        "method": "json",
        "ntfy_topic_url": "",
    },
    {
        "name": "Recon1",
        "target_url": "https://recon1.com/collections/new/products.json?sort_by=created-descending",
        "base_url": "https://recon1.com",
        "method": "json",
        "ntfy_topic_url": "",
    }
]

# {
#     "name": "NonShopifySite",
#     "target_url": "https://some-other-store.com/new-arrivals",
#     "base_url": "https://some-other-store.com",
#     "regex_pattern": r'<a href="(/products/[^"]+)" class="product-link"', Insert regex here
#     "method": "regex", # Use the 'regex' method
#     "ntfy_topic_url": ,
# }

CHECK_INTERVAL_SECONDS = 30
STATE_DIR = "inventory_states"

# --- SCRIPT LOGIC ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def load_known_inventory(state_file):
    """Loads the set of known inventory URLs from a specific state file."""
    try:
        with open(state_file, 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def save_known_inventory(inventory_urls, state_file):
    """Saves the current set of inventory URLs to a specific state file."""
    os.makedirs(os.path.dirname(state_file), exist_ok=True)
    with open(state_file, 'w') as f:
        json.dump(list(inventory_urls), f)

def send_notification(title, message, ntfy_topic_url):
    """Sends a push notification using a specific ntfy.sh topic."""
    logger = logging.getLogger(title)
    try:
        requests.post(
            ntfy_topic_url,
            data=message.encode('utf-8'),
            headers={"Title": title}
        )
        logger.info(f"Notification sent via {ntfy_topic_url}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send notification: {e}")

def get_inventory_by_json(name, target_url, base_url):
    """Fetches a Shopify collection's .json endpoint and returns a set of product URLs."""
    logger = logging.getLogger(name)
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(target_url, headers=headers, timeout=15)
        response.raise_for_status()

        data = response.json()
        inventory_urls = set()
        
        if 'products' not in data or not data['products']:
             logger.info("Found 0 items in JSON response.")
             return set()

        for product in data['products']:
            # 'handle' is the product's unique URL slug
            product_slug = product['handle'] 
            full_url = f"{base_url}/products/{product_slug}"
            inventory_urls.add(full_url)
        
        logger.info(f"Found {len(inventory_urls)} items from JSON endpoint.")
        return inventory_urls

    except requests.exceptions.RequestException as e:
        logger.error(f"Could not fetch JSON content: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from response: {e}")
        # Save the invalid response for debugging
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(os.path.join(STATE_DIR, f"debug_{name}.html"), 'w', encoding='utf-8') as f:
            f.write(response.text)
        return None
    except Exception as e:
        logger.error(f"An error occurred during JSON parsing: {e}")
        return None

def get_inventory_by_regex(name, target_url, base_url, pattern):
    """Fetches a website and returns a set of current inventory item URLs using a given regex pattern."""
    logger = logging.getLogger(name)
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(target_url, headers=headers, timeout=15)
        response.raise_for_status()

        relative_urls = re.findall(pattern, response.text)
        
        if not relative_urls:
            logger.warning(f"Regex found 0 items. Saving HTML for review.")
            os.makedirs(STATE_DIR, exist_ok=True)
            with open(os.path.join(STATE_DIR, f"debug_{name}.html"), 'w', encoding='utf-8') as f:
                f.write(response.text)
        
        inventory_urls = {base_url + url for url in relative_urls}
        logger.info(f"Found {len(inventory_urls)} items from regex.")
        return inventory_urls

    except requests.exceptions.RequestException as e:
        logger.error(f"Could not fetch website content: {e}")
        return None
    except Exception as e:
        logger.error(f"An error occurred during regex parsing: {e}")
        return None

def check_site(site_config):
    """Runs a single check for a given site configuration."""
    name = site_config["name"]
    logger = logging.getLogger(name)
    logger.info("Checking for new inventory...")

    state_file = os.path.join(STATE_DIR, f"known_inventory_{name.lower()}.json")
    
    known_inventory = load_known_inventory(state_file)
    if not known_inventory:
        logger.info(f"State file not found or empty. Starting with a fresh inventory list for {name}.")

    current_inventory = None
    if site_config["method"] == "json":
        current_inventory = get_inventory_by_json(
            name,
            site_config["target_url"],
            site_config["base_url"]
        )
    elif site_config["method"] == "regex":
        current_inventory = get_inventory_by_regex(
            name,
            site_config["target_url"],
            site_config["base_url"],
            site_config["regex_pattern"]
        )
    
    if current_inventory is not None:
        if not known_inventory and current_inventory:
            logger.info(f"Establishing baseline inventory for {name} with {len(current_inventory)} items.")
            save_known_inventory(current_inventory, state_file)
            return

        new_items = current_inventory - known_inventory
        if new_items:
            logger.info(f"Found {len(new_items)} new item(s)!")
            for item_url in new_items:
                send_notification(
                    f"New {name} Inventory!",
                    f"A new item has been listed: {item_url}",
                    site_config["ntfy_topic_url"]
                )
            # Save the new complete list
            save_known_inventory(current_inventory, state_file)
        else:
            logger.info("No new items found.")

def main():
    """The main function that runs the monitoring loop."""
    logging.info("Starting multi-site inventory monitor (JSON API)...")
    
    unique_topics = {site["ntfy_topic_url"] for site in SITES_TO_MONITOR}
    for topic_url in unique_topics:
        send_notification(
            "Inventory Monitor Started - v3 (JSON)",
            "The script is now running and checking for new items using the Shopify JSON API.",
            topic_url
        )
    
    while True:
        for site in SITES_TO_MONITOR:
            check_site(site)
        
        logging.info(f"All sites checked. Waiting for {CHECK_INTERVAL_SECONDS} seconds...")
        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()