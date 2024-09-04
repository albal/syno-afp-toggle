import requests
import argparse
import sys
import os
import json
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Suppress the InsecureRequestWarning when -k or --insecure is used
urllib3.disable_warnings(InsecureRequestWarning)

# Step 2: Function to login and get the SID (Auth Token) in DSM 7
def login_to_nas(nas_url, username, password, verify_ssl):
    login_url = f"{nas_url}/webapi/auth.cgi"
    params = {
        'api': 'SYNO.API.Auth',
        'version': '7',
        'method': 'login',
        'account': username,
        'passwd': password,
        'session': 'FileStation',
        'format': 'sid'
    }
    response = requests.get(login_url, params=params, verify=verify_ssl)
    response_data = response.json()
    
    if response_data['success']:
        sid = response_data['data']['sid']
        syno_token = response_data['data'].get('synotoken', None)
        return sid, syno_token
    else:
        print("Login Response:", response_data)
        raise Exception(f"Failed to login: {response_data}")

# Step 3: Function to set AFP service status using SYNO.Entry.Request
def set_afp_service_status(nas_url, sid, syno_token, enable, verify_ssl):
    afp_api_url = f"{nas_url}/webapi/entry.cgi"
    
    # Payload using SYNO.Entry.Request and compound requests
    payload = {
        'api': 'SYNO.Entry.Request',
        'version': '1',
        'method': 'request',
        'compound': json.dumps([{
            'api': 'SYNO.Core.FileServ.AFP',
            'method': 'set',
            'version': '1',
            'enable_afp': enable,
            'afp_transfer_log_enable': enable  # Optional: log transfers if AFP is enabled
        }]),
        '_sid': sid
    }

    if syno_token and syno_token != "--------":  # Only add SynoToken if it's valid
        payload['SynoToken'] = syno_token

    print("Sending AFP Set Request:", payload)

    response = requests.post(afp_api_url, data=payload, verify=verify_ssl)  # Use data=payload for form-encoded request
    return response.json()

# Step 4: Function to logout from NAS in DSM 7
def logout_from_nas(nas_url, sid, verify_ssl):
    logout_url = f"{nas_url}/webapi/auth.cgi"
    params = {
        'api': 'SYNO.API.Auth',
        'version': '7',
        'method': 'logout',
        '_sid': sid
    }
    response = requests.get(logout_url, params=params, verify=verify_ssl)
    return response.json()

# Command-line argument parsing
def parse_arguments():
    parser = argparse.ArgumentParser(description="Toggle AFP service on Synology NAS")
    
    parser.add_argument(
        "afp_toggle", 
        choices=['true', 'false'], 
        nargs='?',  
        help="Enable or disable AFP service (true/false)"
    )
    
    parser.add_argument(
        "-k", "--insecure",
        action="store_true", 
        help="Disable SSL certificate validation (like curl's -k or --insecure)"
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
    args = parse_arguments()

    nas_hostname = get_env_variable("NAS_HOSTNAME")
    nas_port = os.getenv("NAS_PORT", "5001")
    username = get_env_variable("NAS_USERNAME")
    password = get_env_variable("NAS_PASSWORD")

    nas_url = f"https://{nas_hostname}:{nas_port}"

    verify_ssl = not args.insecure

    sid = None
    syno_token = None

    try:
        sid, syno_token = login_to_nas(nas_url, username, password, verify_ssl)
        print(f"Logged in successfully. SID: {sid}, SynoToken: {syno_token if syno_token else 'None'}")
        
        enable_afp = True if args.afp_toggle == 'true' else False
        result = set_afp_service_status(nas_url, sid, syno_token, enable_afp, verify_ssl)
        print(json.dumps(result, indent=4))
        
        if result['success']:
            print(f"AFP service successfully {'enabled' if enable_afp else 'disabled'}")
        else:
            print(f"Failed to change AFP service state: {result}")

    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        if sid:
            logout_response = logout_from_nas(nas_url, sid, verify_ssl)
            print("Logged out:", logout_response)
        else:
            print("No session to log out of. Skipping logout.")

