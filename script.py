import requests
import time
import json
import logging
import re 

TARGET_URL = "https://machinewise.store/collections/mojave-inventory"

CHECK_INTERVAL_SECONDS = 60

STATE_FILE = "known_inventory.json"


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def load_known_inventory():
    """Loads the set of known inventory URLs from the state file."""
    try:
        with open(STATE_FILE, 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        logging.info(f"State file '{STATE_FILE}' not found. Starting with an empty inventory list.")
        return set()

def save_known_inventory(inventory_urls):
    """Saves the current set of inventory URLs to the state file."""
    with open(STATE_FILE, 'w') as f:
        json.dump(list(inventory_urls), f)

def send_notification(title, message):
    """Sends a push notification using ntfy.sh."""
    try:
        requests.post(
            NTFY_TOPIC_URL,
            data=message.encode('utf-8'),
            headers={"Title": title}
        )
        logging.info(f"Notification sent: {title}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send notification: {e}")

# THIS IS THE MODIFIED FUNCTION
def get_current_inventory():
    """Fetches the website and returns a set of current inventory item URLs using regex."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(TARGET_URL, headers=headers, timeout=15)
        response.raise_for_status()

        html_content = response.text

        # Define the regular expression machinewise uses for the mojaves
        pattern = r'<a[^>]*?href="(/products/[^"]+)"[^>]*?class="[^"]*?full-unstyled-link[^"]*?"'
        
        # finds all the regex matches
        relative_urls = re.findall(pattern, html_content)
        
        # Build the full URLs
        base_url = "https://machinewise.store"
        inventory_urls = {base_url + url for url in relative_urls}
        
        return inventory_urls

    except requests.exceptions.RequestException as e:
        logging.error(f"Could not fetch website content: {e}")
        return None
    except Exception as e:
        logging.error(f"An error occurred during regex parsing: {e}")
        return None

def main():
    """The main function that runs the monitoring loop."""
    logging.info("Starting inventory monitor...")
    known_inventory = load_known_inventory()

    while True:
        logging.info("Checking for new inventory...")
        current_inventory = get_current_inventory()
        
        if current_inventory is not None:
            new_items = current_inventory - known_inventory
            if new_items:
                logging.info(f"Found {len(new_items)} new item(s)!")
                for item_url in new_items:
                    send_notification(
                        "New MachineWise Inventory!",
                        f"A new item has been listed: {item_url}"
                    )
                known_inventory.update(new_items)
                save_known_inventory(known_inventory)
            else:
                logging.info("No new items found.")
        
        logging.info(f"Waiting for {CHECK_INTERVAL_SECONDS} seconds...")
        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()