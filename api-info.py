import requests
import argparse
import sys
import os
import json
import urllib3
from urllib3.exceptions import InsecureRequestWarning
from colorama import init, Fore, Style

# Initialize colorama for colored output
init(autoreset=True)

# Suppress the InsecureRequestWarning when -k is used
urllib3.disable_warnings(InsecureRequestWarning)

# Function to pretty-print JSON with colors
def pretty_print_json(data):
    def colorize_json(key, value):
        key_colored = f"{Fore.YELLOW}\"{key}\"{Style.RESET_ALL}"
        if isinstance(value, str):
            value_colored = f"{Fore.GREEN}\"{value}\"{Style.RESET_ALL}"
        elif isinstance(value, bool):
            value_colored = f"{Fore.CYAN}{value}{Style.RESET_ALL}"
        elif value is None:
            value_colored = f"{Fore.RED}null{Style.RESET_ALL}"
        else:
            value_colored = f"{Fore.MAGENTA}{value}{Style.RESET_ALL}"
        return key_colored, value_colored

    # Format and colorize the JSON
    formatted_json = json.dumps(data, indent=4)
    for key, value in json.loads(formatted_json).items():
        key_colored, value_colored = colorize_json(key, value)
        formatted_json = formatted_json.replace(f"\"{key}\"", key_colored).replace(str(value), value_colored)

    print(formatted_json)

# Function to get the list of available APIs
def get_available_apis(nas_url, verify_ssl):
    api_info_url = f"{nas_url}/webapi/entry.cgi"
    params = {
        'api': 'SYNO.API.Info',
        'version': '1',
        'method': 'query'
    }
    response = requests.get(api_info_url, params=params, verify=verify_ssl)
    data = response.json()
    return data

# Function to print only the API names
def print_api_names(data):
    if 'data' in data:
        for api_name in data['data']:
            print(api_name)

# Get API methods
def get_api_method_info(nas_url, api_name, verify_ssl):
    api_info_url = f"{nas_url}/webapi/entry.cgi"
    params = {
        'api': 'SYNO.API.Info',
        'version': '1',
        'method': 'query',
        'query': api_name
    }
    response = requests.get(api_info_url, params=params, verify=verify_ssl)
    return response.json()

# Step 2: Function to login and get the SID (Auth Token)
def login_to_nas(nas_url, username, password, verify_ssl):
    login_url = f"{nas_url}/webapi/entry.cgi"
    params = {
        'api': 'SYNO.API.Auth',
        'version': '6',
        'method': 'login',
        'account': username,
        'passwd': password,
        'enable_syno_token': 'yes'
    }
    response = requests.get(login_url, params=params, verify=verify_ssl)
    response_data = response.json()
    
    if response_data['success']:
        sid = response_data['data']['sid']
        syno_token = response_data['data'].get('synotoken', None)  # Get syno_token if available
        return sid, syno_token
    else:
        raise Exception(f"Failed to login: {response_data}")

# Step 3: Function to toggle AFP service (enable/disable)
def toggle_afp_service(nas_url, sid, syno_token, enable, verify_ssl):
    afp_api_url = f"{nas_url}/webapi/entry.cgi"
    params = {
        'api': 'SYNO.Core.FileServ.AFP',  # Corrected API endpoint
        'version': '1',
        'method': 'set',
        'afp_enable': 'true' if enable else 'false',  # Correct parameter: afp_enable
        '_sid': sid  # Pass the session ID
    }
    if syno_token:
        params['SynoToken'] = syno_token  # Pass the SynoToken if available
    response = requests.get(afp_api_url, params=params, verify=verify_ssl)
    return response.json()

# Step 4: Function to logout from NAS
def logout_from_nas(nas_url, sid, verify_ssl):
    logout_url = f"{nas_url}/webapi/entry.cgi"
    params = {
        'api': 'SYNO.API.Auth',
        'version': '6',
        'method': 'logout',
        '_sid': sid
    }
    response = requests.get(logout_url, params=params, verify=verify_ssl)
    return response.json()

# Command-line argument parsing
def parse_arguments():
    parser = argparse.ArgumentParser(description="Toggle AFP service on Synology NAS")
    
    # Add argument for AFP toggle
    parser.add_argument(
        "afp_toggle", 
        choices=['true', 'false'], 
        nargs='?',  # Make this optional if --apis is used
        help="Enable or disable AFP service (true/false)"
    )
    
    # Add argument to disable SSL verification
    parser.add_argument(
        "--insecure", "-k", 
        action="store_true", 
        help="Disable SSL certificate validation (like curl's -k)"
    )
    
    # Add argument to list available APIs
    parser.add_argument(
        "--apis", "-a",
        action="store_true",
        help="Print available APIs and exit"
    )

    # Add argument to print only API names
    parser.add_argument(
        "--name", "-n",
        action="store_true",
        help="Print only the API names (with --apis or -a)"
    )

    # Add argument to print only specific API info
    parser.add_argument(
        "--info", "-i",
        action="store_true",
        help="Print only the API info and exit"
    )
    
    return parser.parse_args()

# Function to retrieve environment variables and check if they are set
def get_env_variable(var_name):
    value = os.getenv(var_name)
    if not value:
        print(f"Error: Environment variable '{var_name}' is not set.")
        sys.exit(1)
    return value

# Main program to login, toggle AFP service, and logout
if __name__ == "__main__":
    # Parse the command-line arguments to get AFP toggle state, SSL verification flag, and API listing flag
    args = parse_arguments()

    # Retrieve environment variables with error handling
    nas_hostname = get_env_variable("NAS_HOSTNAME")
    nas_port = os.getenv("NAS_PORT", "5001")  # Default to 5001 for HTTPS if not set
    username = get_env_variable("NAS_USERNAME")
    password = get_env_variable("NAS_PASSWORD")

    # Construct NAS URL
    nas_url = f"https://{nas_hostname}:{nas_port}"

    # Set verify_ssl based on the presence of the -k flag
    verify_ssl = not args.insecure  # False if -k is used, otherwise True

    # If the --apis or -a flag is set, print the available APIs and exit
    if args.apis:
        api_data = get_available_apis(nas_url, verify_ssl)
        if args.name:
            print_api_names(api_data)
        else:
            pretty_print_json(api_data)
        sys.exit(0)  # Exit after printing available APIs

    # If the afp_toggle argument is not set and --apis was not provided, exit
    if not args.afp_toggle:
        print("Error: AFP toggle argument (true/false) is missing.")
        sys.exit(1)

    sid = None  # Initialize sid as None to avoid issues if login fails
    syno_token = None  # Initialize syno_token

    try:
        # Step 1: Retrieve API Information
        api_info = get_available_apis(nas_url, verify_ssl)

        # Step 1.1: Retrieve API Information specifically for SYNO.Core.FileServ.AFP
        if args.info:
            api_info = get_api_method_info(nas_url, 'SYNO.Core.FileServ.AFP', verify_ssl)
            pretty_print_json(api_info)  # This will print the full details of the SYNO.Core.FileServ.AFP API
            sys.exit(0)
        
        # Check if SYNO.Core.FileServ.AFP API is present
        if 'SYNO.Core.FileServ.AFP' not in api_info['data']:
            print("Error: SYNO.Core.FileServ.AFP API is not available on this NAS.")
            sys.exit(1)
        
        # Step 2: Login to NAS
        sid, syno_token = login_to_nas(nas_url, username, password, verify_ssl)
        print(f"Logged in successfully. SID: {sid}, SynoToken: {syno_token}")
        
        # Step 3: Toggle AFP Service (enable or disable)
        result = toggle_afp_service(nas_url, sid, syno_token, args.afp_toggle == 'true', verify_ssl)
        if result['success']:
            print(f"AFP service successfully {'enabled' if args.afp_toggle == 'true' else 'disabled'}")
        else:
            print(f"Failed to change AFP service state: {result}")

    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        # Step 4: Logout from NAS (only if login was successful and sid was obtained)
        if sid:
            logout_response = logout_from_nas(nas_url, sid, verify_ssl)
            print("Logged out:", logout_response)
        else:
            print("No session to log out of. Skipping logout.")

