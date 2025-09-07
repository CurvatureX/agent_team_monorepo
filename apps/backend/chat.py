#!/usr/bin/env python3
"""
Clean Chat Test - Focus on SSE messages, status changes, and assistant responses
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

import requests
from colorama import Fore, Style, init
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD")


class CleanChatTester:
    def __init__(self):
        self.session = requests.Session()
        # Bypass proxy for localhost
        self.session.trust_env = False
        self.access_token = None
        self.session_id = None

        # Configure retry strategy for SSL issues
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
        )

        # Configure SSL adapter
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # SSL configuration for potential issues
        self.session.verify = True

    def print_separator(self):
        print(f"{Fore.WHITE}{'─'*80}{Style.RESET_ALL}")

    def authenticate(self):
        """Authenticate and get access token"""
        print(f"\n{Fore.CYAN}🔐 Authenticating...{Style.RESET_ALL}")

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    print(
                        f"{Fore.YELLOW}Retry attempt {attempt + 1}/{max_attempts}...{Style.RESET_ALL}"
                    )
                    time.sleep(2**attempt)  # Exponential backoff

                response = self.session.post(
                    f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                    headers={
                        "apikey": SUPABASE_ANON_KEY,
                        "Content-Type": "application/json",
                        "User-Agent": "ChatTester/1.0",
                    },
                    json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
                    timeout=(10, 30),  # Connect timeout, read timeout
                )

                if response.status_code == 200:
                    auth_data = response.json()
                    self.access_token = auth_data.get("access_token")
                    if not self.access_token:
                        print(f"{Fore.RED}✗ No access token in response{Style.RESET_ALL}")
                        print(f"{Fore.RED}Response keys: {auth_data.keys()}{Style.RESET_ALL}")
                        return False
                    print(f"{Fore.GREEN}✓ Authentication successful{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}Token preview: {self.access_token[:20]}...{Style.RESET_ALL}")
                    return True
                else:
                    print(
                        f"{Fore.RED}✗ Authentication failed: {response.status_code}{Style.RESET_ALL}"
                    )
                    print(f"{Fore.RED}Response: {response.text[:500]}{Style.RESET_ALL}")
                    if attempt == max_attempts - 1:
                        return False

            except requests.exceptions.SSLError as e:
                print(f"{Fore.RED}SSL Error (attempt {attempt + 1}): {str(e)}{Style.RESET_ALL}")
                if attempt == max_attempts - 1:
                    print(
                        f"{Fore.RED}All authentication attempts failed due to SSL issues{Style.RESET_ALL}"
                    )
                    return False

            except requests.exceptions.RequestException as e:
                print(f"{Fore.RED}Request Error (attempt {attempt + 1}): {str(e)}{Style.RESET_ALL}")
                if attempt == max_attempts - 1:
                    return False

        return False

    def create_session(self):
        """Create chat session"""
        print(f"\n{Fore.CYAN}📝 Creating session...{Style.RESET_ALL}")
        
        url = f"{API_BASE_URL}/api/v1/app/sessions"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        
        print(f"{Fore.CYAN}Request URL: {url}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Auth header preview: Bearer {self.access_token[:30]}...{Style.RESET_ALL}")
        
        try:
            # Use session (which now has proxy disabled)
            response = self.session.post(
                url,
                headers=headers,
                json={"action": "create"},
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            print(f"{Fore.RED}Request exception: {e}{Style.RESET_ALL}")
            return False

        if response.status_code == 200:
            self.session_id = response.json()["session"]["id"]
            print(f"{Fore.GREEN}✓ Session created: {self.session_id}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}✗ Session creation failed: {response.status_code}{Style.RESET_ALL}")
            print(f"{Fore.RED}Response text: {response.text[:500]}{Style.RESET_ALL}")
            print(f"{Fore.RED}Request URL: {API_BASE_URL}/api/v1/app/sessions{Style.RESET_ALL}")
            return False

    def chat(self, message):
        """Send message and process stream"""
        self.print_separator()
        print(f"{Fore.CYAN}USER:{Style.RESET_ALL} {message}")
        self.print_separator()

        with self.session.post(
            f"{API_BASE_URL}/api/v1/app/chat/stream",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            json={"session_id": self.session_id, "user_message": message},
            stream=True,
            timeout=(
                10,
                300,
            ),  # (connection timeout, read timeout) - 10s to connect, 5 minutes to read
        ) as response:
            if response.status_code != 200:
                print(f"{Fore.RED}Request failed: {response.status_code}{Style.RESET_ALL}")
                return

            # Print tracking ID from response headers
            trace_id = response.headers.get("X-Trace-ID")
            if trace_id:
                print(f"{Fore.MAGENTA}Trace ID: {trace_id}{Style.RESET_ALL}")

            # Also check for x-tracking-id (lowercase)
            tracking_id = response.headers.get("x-tracking-id")
            if tracking_id:
                print(f"{Fore.MAGENTA}Tracking ID: {tracking_id}{Style.RESET_ALL}")

            event_count = 0
            assistant_messages = []

            # Use iter_lines with a chunk size and handle timeouts more gracefully
            for line in response.iter_lines(chunk_size=1024, decode_unicode=False):
                if line and line.startswith(b"data: "):
                    try:
                        data_str = line[6:].decode("utf-8")

                        if data_str == "[DONE]":
                            break

                        if not data_str.strip():
                            continue

                        # Parse SSE event
                        event = json.loads(data_str)
                        event_count += 1

                        # Print raw SSE message
                        print(f"\n{Fore.YELLOW}[SSE Event #{event_count}]{Style.RESET_ALL}")
                        print(json.dumps(event, indent=2, ensure_ascii=False))

                        # Handle specific event types
                        event_type = event.get("type")
                        event_data = event.get("data", {})

                        if event_type == "status_change":
                            # Highlight status transitions
                            prev = event_data.get("previous_stage", "unknown")
                            curr = event_data.get("current_stage", "unknown")
                            print(
                                f"\n{Fore.MAGENTA}>>> Status Change: {prev} → {curr}{Style.RESET_ALL}"
                            )

                        elif event_type == "message":
                            # Collect assistant messages
                            content = event_data.get("text", "")
                            if content:
                                assistant_messages.append(content)

                        elif event_type == "workflow":
                            print(f"\n{Fore.GREEN}>>> Workflow Generated!{Style.RESET_ALL}")

                        elif event_type == "error":
                            print(
                                f"\n{Fore.RED}>>> Error: {event_data.get('error', 'Unknown')}{Style.RESET_ALL}"
                            )

                        # Handle heartbeat messages to show progress
                        elif event.get("response_type") == "RESPONSE_TYPE_HEARTBEAT":
                            print(
                                f"{Fore.YELLOW}💓 Heartbeat: {event.get('message', 'Processing...')}{Style.RESET_ALL}"
                            )

                    except json.JSONDecodeError as e:
                        print(f"{Fore.RED}JSON parse error: {e}{Style.RESET_ALL}")

            # Print complete assistant response
            if assistant_messages:
                self.print_separator()
                print(f"{Fore.GREEN}ASSISTANT:{Style.RESET_ALL}")
                full_message = "".join(assistant_messages)
                print(full_message)
                self.print_separator()

            print(f"\n{Fore.CYAN}Total events: {event_count}{Style.RESET_ALL}")

    def run(self, initial_message=None):
        """Run the test"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print("Workflow Chat Test - Clean Output")
        print(f"{'='*80}{Style.RESET_ALL}")

        if not all([SUPABASE_URL, SUPABASE_ANON_KEY, TEST_USER_EMAIL, TEST_USER_PASSWORD]):
            print(f"{Fore.RED}Missing required environment variables!{Style.RESET_ALL}")
            return

        if not self.authenticate():
            return

        if not self.create_session():
            return

        # If initial message provided via command line, send it directly
        if initial_message:
            print(f"\n{Fore.YELLOW}Sending message from command line/file...{Style.RESET_ALL}")
            self.chat(initial_message)
            return

        print(f"\n{Fore.YELLOW}Ready to chat. Type 'exit' to quit.{Style.RESET_ALL}")
        print(
            f"{Fore.YELLOW}For multi-line input: End your message with '###' on a new line{Style.RESET_ALL}"
        )
        print(
            f"{Fore.YELLOW}Example: Send a HTTP request to https://google.com every 5 minutes{Style.RESET_ALL}\n"
        )

        while True:
            try:
                print(f"\n{Fore.CYAN}> {Style.RESET_ALL}", end="")

                # Check if input is being piped
                if not sys.stdin.isatty():
                    # Read all piped input
                    user_input = sys.stdin.read().strip()
                else:
                    # Interactive mode - support multi-line with ### terminator
                    lines = []
                    first_line = True
                    while True:
                        if not first_line:
                            print(f"{Fore.CYAN}  {Style.RESET_ALL}", end="")
                        line = input()
                        first_line = False

                        if line.strip() == "###":
                            break
                        lines.append(line)

                        # Single line mode - if no ### needed
                        if len(lines) == 1 and not line.endswith("\\"):
                            # Check if this looks like a complete single-line message
                            if "###" not in line:
                                break

                    user_input = "\n".join(lines).strip()

                if user_input.lower() in ["exit", "quit"]:
                    break
                if user_input:
                    self.chat(user_input)
            except (KeyboardInterrupt, EOFError):
                print(f"\n{Fore.YELLOW}Interrupted{Style.RESET_ALL}")
                break

        print(f"\n{Fore.GREEN}Test completed!{Style.RESET_ALL}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Workflow Chat Test Client")
    parser.add_argument("-m", "--message", help="Send a message directly without interactive mode")
    parser.add_argument("-f", "--file", help="Read message from a file")
    parser.add_argument("--stdin", action="store_true", help="Read message from stdin (for piping)")

    args = parser.parse_args()

    tester = CleanChatTester()

    # Determine input source
    initial_message = None

    if args.message:
        initial_message = args.message
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                initial_message = f.read().strip()
        except FileNotFoundError:
            print(f"{Fore.RED}File not found: {args.file}{Style.RESET_ALL}")
            sys.exit(1)
        except Exception as e:
            print(f"{Fore.RED}Error reading file: {e}{Style.RESET_ALL}")
            sys.exit(1)
    elif args.stdin or not sys.stdin.isatty():
        # Read from stdin if --stdin flag or input is piped
        initial_message = sys.stdin.read().strip()

    tester.run(initial_message)
