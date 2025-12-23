"""
Patras CityBus CLI
------------------
Fetches scheduled or live bus times for Patras from the CityBus API.
Greek output supported.
"""
import argparse
import datetime
import re
import sys
import requests
import json
import pathlib
import os
from colorama import init, Fore, Back, Style
import shutil

API_URL = "https://rest.citybus.gr/api/v1/el/112/trips/stop/{stop}/day/{day}"
LIVE_URL = "https://rest.citybus.gr/api/v1/el/112/stops/live/{stop}"
STOPS_URL = "https://rest.citybus.gr/api/v1/el/112/stops"
MAIN_URL = "https://patra.citybus.gr/el/stops"

USER_DATA_DIR = os.path.join(os.path.dirname(__file__), 'user_data')
CONFIG_FILE = os.path.join(USER_DATA_DIR, 'citybus_config.json')
LINECODE_MAP_FILE = os.path.join(USER_DATA_DIR, 'linecode_map.json')
BOOKMARKS_FILE = os.path.join(USER_DATA_DIR, 'bookmarks.json')

# Ensure user_data directory exists
os.makedirs(USER_DATA_DIR, exist_ok=True)

def _make_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "https://patra.citybus.gr/",
        "Origin": "https://patra.citybus.gr"
    }

def get_bearer_token():
    """Extract Bearer token from the main website's JavaScript."""
    try:
        session = requests.Session()
        response = session.get(MAIN_URL)
        response.raise_for_status()
        match = re.search(r"const token = '([^']+)'", response.text)
        if match:
            return match.group(1)
        print("No Bearer token found in page JavaScript", file=sys.stderr)
        sys.exit(1)
    except requests.RequestException as e:
        print(f"Error getting Bearer token: {e}", file=sys.stderr)
        sys.exit(1)


def fetch_bus_times(stop, day):
    """Fetch scheduled bus times for a stop and day."""
    url = API_URL.format(stop=stop, day=day)
    headers = _make_headers()
    headers["Authorization"] = f"Bearer {get_bearer_token()}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        if response.status_code == 401:
            print('401 Unauthorized - Token may be expired', file=sys.stderr)
        else:
            print(f"Error fetching data: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.RequestException as e:
        print(f"Error fetching data: {e}", file=sys.stderr)
        sys.exit(1)


def fetch_bus_times_live(stop):
    """Fetch live bus times for a stop."""
    url = LIVE_URL.format(stop=stop)
    headers = _make_headers()
    headers["Authorization"] = f"Bearer {get_bearer_token()}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching live data: {e}", file=sys.stderr)
        sys.exit(1)


def load_config():
    """Load config from file, or return defaults."""
    defaults = {'stop': 430, 'day': 5}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding='utf-8') as f:
                data = json.load(f)
                defaults.update({k: v for k, v in data.items() if k in defaults})
        except Exception as e:
            print(f"Warning: Could not read config file: {e}", file=sys.stderr)
    return defaults


def save_config(config):
    """Save config to file."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}", file=sys.stderr)
        sys.exit(1)


def set_default_stop(stop_code):
    """Set the default stop in config."""
    config = load_config()
    config['stop'] = stop_code
    save_config(config)
    print(Fore.GREEN + f"Default stop set to {stop_code}")


def set_default_day(day):
    """Set the default day in config."""
    if day < 1 or day > 7:
        print(Fore.RED + "Error: Day must be between 1 (Monday) and 7 (Sunday)")
        sys.exit(1)
    config = load_config()
    config['day'] = day
    save_config(config)
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    print(Fore.GREEN + f"Default day set to {day} ({day_names[day-1]})")


def fetch_stop_to_name_map():
    """
    Return a dict mapping stop code to stop name.
    If user_data/stop_name.json exists, load it.
    Otherwise, fetch from the CityBus API and create it.
    """
    stop_name_path = os.path.join(USER_DATA_DIR, 'stop_name.json')
    if os.path.exists(stop_name_path):
        with open(stop_name_path, encoding='utf-8') as f:
            print('Found local cache')
            return json.load(f)
    # Fetch from the CityBus API
    url = STOPS_URL
    headers = _make_headers()
    headers["Authorization"] = f"Bearer {get_bearer_token()}"
    try:
        print('Fetching from API')
        response = requests.get(STOPS_URL, headers=headers)
        response.raise_for_status()
        stops = response.json()
    except requests.RequestException as e:
        print(f"Error fetching stops: {e}", file=sys.stderr)
        sys.exit(1)
    stop_map = {str(stop['code']): stop['name'] for stop in stops}
    with open(stop_name_path, 'w', encoding='utf-8') as f:
        json.dump(stop_map, f, ensure_ascii=False, indent=2)
    return stop_map

def print_bus_times(bus_times):
    """
    Print bus times in a table, handling both scheduled and live formats.
    """
    init(autoreset=True)
    # Fixed widths for columns
    col_names = ["Mins", "Time", "Line/Route"]
    col_widths = [4, 5, 8, 24]  # Mins, Time, Line, Route
    if not bus_times:
        print(Fore.RED + Back.BLACK + Style.BRIGHT + "No bus times found.")
        return
    if isinstance(bus_times, dict) and 'vehicles' in bus_times:
        vehicles = bus_times['vehicles']
        if not vehicles:
            print(Fore.RED + Back.BLACK + Style.BRIGHT + "No live vehicles found.")
            return
        # Header
        print(Fore.YELLOW + Style.BRIGHT + f"|{'Mins':<{col_widths[0]}}|{'Time':<{col_widths[1]}}|{'Line':<{col_widths[2]}} {'Route':<{col_widths[3]}}")
        now = datetime.datetime.now()
        for v in vehicles:
            mins = v.get('departureMins', 'N/A')
            route = v.get('routeName', 'N/A')
            linecode = str(v.get('lineCode', ''))[:col_widths[2]]
            if isinstance(mins, int) or (isinstance(mins, str) and str(mins).isdigit()):
                mins_int = int(mins)
                time_str = (now + datetime.timedelta(minutes=mins_int)).strftime('%H:%M')
                if mins_int <= 5:
                    color = Fore.RED + Style.BRIGHT
                elif mins_int <= 15:
                    color = Fore.YELLOW + Style.BRIGHT
                else:
                    color = Fore.GREEN + Style.BRIGHT
            else:
                time_str = 'N/A'
                color = Fore.WHITE + Style.BRIGHT
            line_part = Style.BRIGHT + linecode.ljust(col_widths[2]) + Style.NORMAL
            route_part = route[:col_widths[3]]
            print(color + Back.BLACK + f"|{str(mins):>{col_widths[0]}}|{time_str:<{col_widths[1]}}|{line_part} {route_part:<{col_widths[3]}}")
        return
    # Scheduled format (list)
    stop = bus_times[0].get('stopName', 'N/A')
    print(Fore.CYAN + Back.BLACK + Style.BRIGHT + stop)
    col_names = ["Time", "Line/Route"]
    col_widths = [5, 8, 24]
    print(Fore.YELLOW + Back.BLUE + Style.BRIGHT + f"|{'Time':<{col_widths[0]}}|{'Line':<{col_widths[1]}} {'Route':<{col_widths[2]}}")
    for bus in bus_times:
        time = bus.get('tripTime', 'N/A')
        route = bus.get('routeName', 'N/A')
        linecode = str(bus.get('lineCode', ''))[:col_widths[1]]
        line_part = Style.BRIGHT + linecode.ljust(col_widths[1]) + Style.NORMAL
        route_part = route[:col_widths[2]]
        print(Fore.GREEN + Back.BLACK + Style.BRIGHT + f"|{time:<{col_widths[0]}}|{line_part} {route_part:<{col_widths[2]}}")

def print_stopname_map(stopname_map, query=None):
    from colorama import Fore, Back, Style, init
    init(autoreset=True)
    col_names = ["Code", "Stop Name"]
    col_widths = [6, 32]
    print(Fore.YELLOW + Style.BRIGHT + f"|{col_names[0]:<{col_widths[0]}}|{col_names[1]:<{col_widths[1]}}")
    for code, name in stopname_map.items():
        if query and query.lower() not in name.lower():
            continue
        print(Fore.GREEN + Back.BLACK + Style.BRIGHT + f"|{code:<{col_widths[0]}}|{name[:col_widths[1]]:<{col_widths[1]}}")


def load_bookmarks():
    """Load bookmarked stops from file."""
    if os.path.exists(BOOKMARKS_FILE):
        try:
            with open(BOOKMARKS_FILE, encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not read bookmarks file: {e}", file=sys.stderr)
    return []


def save_bookmarks(bookmarks):
    """Save bookmarked stops to file."""
    try:
        with open(BOOKMARKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(bookmarks, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving bookmarks: {e}", file=sys.stderr)
        sys.exit(1)


def add_bookmark(stop_code):
    """Add a stop to bookmarks."""
    bookmarks = load_bookmarks()
    if stop_code in bookmarks:
        print(Fore.YELLOW + f"Stop {stop_code} is already bookmarked.")
        return
    bookmarks.append(stop_code)
    save_bookmarks(bookmarks)
    print(Fore.GREEN + f"Added stop {stop_code} to bookmarks.")


def list_bookmarks():
    """List all bookmarked stops with their names."""
    init(autoreset=True)
    bookmarks = load_bookmarks()
    if not bookmarks:
        print(Fore.YELLOW + "No bookmarked stops yet. Use 'citybus bookmark add <stop_code>' to add one.")
        return
    
    # Fetch stop names
    stopname_map = fetch_stop_to_name_map()
    
    col_names = ["Code", "Stop Name"]
    col_widths = [6, 40]
    print(Fore.CYAN + Style.BRIGHT + "Bookmarked Stops:")
    print(Fore.YELLOW + Style.BRIGHT + f"|{col_names[0]:<{col_widths[0]}}|{col_names[1]:<{col_widths[1]}}")
    
    for code in bookmarks:
        name = stopname_map.get(str(code), "Unknown")
        print(Fore.GREEN + Back.BLACK + Style.BRIGHT + f"|{str(code):<{col_widths[0]}}|{name[:col_widths[1]]:<{col_widths[1]}}")


def main():
    parser = argparse.ArgumentParser(
        description="Get Patras CityBus times for a stop and day.",
        epilog="""
Notes:
- Live times require internet
- Greek characters (UTF-8) supported
- If the API is unavailable, the script falls back to archived data (debug mode)
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    config = load_config()
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Stop subcommand
    stop_parser = subparsers.add_parser('stop', help='Manage default stop')
    stop_subparsers = stop_parser.add_subparsers(dest='stop_action', help='Stop actions')
    
    # stop default
    stop_default_parser = stop_subparsers.add_parser('default', help='Set default stop')
    stop_default_parser.add_argument('stop_code', type=int, help='Stop code to set as default')
    
    # Day subcommand
    day_parser = subparsers.add_parser('day', help='Manage default day')
    day_subparsers = day_parser.add_subparsers(dest='day_action', help='Day actions')
    
    # day default
    day_default_parser = day_subparsers.add_parser('default', help='Set default day')
    day_default_parser.add_argument('day_number', type=int, help='Day number (1=Monday, ..., 7=Sunday)')
    
    # Bookmark subcommand
    bookmark_parser = subparsers.add_parser('bookmark', help='Manage bookmarked stops')
    bookmark_subparsers = bookmark_parser.add_subparsers(dest='bookmark_action', help='Bookmark actions')
    
    # bookmark add
    bookmark_add_parser = bookmark_subparsers.add_parser('add', help='Add a stop to bookmarks')
    bookmark_add_parser.add_argument('stop_code', type=int, help='Stop code to bookmark')
    
    # bookmark list (default when just 'bookmark' is used)
    bookmark_list_parser = bookmark_subparsers.add_parser('list', help='List all bookmarked stops')
    
    # Main arguments (for default behavior)
    parser.add_argument('--stop', type=int, default=config['stop'], help=f'Stop ID (default: {config["stop"]})')
    parser.add_argument('--day', type=int, default=config['day'], help=f'Day of week (1=Monday, ..., 7=Sunday, default: {config["day"]})')
    parser.add_argument('--live', action='store_true', help='Show live bus times instead of scheduled')
    parser.add_argument('--names', nargs='?', const=True, default=False, help='Print the stop code-to-name map. Filter by substring if given')
    
    args = parser.parse_args()

    # Handle stop command
    if args.command == 'stop':
        if args.stop_action == 'default':
            set_default_stop(args.stop_code)
        return
    
    # Handle day command
    if args.command == 'day':
        if args.day_action == 'default':
            set_default_day(args.day_number)
        return

    # Handle bookmark command
    if args.command == 'bookmark':
        if args.bookmark_action == 'add':
            add_bookmark(args.stop_code)
        elif args.bookmark_action == 'list':
            list_bookmarks()
        else:
            # Default to list when just 'bookmark' is used
            list_bookmarks()
        return

    # Handle --names flag
    if args.names:
        stopname_map = fetch_stop_to_name_map()
        if isinstance(args.names, str):
            query = args.names
            print_stopname_map(stopname_map, query=query)
        else:
            print_stopname_map(stopname_map)
        return

    # Default behavior: show bus times
    if args.live:
        bus_times = fetch_bus_times_live(args.stop)
    else:
        bus_times = fetch_bus_times(args.stop, args.day)
    print_bus_times(bus_times)

if __name__ == "__main__":
    # Set UTF-8 encoding for stdout on Windows
    if sys.platform == "win32":
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    main()