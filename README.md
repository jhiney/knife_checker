# Knife Checker

A simple, configurable Python script to monitor Shopify and other websites for knife restocks (or any other products) and send notifications via [ntfy.sh](https://ntfy.sh).

## Features

- **Shopify Support**: Monitor any Shopify collection for new products using the JSON API (fast and reliable).
- **Regex Support**: Monitor any website by using regex patterns to find product links.
- **Availability Check**: Option to filter for only in-stock items (Shopify only).
- **Notifications**: Push notifications via ntfy.sh (supports iOS, Android, and Desktop).
- **State Tracking**: Keeps track of known inventory to only notify on *new* items.

## Prerequisites

- **Python 3.6+**
- **requests** library

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/jhiney/inventory_monitor.git
    cd inventory_monitor
    ```

2.  **Install dependencies:**
    ```bash
    pip install requests
    ```

## Configuration

1.  **Create your config file:**
    Copy the example configuration file to `config.json`.
    ```bash
    cp config.example.json config.json
    ```

2.  **Edit `config.json`:**
    Open `config.json` and add the sites you want to monitor.

    **Example Configuration:**
    ```json
    {
      "check_interval_seconds": 60,
      "sites": [
        {
          "name": "MachineWise",
          "target_url": "https://machinewise.store/collections/mojave-inventory/products.json",
          "base_url": "https://machinewise.store",
          "method": "json",
          "ntfy_topic_url": "https://ntfy.sh/my_secret_topic"
        },
        {
          "name": "OtherStore",
          "target_url": "https://otherstore.com/new",
          "base_url": "https://otherstore.com",
          "method": "regex",
          "regex_pattern": "<a href=\"(/products/[^\"]+)\"",
          "ntfy_topic_url": "https://ntfy.sh/my_secret_topic"
        }
      ]
    }
    ```

    **Configuration Fields:**
    - `check_interval_seconds`: How often (in seconds) to check for updates.
    - `sites`: A list of site objects.
      - `name`: A unique name for the site (used for logging and state tracking).
      - `target_url`: The URL to fetch. For Shopify, append `/products.json` to a collection URL.
      - `base_url`: The base URL of the site (used to construct full product links).
      - `method`: `json` for Shopify sites, `regex` for others.
      - `regex_pattern`: (Required for `regex` method) A Python regex pattern with one capturing group for the relative product URL.
      - `check_availability`: (Optional, `json` method only) Set to `true` to only notify if the item is in stock.
      - `ntfy_topic_url`: Your ntfy.sh topic URL.

## Usage

Run the script:
```bash
python script.py
```

The script will run continuously. To stop it, press `Ctrl+C`.

On the first run, it will populate the initial state for each site and will not send notifications. Notifications will only be sent for *new* items detected in subsequent checks.

## Deployment (DigitalOcean)

Here is a guide to deploying this script on a DigitalOcean Droplet (Ubuntu) so it runs 24/7.

1.  **Create a Droplet:**
    - Create a basic Droplet (the cheapest option is sufficient).
    - Choose an Ubuntu image.
    - SSH into your droplet: `ssh root@your_droplet_ip`

2.  **Setup Environment:**
    ```bash
    apt update
    apt install python3-pip python3-venv git -y
    ```

3.  **Clone & Install:**
    ```bash
    git clone https://github.com/jhiney/inventory_monitor.git
    cd inventory_monitor
    python3 -m venv .venv
    source .venv/bin/activate
    pip install requests
    ```

4.  **Configure:**
    - Create your config file: `cp config.example.json config.json`
    - Edit it with nano: `nano config.json`

5.  **Run in Background (Systemd):**
    - Create a service file:
      ```bash
      nano /etc/systemd/system/inventory_monitor.service
      ```
    - Paste the following (adjust paths/usernames as needed):
      ```ini
      [Unit]
      Description=Inventory Monitor Service
      After=network.target

      [Service]
      Type=simple
      User=root
      WorkingDirectory=/root/inventory_monitor
      ExecStart=/root/inventory_monitor/.venv/bin/python script.py
      Restart=always

      [Install]
      WantedBy=multi-user.target
      ```
    - Start and enable the service:
      ```bash
      systemctl daemon-reload
      systemctl start inventory_monitor
      systemctl enable inventory_monitor
      ```

6.  **Check Status:**
    ```bash
    systemctl status inventory_monitor
    ```
    To see logs:
    ```bash
    journalctl -u inventory_monitor -f
    ```

## License

[MIT License](LICENSE)
