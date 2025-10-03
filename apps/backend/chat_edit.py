#!/usr/bin/env python3
"""Edit Workflow Chat Test - drive the chat endpoint in edit/copy modes."""

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, Optional

import requests
from colorama import Fore, Style, init
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from urllib3.util.retry import Retry

# Initialize terminal colours and load environment
init(autoreset=True)
load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD")


class EditChatTester:
    """Helper around the app chat endpoint for edit/copy flows."""

    def __init__(
        self,
        action: str,
        workflow_id: str,
        show_original: bool = False,
        fetch_result: bool = False,
        print_json: bool = False,
    ) -> None:
        self.session = requests.Session()
        self.session.trust_env = False  # avoid proxy interference for localhost

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.verify = True

        self.action = action
        self.workflow_id = workflow_id
        self.show_original = show_original
        self.fetch_result = fetch_result
        self.print_json = print_json

        self.access_token: Optional[str] = None
        self.session_id: Optional[str] = None
        self.latest_workflow_id: Optional[str] = None
        self.original_workflow: Optional[Dict[str, Any]] = None

    def print_separator(self) -> None:
        print(f"{Fore.WHITE}{'─'*80}{Style.RESET_ALL}")

    def authenticate(self) -> bool:
        """Authenticate against Supabase and capture the bearer token."""
        print(f"\n{Fore.CYAN}🔐 Authenticating...{Style.RESET_ALL}")
        max_attempts = 3

        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    print(
                        f"{Fore.YELLOW}Retry attempt {attempt + 1}/{max_attempts}...{Style.RESET_ALL}"
                    )
                    time.sleep(2**attempt)

                response = self.session.post(
                    f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                    headers={
                        "apikey": SUPABASE_ANON_KEY,
                        "Content-Type": "application/json",
                        "User-Agent": "EditChatTester/1.0",
                    },
                    json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
                    timeout=(10, 30),
                )

                if response.status_code == 200:
                    auth_data = response.json()
                    self.access_token = auth_data.get("access_token")
                    if not self.access_token:
                        print(f"{Fore.RED}✗ No access token in response{Style.RESET_ALL}")
                        return False
                    preview = self.access_token[:20]
                    print(f"{Fore.GREEN}✓ Authentication successful{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}Token preview: {preview}...{Style.RESET_ALL}")
                    return True

                print(
                    f"{Fore.RED}✗ Authentication failed: {response.status_code}{Style.RESET_ALL}"
                )
                print(f"{Fore.RED}Response: {response.text[:500]}{Style.RESET_ALL}")

            except RequestException as exc:
                print(
                    f"{Fore.RED}Request error (attempt {attempt + 1}): {exc}{Style.RESET_ALL}"
                )
                if attempt == max_attempts - 1:
                    return False

        return False

    def create_session(self, retry_auth: bool = True) -> bool:
        """Create a chat session with the selected action/workflow."""
        if not self.access_token:
            print(f"{Fore.RED}✗ Missing access token; authenticate first{Style.RESET_ALL}")
            return False

        print(
            f"\n{Fore.CYAN}📝 Creating session (action={self.action}, workflow={self.workflow_id})"
            f"...{Style.RESET_ALL}"
        )

        url = f"{API_BASE_URL}/api/v1/app/sessions"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {"action": self.action, "workflow_id": self.workflow_id}

        try:
            response = self.session.post(url, headers=headers, json=payload, timeout=30)
        except RequestException as exc:
            print(f"{Fore.RED}Session request failed: {exc}{Style.RESET_ALL}")
            return False

        if response.status_code == 200:
            self.session_id = response.json()["session"]["id"]
            print(f"{Fore.GREEN}✓ Session created: {self.session_id}{Style.RESET_ALL}")
            return True

        if response.status_code == 401 and retry_auth:
            print(f"{Fore.YELLOW}Token expired, re-authenticating...{Style.RESET_ALL}")
            if self.authenticate():
                return self.create_session(retry_auth=False)
            return False

        print(f"{Fore.RED}✗ Session creation failed: {response.status_code}{Style.RESET_ALL}")
        try:
            print(f"{Fore.RED}Response text: {response.text[:500]}{Style.RESET_ALL}")
        except Exception:
            pass
        return False

    def fetch_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Fetch workflow details via the app API."""
        if not workflow_id:
            return None

        url = f"{API_BASE_URL}/api/v1/app/workflows/{workflow_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }

        try:
            response = self.session.get(url, headers=headers, timeout=30)
        except RequestException as exc:
            print(f"{Fore.RED}Failed to fetch workflow {workflow_id}: {exc}{Style.RESET_ALL}")
            return None

        if response.status_code != 200:
            print(
                f"{Fore.RED}Failed to fetch workflow {workflow_id}: {response.status_code}{Style.RESET_ALL}"
            )
            return None

        data = response.json()
        return data.get("workflow") or data

    def print_workflow_snapshot(self, workflow: Dict[str, Any], label: str) -> None:
        """Display a compact snapshot of a workflow."""
        name = workflow.get("name", "Unknown")
        workflow_id = workflow.get("workflow_id") or workflow.get("id") or "?"
        node_count = len(workflow.get("nodes", [])) if workflow.get("nodes") else 0
        description = workflow.get("description") or ""
        metadata = workflow.get("metadata") or {}
        source_id = metadata.get("source_workflow_id") or workflow.get("source_workflow_id")

        self.print_separator()
        print(f"{Fore.YELLOW}{label}{Style.RESET_ALL}")
        print(f"  ID: {workflow_id}")
        print(f"  Name: {name}")
        print(f"  Nodes: {node_count}")
        if description:
            print(f"  Description: {description}")
        if source_id:
            print(f"  Source workflow: {source_id}")
        if metadata:
            keys = ", ".join(sorted(metadata.keys()))
            print(f"  Metadata keys: {keys}")
        self.print_separator()

    def maybe_fetch_result(self, workflow_id: Optional[str]) -> None:
        if not (self.fetch_result and workflow_id):
            return

        workflow = self.fetch_workflow(workflow_id)
        if workflow:
            self.print_workflow_snapshot(workflow, f"New Workflow ({workflow_id})")

    def chat(self, message: str) -> Optional[str]:
        """Send a prompt and stream SSE responses."""
        if not self.session_id:
            print(f"{Fore.RED}✗ No session available{Style.RESET_ALL}")
            return None

        self.print_separator()
        print(f"{Fore.CYAN}USER:{Style.RESET_ALL} {message}")
        print(
            f"{Fore.YELLOW}[Mode: {self.action.upper()} | Workflow: {self.workflow_id}]{Style.RESET_ALL}"
        )
        self.print_separator()

        request_data: Dict[str, Any] = {
            "session_id": self.session_id,
            "user_message": message,
            "action": self.action,
            "workflow_id": self.workflow_id,
        }

        try:
            response = self.session.post(
                f"{API_BASE_URL}/api/v1/app/chat/stream",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
                json=request_data,
                stream=True,
                timeout=(10, 600),
            )
        except RequestException as exc:
            print(f"{Fore.RED}Chat request failed: {exc}{Style.RESET_ALL}")
            return None

        if response.status_code != 200:
            print(f"{Fore.RED}Request failed: {response.status_code}{Style.RESET_ALL}")
            try:
                print(f"{Fore.RED}Response: {response.text[:500]}{Style.RESET_ALL}")
            except Exception:
                pass
            return None

        trace_id = response.headers.get("X-Trace-ID") or response.headers.get("x-trace-id")
        if trace_id:
            print(f"{Fore.MAGENTA}Trace ID: {trace_id}{Style.RESET_ALL}")

        event_count = 0
        assistant_messages: list[str] = []
        returned_workflow_id: Optional[str] = None

        for line in response.iter_lines(chunk_size=1024, decode_unicode=False):
            if not line or not line.startswith(b"data: "):
                continue

            data_str = line[6:].decode("utf-8")
            if data_str == "[DONE]" or not data_str.strip():
                continue

            try:
                event = json.loads(data_str)
            except json.JSONDecodeError as exc:
                print(f"{Fore.RED}JSON parse error: {exc}{Style.RESET_ALL}")
                continue

            event_count += 1
            event_type = event.get("type")
            event_data = event.get("data", {})
            response_type = event.get("response_type")

            if response_type == "RESPONSE_TYPE_HEARTBEAT":
                message_text = event.get("message", "Processing...")
                print(f"{Fore.YELLOW}💓 Heartbeat: {message_text}{Style.RESET_ALL}")
                continue

            if self.print_json:
                print(f"\n{Fore.YELLOW}[SSE Event #{event_count}]{Style.RESET_ALL}")
                print(json.dumps(event, indent=2, ensure_ascii=False))

            if event_type == "status_change":
                prev_stage = event_data.get("previous_stage", "unknown")
                curr_stage = event_data.get("current_stage", "unknown")
                print(
                    f"\n{Fore.MAGENTA}>>> Status: {prev_stage} → {curr_stage}{Style.RESET_ALL}"
                )
            elif event_type == "message":
                content = event_data.get("text", "")
                if content:
                    assistant_messages.append(content)
            elif event_type == "workflow":
                workflow_info = event_data.get("workflow", {})
                returned_workflow_id = (
                    workflow_info.get("workflow_id")
                    or workflow_info.get("id")
                    or returned_workflow_id
                )
                print(
                    f"\n{Fore.GREEN}>>> Workflow {'Updated' if self.action == 'edit' else 'Created'}!{Style.RESET_ALL}"
                )
                metadata = workflow_info.get("metadata") or {}
                source_id = metadata.get("source_workflow_id") or workflow_info.get(
                    "source_workflow_id"
                )
                if source_id:
                    print(f"  Source workflow: {source_id}")
                if returned_workflow_id:
                    print(f"  New workflow ID: {returned_workflow_id}")
                print(f"  Nodes: {len(workflow_info.get('nodes', []))}")
                if self.print_json:
                    print(
                        json.dumps(
                            workflow_info,
                            indent=2,
                            ensure_ascii=False,
                        )
                    )
            elif event_type == "error":
                error_message = event_data.get("error") or event_data.get("message")
                print(f"\n{Fore.RED}>>> Error: {error_message}{Style.RESET_ALL}")

        if assistant_messages:
            self.print_separator()
            print(f"{Fore.GREEN}ASSISTANT:{Style.RESET_ALL}")
            print("".join(assistant_messages))
            self.print_separator()

        print(f"\n{Fore.CYAN}Total events: {event_count}{Style.RESET_ALL}")

        if returned_workflow_id and self.workflow_id:
            if returned_workflow_id == self.workflow_id:
                print(
                    f"{Fore.YELLOW}⚠️ Workflow ID unchanged; edit likely updated in-place.{Style.RESET_ALL}"
                )
            else:
                print(
                    f"{Fore.GREEN}✓ New workflow generated from {self.workflow_id}:{Style.RESET_ALL}"
                )
                print(f"  Original → {self.workflow_id}")
                print(f"  New      → {returned_workflow_id}")

        self.latest_workflow_id = returned_workflow_id or self.latest_workflow_id
        self.maybe_fetch_result(returned_workflow_id)
        return returned_workflow_id

    def run(self, initial_message: Optional[str]) -> None:
        """Run authentication, optional snapshot, and interactive chat."""
        print(f"\n{Fore.CYAN}{'='*80}")
        print("Workflow Edit Chat Test")
        print(f"{'='*80}{Style.RESET_ALL}")

        required_env = [SUPABASE_URL, SUPABASE_ANON_KEY, TEST_USER_EMAIL, TEST_USER_PASSWORD]
        if not all(required_env):
            print(f"{Fore.RED}Missing Supabase configuration in environment.{Style.RESET_ALL}")
            return

        if not self.authenticate():
            return

        if self.show_original:
            original = self.fetch_workflow(self.workflow_id)
            if original:
                self.original_workflow = original
                self.print_workflow_snapshot(original, "Original Workflow Snapshot")
            else:
                print(
                    f"{Fore.YELLOW}⚠️ Unable to fetch original workflow before editing.{Style.RESET_ALL}"
                )

        if not self.create_session():
            return

        if initial_message:
            print(
                f"\n{Fore.YELLOW}Sending message from command line/file...{Style.RESET_ALL}"
            )
            self.chat(initial_message)
            return

        print(f"\n{Fore.YELLOW}Ready to edit workflow. Type 'exit' to quit.{Style.RESET_ALL}")
        print(
            f"{Fore.YELLOW}Use '###' on a new line to finish multi-line input.{Style.RESET_ALL}"
        )
        print(
            f"{Fore.YELLOW}Example: Tighten the trigger schedule and update action details.{Style.RESET_ALL}\n"
        )

        while True:
            try:
                print(f"{Fore.CYAN}> {Style.RESET_ALL}", end="", flush=True)

                if not sys.stdin.isatty():
                    user_input = sys.stdin.read().strip()
                else:
                    lines = []
                    first_line = True
                    while True:
                        if not first_line:
                            print(f"{Fore.CYAN}  {Style.RESET_ALL}", end="", flush=True)
                        line = input()
                        first_line = False
                        if line.strip() == "###":
                            break
                        lines.append(line)
                        if len(lines) == 1 and line.strip() and "###" not in line:
                            break
                    user_input = "\n".join(lines).strip()

                if not user_input:
                    if not sys.stdin.isatty():
                        break
                    continue

                if user_input.lower() in {"exit", "quit"}:
                    break

                self.chat(user_input)

                if not sys.stdin.isatty():
                    break

            except (KeyboardInterrupt, EOFError):
                print(f"\n{Fore.YELLOW}Interrupted{Style.RESET_ALL}")
                break

        print(f"\n{Fore.GREEN}Edit workflow test completed!{Style.RESET_ALL}")


def load_initial_message(args: argparse.Namespace) -> Optional[str]:
    if args.message:
        return args.message
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as handle:
                return handle.read().strip()
        except FileNotFoundError:
            print(f"{Fore.RED}File not found: {args.file}{Style.RESET_ALL}")
            sys.exit(1)
        except Exception as exc:
            print(f"{Fore.RED}Error reading file: {exc}{Style.RESET_ALL}")
            sys.exit(1)
    if args.stdin or not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Workflow Edit Chat Test Client")
    parser.add_argument(
        "--workflow-id",
        required=True,
        help="Existing workflow ID to edit or copy",
    )
    parser.add_argument(
        "--action",
        choices=["edit", "copy"],
        default="edit",
        help="Set to 'copy' to clone a workflow instead of editing",
    )
    parser.add_argument("-m", "--message", help="Send a single message without interactive mode")
    parser.add_argument("-f", "--file", help="Read the message from a file")
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read the message from stdin (useful for piping)",
    )
    parser.add_argument(
        "--show-original",
        action="store_true",
        help="Fetch and display the original workflow before editing",
    )
    parser.add_argument(
        "--fetch-result",
        action="store_true",
        help="Fetch the saved workflow details after an edit completes",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Print every SSE event payload for debugging",
    )

    args = parser.parse_args()
    initial_message = load_initial_message(args)

    tester = EditChatTester(
        action=args.action,
        workflow_id=args.workflow_id,
        show_original=args.show_original,
        fetch_result=args.fetch_result,
        print_json=args.print_json,
    )
    tester.run(initial_message)


if __name__ == "__main__":
    main()
