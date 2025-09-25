import requests
import time
import json
import logging
import re
import os


SITES_TO_MONITOR = [  
    {
         "name": "MachineWise",
         "target_url": "https://machinewise.store/collections/mojave-inventory",
         "base_url": "https://machinewise.store",
         "regex_pattern": r'<a[^>]*?href="(/products/[^"]+)"[^>]*?class="[^"]*?full-unstyled-link[^"]*?"',
         "ntfy_topic_url": "https://ntfy.sh/",
     },
     {
        "name": "GrimsmoNorseman",
        "target_url": "https://grimsmoknives.com/collections/norseman-inventory",
        "base_url": "https://grimsmoknives.com",
        "regex_pattern": r'<a href="(/products/[^"]+)" class="product-card__media"',
        "ntfy_topic_url": "https://ntfy.sh/", 
    },
    {
        "name": "GrimsmoRask",
        "target_url": "https://grimsmoknives.com/collections/rask-inventory",
        "base_url": "https://grimsmoknives.com",
        "regex_pattern": r'<a href="(/products/[^"]+)" class="product-card__media"',
        "ntfy_topic_url": "https://ntfy.sh/", 
    },
    {
        "name": "Recon1",
        "target_url": "https://recon1.com/collections/new?sort_by=created-descending",
        "base_url": "https://recon1.com",
        "regex_pattern": r'<a href="(/products/[^"]+)" class="product-card__media"',
        "ntfy_topic_url": "https://ntfy.sh/", 
    }
]

CHECK_INTERVAL_SECONDS = 60
STATE_DIR = "inventory_states" # Directory to store state files

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
    # Ensure the state directory exists
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

def get_current_inventory(name, target_url, base_url, pattern):
    """Fetches a website and returns a set of current inventory item URLs using a given regex pattern."""
    logger = logging.getLogger(name)
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(target_url, headers=headers, timeout=15)
        response.raise_for_status()

        relative_urls = re.findall(pattern, response.text)
        
        inventory_urls = {base_url + url for url in relative_urls}
        logger.info(f"Found {len(inventory_urls)} items on the page.")
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

    current_inventory = get_current_inventory(
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
            save_known_inventory(current_inventory, state_file)
        else:
            logger.info("No new items found.")

def main():
    """The main function that runs the monitoring loop."""
    logging.info("Starting multi-site inventory monitor...")
    
    while True:
        for site in SITES_TO_MONITOR:
            check_site(site)
        
        logging.info(f"All sites checked. Waiting for {CHECK_INTERVAL_SECONDS} seconds...")
        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()