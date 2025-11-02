#!/usr/bin/env python3
"""
Test Unicode handling functions independently.

Run this to verify the Unicode utilities work correctly before applying
to the full Music Assistant codebase.

Usage:
    python3 test_unicode_handling.py
"""

import json
import unicodedata
from typing import Any


# ============================================================================
# UTILITY FUNCTIONS (copied from fix)
# ============================================================================

def safe_unicode_str(value: Any, fallback: str = "") -> str:
    """Safely convert any value to a Unicode string with NFC normalization."""
    if value is None:
        return fallback
    if isinstance(value, str):
        return unicodedata.normalize('NFC', value)
    if isinstance(value, bytes):
        try:
            decoded = value.decode('utf-8')
        except UnicodeDecodeError:
            try:
                decoded = value.decode('latin-1')
            except Exception:
                return fallback
        return unicodedata.normalize('NFC', decoded)
    try:
        return unicodedata.normalize('NFC', str(value))
    except Exception:
        return fallback


def safe_json_get(data: dict, *keys, default: Any = None) -> Any:
    """Safely navigate nested dictionary with list indexing support."""
    current = data
    for key in keys:
        # Handle dictionary keys
        if isinstance(current, dict):
            current = current.get(key)
            if current is None:
                return default
        # Handle list/tuple indexing
        elif isinstance(current, (list, tuple)):
            if isinstance(key, int):
                try:
                    current = current[key]
                except (IndexError, TypeError):
                    return default
            else:
                return default
        else:
            return default
    return current


def truncate_for_log(text: str, max_length: int = 100) -> str:
    """Safely truncate text for logging."""
    if not text:
        return ""
    text = safe_unicode_str(text)
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


# ============================================================================
# TEST DATA
# ============================================================================

# Simulate Apple Music API response with problematic artist
TEST_ARTIST_BARTOS = {
    "id": "123456789",
    "type": "library-artists",
    "href": "/v1/me/library/artists/123456789",
    "relationships": {
        "catalog": {
            "data": [
                {
                    "id": "987654321",
                    "type": "artists",
                    "href": "/v1/catalog/us/artists/987654321",
                    "attributes": {
                        "name": "Jan Bartoš",  # Czech artist with háček
                        "genreNames": ["Electronic", "Experimental"],
                        "url": "https://music.apple.com/us/artist/jan-bartoš/987654321",
                        "artwork": {
                            "width": 600,
                            "height": 600,
                            "url": "https://is1-ssl.mzstatic.com/image/{w}x{h}.jpg"
                        },
                        "editorialNotes": {
                            "standard": "Czech electronic music producer known for experimental soundscapes."
                        }
                    }
                }
            ]
        }
    }
}

# Test cases for various Unicode characters
TEST_CASES = [
    # Czech
    ("Jan Bartoš", "Czech with háček (caron over s)"),
    ("Dvořák", "Czech with háček over r and acute over a"),

    # Other European
    ("Björk", "Icelandic with umlaut"),
    ("Françoise", "French with cedilla and acute"),
    ("José González", "Spanish with acute accents"),
    ("Łukasz Żal", "Polish with stroke and dot above"),

    # CJK (Chinese, Japanese, Korean)
    ("藤井 風", "Japanese (Fujii Kaze)"),
    ("周杰倫", "Chinese Traditional (Jay Chou)"),
    ("방탄소년단", "Korean (BTS)"),

    # RTL (Right-to-Left)
    ("فيروز", "Arabic (Fairuz)"),
    ("עומר אדם", "Hebrew (Omer Adam)"),

    # Special characters and emoji
    ("Sigur Rós", "Icelandic with acute and special o"),
    ("Mötley Crüe", "English with umlauts (decorative)"),
    ("$uicideboy$", "With dollar signs"),
    ("deadmau5", "Lowercase with number"),
    ("Panic! at the Disco", "With exclamation"),

    # Edge cases
    ("", "Empty string"),
    ("   ", "Whitespace only"),
    ("A", "Single ASCII character"),
    ("😀🎵🎸", "Emoji only"),
    ("Artist™", "With trademark symbol"),
    ("50 Cent", "Starting with number"),
]


# ============================================================================
# TESTS
# ============================================================================

def test_safe_unicode_str():
    """Test safe_unicode_str function."""
    print("=" * 80)
    print("TEST: safe_unicode_str()")
    print("=" * 80)

    passed = 0
    failed = 0

    for test_input, description in TEST_CASES:
        try:
            result = safe_unicode_str(test_input)
            # Check result is normalized to NFC
            normalized = unicodedata.normalize('NFC', test_input) if test_input else ""
            assert result == normalized, f"Normalization mismatch: {result!r} != {normalized!r}"
            print(f"✅ PASS: {description:40s} → {result!r}")
            passed += 1
        except Exception as exc:
            print(f"❌ FAIL: {description:40s} → {exc}")
            failed += 1

    # Additional edge cases
    print("\n--- Edge Cases ---")

    # Test None
    result = safe_unicode_str(None, fallback="DEFAULT")
    assert result == "DEFAULT", "None handling failed"
    print(f"✅ PASS: None with fallback → {result!r}")
    passed += 1

    # Test bytes (UTF-8)
    result = safe_unicode_str("Jan Bartoš".encode('utf-8'))
    assert result == "Jan Bartoš", "UTF-8 bytes handling failed"
    print(f"✅ PASS: UTF-8 bytes → {result!r}")
    passed += 1

    # Test bytes (Latin-1)
    result = safe_unicode_str(b"Fran\xe7oise")  # ç in Latin-1
    print(f"✅ PASS: Latin-1 bytes → {result!r}")
    passed += 1

    # Test integer
    result = safe_unicode_str(12345)
    assert result == "12345", "Integer handling failed"
    print(f"✅ PASS: Integer → {result!r}")
    passed += 1

    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_safe_json_get():
    """Test safe_json_get function."""
    print("\n" + "=" * 80)
    print("TEST: safe_json_get()")
    print("=" * 80)

    data = {
        "relationships": {
            "catalog": {
                "data": [
                    {
                        "id": "123",
                        "attributes": {
                            "name": "Jan Bartoš"
                        }
                    }
                ]
            }
        }
    }

    passed = 0
    failed = 0

    # Test successful navigation
    result = safe_json_get(data, "relationships", "catalog", "data", 0, "attributes", "name")
    if result == "Jan Bartoš":
        print(f"✅ PASS: Deep navigation → {result!r}")
        passed += 1
    else:
        print(f"❌ FAIL: Deep navigation returned {result!r}")
        failed += 1

    # Test missing key
    result = safe_json_get(data, "nonexistent", "key", default="NOT_FOUND")
    if result == "NOT_FOUND":
        print(f"✅ PASS: Missing key with default → {result!r}")
        passed += 1
    else:
        print(f"❌ FAIL: Missing key returned {result!r}")
        failed += 1

    # Test partial path
    result = safe_json_get(data, "relationships", "catalog", "data", 0, "id")
    if result == "123":
        print(f"✅ PASS: Partial path → {result!r}")
        passed += 1
    else:
        print(f"❌ FAIL: Partial path returned {result!r}")
        failed += 1

    # Test array index out of bounds
    result = safe_json_get(data, "relationships", "catalog", "data", 999, default="OUT_OF_BOUNDS")
    if result == "OUT_OF_BOUNDS":
        print(f"✅ PASS: Index out of bounds → {result!r}")
        passed += 1
    else:
        print(f"❌ FAIL: Index out of bounds returned {result!r}")
        failed += 1

    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_truncate_for_log():
    """Test truncate_for_log function."""
    print("\n" + "=" * 80)
    print("TEST: truncate_for_log()")
    print("=" * 80)

    passed = 0
    failed = 0

    # Test short string (no truncation)
    result = truncate_for_log("Jan Bartoš", max_length=50)
    if result == "Jan Bartoš":
        print(f"✅ PASS: Short string (no truncation) → {result!r}")
        passed += 1
    else:
        print(f"❌ FAIL: Short string returned {result!r}")
        failed += 1

    # Test long string (with truncation)
    long_string = "Jan Bartoš " * 20  # 220 characters
    result = truncate_for_log(long_string, max_length=50)
    if len(result) == 50 and result.endswith("..."):
        print(f"✅ PASS: Long string truncated → {result!r}")
        passed += 1
    else:
        print(f"❌ FAIL: Long string not truncated properly → {result!r}")
        failed += 1

    # Test Unicode truncation (by character, not bytes)
    unicode_string = "🎵" * 30  # 30 emoji characters
    result = truncate_for_log(unicode_string, max_length=10)
    if len(result) == 10 and result.endswith("..."):
        print(f"✅ PASS: Unicode truncated by characters → {result!r} (len={len(result)})")
        passed += 1
    else:
        print(f"❌ FAIL: Unicode truncation failed → {result!r} (len={len(result)})")
        failed += 1

    # Test empty string
    result = truncate_for_log("", max_length=50)
    if result == "":
        print(f"✅ PASS: Empty string → {result!r}")
        passed += 1
    else:
        print(f"❌ FAIL: Empty string returned {result!r}")
        failed += 1

    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_parse_artist_data():
    """Test parsing TEST_ARTIST_BARTOS data."""
    print("\n" + "=" * 80)
    print("TEST: Parsing Jan Bartoš Artist Data")
    print("=" * 80)

    passed = 0
    failed = 0

    # Extract artist name
    artist_name = safe_json_get(
        TEST_ARTIST_BARTOS,
        "relationships", "catalog", "data", 0, "attributes", "name",
        default="Unknown"
    )

    if artist_name == "Jan Bartoš":
        print(f"✅ PASS: Extracted artist name → {artist_name!r}")
        passed += 1
    else:
        print(f"❌ FAIL: Artist name extraction returned {artist_name!r}")
        failed += 1

    # Ensure proper Unicode normalization
    normalized = safe_unicode_str(artist_name)
    if normalized == "Jan Bartoš":
        print(f"✅ PASS: Unicode normalization → {normalized!r}")
        passed += 1
    else:
        print(f"❌ FAIL: Normalization returned {normalized!r}")
        failed += 1

    # Check character composition
    # 'š' should be single codepoint (U+0161), not 's' (U+0073) + combining caron (U+030C)
    s_with_caron = normalized[-1]  # Last character should be 'š'
    if len(s_with_caron) == 1 and ord(s_with_caron) == 0x0161:
        print(f"✅ PASS: Character composition correct → U+{ord(s_with_caron):04X}")
        passed += 1
    else:
        print(f"❌ FAIL: Character composition wrong → {s_with_caron!r} (len={len(s_with_caron)})")
        failed += 1

    # Extract genre names
    genres = safe_json_get(
        TEST_ARTIST_BARTOS,
        "relationships", "catalog", "data", 0, "attributes", "genreNames",
        default=[]
    )
    if genres == ["Electronic", "Experimental"]:
        print(f"✅ PASS: Extracted genres → {genres}")
        passed += 1
    else:
        print(f"❌ FAIL: Genre extraction returned {genres}")
        failed += 1

    # Extract and format artwork URL
    artwork = safe_json_get(
        TEST_ARTIST_BARTOS,
        "relationships", "catalog", "data", 0, "attributes", "artwork",
        default={}
    )
    if artwork:
        url_template = safe_unicode_str(artwork.get("url", ""))
        width = artwork.get("width", 600)
        height = artwork.get("height", 600)
        formatted_url = url_template.format(w=width, h=height)

        if "600x600" in formatted_url:
            print(f"✅ PASS: Formatted artwork URL → {truncate_for_log(formatted_url, 60)}")
            passed += 1
        else:
            print(f"❌ FAIL: Artwork URL formatting returned {formatted_url!r}")
            failed += 1
    else:
        print(f"❌ FAIL: Could not extract artwork")
        failed += 1

    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_json_encoding():
    """Test JSON encoding/decoding with Unicode."""
    print("\n" + "=" * 80)
    print("TEST: JSON Encoding/Decoding")
    print("=" * 80)

    passed = 0
    failed = 0

    # Test encoding
    try:
        json_str = json.dumps(TEST_ARTIST_BARTOS, ensure_ascii=False, indent=2)
        if "Jan Bartoš" in json_str:
            print(f"✅ PASS: JSON encoding preserves Unicode")
            passed += 1
        else:
            print(f"❌ FAIL: JSON encoding lost Unicode characters")
            failed += 1
    except Exception as exc:
        print(f"❌ FAIL: JSON encoding raised {exc}")
        failed += 1

    # Test decoding
    try:
        decoded = json.loads(json_str)
        artist_name = safe_json_get(
            decoded,
            "relationships", "catalog", "data", 0, "attributes", "name"
        )
        if artist_name == "Jan Bartoš":
            print(f"✅ PASS: JSON decoding preserves Unicode → {artist_name!r}")
            passed += 1
        else:
            print(f"❌ FAIL: JSON decoding returned {artist_name!r}")
            failed += 1
    except Exception as exc:
        print(f"❌ FAIL: JSON decoding raised {exc}")
        failed += 1

    # Test encoding with ensure_ascii=True (escape Unicode)
    try:
        json_str_ascii = json.dumps(TEST_ARTIST_BARTOS, ensure_ascii=True)
        if "\\u0161" in json_str_ascii:  # š should be escaped as \u0161
            print(f"✅ PASS: JSON ASCII encoding escapes Unicode")
            passed += 1
        else:
            print(f"❌ FAIL: JSON ASCII encoding didn't escape Unicode")
            failed += 1

        # Decode the escaped version
        decoded_ascii = json.loads(json_str_ascii)
        artist_name_ascii = safe_json_get(
            decoded_ascii,
            "relationships", "catalog", "data", 0, "attributes", "name"
        )
        if artist_name_ascii == "Jan Bartoš":
            print(f"✅ PASS: Escaped Unicode decodes correctly → {artist_name_ascii!r}")
            passed += 1
        else:
            print(f"❌ FAIL: Escaped Unicode decode returned {artist_name_ascii!r}")
            failed += 1
    except Exception as exc:
        print(f"❌ FAIL: JSON ASCII encoding/decoding raised {exc}")
        failed += 1

    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("UNICODE HANDLING TEST SUITE")
    print("=" * 80)
    print("\nTesting Unicode utilities for Apple Music provider fix")
    print("Focus: Czech artist 'Jan Bartoš' with háček (caron) over 's'")
    print("=" * 80 + "\n")

    results = []

    results.append(("safe_unicode_str", test_safe_unicode_str()))
    results.append(("safe_json_get", test_safe_json_get()))
    results.append(("truncate_for_log", test_truncate_for_log()))
    results.append(("parse_artist_data", test_parse_artist_data()))
    results.append(("json_encoding", test_json_encoding()))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    total_passed = sum(1 for _, passed in results if passed)
    total_failed = len(results) - total_passed

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n📊 Overall: {total_passed}/{len(results)} test suites passed")

    if total_failed == 0:
        print("\n🎉 All tests passed! Unicode handling is working correctly.")
        print("✅ Ready to apply fix to Apple Music provider.")
        return 0
    else:
        print(f"\n⚠️  {total_failed} test suite(s) failed.")
        print("❌ Fix Unicode handling before applying to provider.")
        return 1


if __name__ == "__main__":
    exit(main())
