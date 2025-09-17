"""
Unicode Utilities for Workflow Engine

Provides robust Unicode handling to prevent JSON serialization errors,
especially the dreaded "low surrogate" issues that occur with UTF-16.

The strategy is simple: Force UTF-8 encoding throughout and remove
any characters that could cause JSON serialization issues.
"""

import json
import re
from typing import Any, Dict, List, Union


def clean_unicode_string(text: str) -> str:
    """
    Robust Unicode cleaning that avoids surrogate pair issues entirely.

    The strategy: Force UTF-8 encoding throughout and remove any characters
    that could cause JSON serialization issues.

    Args:
        text: Input string that may contain problematic Unicode

    Returns:
        Clean string safe for JSON serialization
    """
    if not text:
        return text

    try:
        # Strategy 1: Force UTF-8 byte-level cleaning
        # This completely avoids UTF-16 surrogate pair issues

        # Step 1: Convert to bytes using UTF-8, replacing any invalid sequences
        utf8_bytes = text.encode("utf-8", errors="replace")

        # Step 2: Decode back to string, ensuring valid UTF-8
        cleaned = utf8_bytes.decode("utf-8", errors="replace")

        # Step 3: Remove control characters and other problematic chars

        # Remove NULL bytes and control characters (except tab, newline, carriage return)
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", cleaned)

        # Remove Unicode non-characters and private use characters that cause issues
        cleaned = re.sub(r"[\uFDD0-\uFDEF\uFFFE\uFFFF]", "\uFFFD", cleaned)

        # Step 4: Test JSON serialization with ensure_ascii=True
        # This is the ultimate test - if it works, we're good
        json.dumps(cleaned, ensure_ascii=True)

        return cleaned

    except Exception:
        # If anything fails, fall back to aggressive ASCII-only cleaning
        try:
            # Convert to ASCII, replacing non-ASCII characters
            ascii_only = text.encode("ascii", errors="replace").decode("ascii")

            # Remove control characters from ASCII version
            ascii_cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", ascii_only)

            # Final test
            json.dumps(ascii_cleaned, ensure_ascii=True)

            return ascii_cleaned if ascii_cleaned else "[CONTENT_PROCESSED]"

        except Exception:
            # Ultimate fallback
            return "[UNICODE_PROCESSING_ERROR]"


def clean_unicode_data(data: Any) -> Any:
    """
    Recursively clean Unicode in any data structure.

    Args:
        data: Any data structure (dict, list, str, etc.)

    Returns:
        Cleaned data structure safe for JSON serialization
    """
    if isinstance(data, str):
        return clean_unicode_string(data)
    elif isinstance(data, dict):
        return {clean_unicode_string(str(k)): clean_unicode_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_unicode_data(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(clean_unicode_data(item) for item in data)
    else:
        # For other types (int, float, bool, None), return as-is
        return data


def _sanitize_surrogate_escapes(json_text: str) -> str:
    """
    Replace unpaired UTF-16 surrogate escapes (e.g. "\uD83D" without a following low surrogate)
    with the Unicode replacement character to avoid downstream API rejections.
    Operates on the JSON-encoded string.
    """
    # Unpaired high surrogates: \uD800-\uDBFF not followed by a low surrogate
    json_text = re.sub(
        r"\\uD[89ABab][0-9A-Fa-f]{2}(?!\\uD[C-Fc-f][0-9A-Fa-f]{2})", r"\\uFFFD", json_text
    )
    # Unpaired low surrogates: \uDC00-\uDFFF not preceded by a high surrogate
    json_text = re.sub(
        r"(?<!\\uD[89ABab][0-9A-Fa-f]{2})\\uD[C-Fc-f][0-9A-Fa-f]{2}", r"\\uFFFD", json_text
    )
    return json_text


def safe_json_dumps(data: Any, **kwargs) -> str:
    """
    JSON dumps with automatic Unicode cleaning.

    Args:
        data: Data to serialize
        **kwargs: Additional arguments to json.dumps

    Returns:
        JSON string, guaranteed to serialize without Unicode errors
    """
    try:
        # First try with original data
        dumped = json.dumps(data, ensure_ascii=True, **kwargs)
        return _sanitize_surrogate_escapes(dumped)
    except (UnicodeEncodeError, UnicodeDecodeError, TypeError, ValueError):
        # If error, clean the data and try again
        cleaned_data = clean_unicode_data(data)
        dumped = json.dumps(cleaned_data, ensure_ascii=True, **kwargs)
        return _sanitize_surrogate_escapes(dumped)


def safe_json_loads(text: str) -> Any:
    """
    JSON loads with automatic Unicode cleaning.

    Args:
        text: JSON string that may contain problematic Unicode

    Returns:
        Parsed JSON data
    """
    try:
        # First try with original text
        return json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError):
        # If Unicode error, clean the text and try again
        cleaned_text = clean_unicode_string(text)
        return json.loads(cleaned_text)


def ensure_utf8_safe_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure a dictionary is completely UTF-8 safe.

    This is useful for request/response data before sending to APIs.

    Args:
        data: Dictionary to clean

    Returns:
        UTF-8 safe dictionary
    """
    return clean_unicode_data(data)


def test_unicode_safety():
    """Test function to verify Unicode cleaning works."""
    test_cases = [
        "Hello world",  # Normal text
        "Hello 世界",  # Unicode text
        "Test\x00null",  # NULL byte
        "Control\x1fchar",  # Control character
        # Note: We can't include actual surrogate pairs in source code
        # as they would break the file itself
    ]

    for test_text in test_cases:
        cleaned = clean_unicode_string(test_text)
        try:
            json.dumps(cleaned, ensure_ascii=True)
            print(f"✅ Safe: '{test_text}' -> '{cleaned}'")
        except Exception as e:
            print(f"❌ Failed: '{test_text}' -> '{cleaned}' - {e}")


if __name__ == "__main__":
    test_unicode_safety()
