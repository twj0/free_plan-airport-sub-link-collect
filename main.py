import os
import sys
import logging
import urllib.parse
import requests

# Dynamically import all clients
from clients import blue2sea_client, dabai_client, ikuuu_client, louwangzhiyu_client, wwn_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
OUTPUT_FILE = "merged_subscription.yaml"

# --- Task Definitions ---
TASKS = {
    "blue2sea": { "id": "blue2sea.com", "func": blue2sea_client.get_subscription, "needs_creds": False },
    "dabai": { "id": "dabai.in", "func": dabai_client.get_subscription, "needs_creds": True },
    "ikuuu": { "id": "ikuuu.one", "func": ikuuu_client.get_subscription, "needs_creds": True },
    "louwangzhiyu": { "id": "louwangzhiyu.xyz", "func": louwangzhiyu_client.get_subscription, "needs_creds": True },
    "wwn": { "id": "wwn.trx1.cyou", "func": wwn_client.get_subscription, "needs_creds": True }
}

# --- Subscription Converter Configuration ---
SUB_CONVERTER_BACKEND = "subapi.v1.mk"
# CHANGED: Corrected the GitHub Raw URL to the standard, permanent format.
# Replace 'twj0' and 'free_plan-airport-sub-link-collect' with your username and repo name.
BASE_CONFIG_URL = "https://raw.githubusercontent.com/twj0/free_plan-airport-sub-link-collect/main/base.yaml" 

def run_tasks(task_names):
    """Runs the specified tasks and returns a list of fetched subscription links."""
    # CHANGED: This function now collects the actual links.
    all_links = []
    for name in task_names:
        task = TASKS[name]
        logging.info(f"--- Running task: {name} ---")
        
        link = None
        if task['needs_creds']:
            email = os.environ.get(f"{name.upper()}_EMAIL")
            password = os.environ.get(f"{name.upper()}_PASSWORD")
            if not email or not password:
                logging.warning(f"Skipping {name}: Credentials not found in GitHub Secrets.")
                continue
            link = task['func'](email, password)
        else:
            link = task['func']()
            
        if link:
            logging.info(f"Success! Fetched link for {name}.")
            all_links.append(link)
        else:
            logging.error(f"Failed to fetch link for {name}.")
            
    return all_links

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ['daily', 'weekly']:
        print("Usage: python main.py [daily|weekly]")
        sys.exit(1)
        
    run_mode = sys.argv[1]
    
    tasks_to_run = []
    if run_mode == 'daily':
        tasks_to_run = ['blue2sea']
    elif run_mode == 'weekly':
        tasks_to_run = ['dabai', 'ikuuu', 'louwangzhiyu', 'wwn']

    # 1. Get all raw subscription links
    subscription_links = run_tasks(tasks_to_run)
    
    if not subscription_links:
        logging.warning("No subscription links were fetched. Halting execution.")
        # We exit with a success code to prevent the Actions workflow from showing an error,
        # as this is an expected outcome if a site is down.
        sys.exit(0)

    # 2. Build the URL for the subscription converter
    links_str = "|".join(subscription_links)
    
    encoded_links = urllib.parse.quote(links_str)
    encoded_config_url = urllib.parse.quote(BASE_CONFIG_URL)

    final_converter_url = f"https://{SUB_CONVERTER_BACKEND}/sub?target=clash&url={encoded_links}&insert=false&config={encoded_config_url}&emoji=true&new_name=true"
    
    logging.info(f"Calling subscription converter...")
    logging.debug(f"Converter URL: {final_converter_url}")

    # 3. Get the final merged subscription from the converter
    try:
        response = requests.get(final_converter_url, timeout=45) # Increased timeout for safety
        response.raise_for_status()
        final_subscription_content = response.text

        # 4. Save the content to the output file
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(final_subscription_content)
        
        logging.info(f"--- Successfully generated merged subscription file: {OUTPUT_FILE}! ---")

    except requests.exceptions.RequestException as e:
        logging.error(f"Error calling the subscription converter or saving the file: {e}")
        # Exit with a non-zero status code to indicate a real failure in the workflow
        sys.exit(1)

if __name__ == "__main__":
    main()