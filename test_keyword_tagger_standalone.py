#!/usr/bin/env python3
"""
Standalone test for keyword tagging functionality

Tests the keyword data loading and HTML tagging capabilities.
"""

import os
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_keyword_database_loading():
    """Test loading keyword database from CSV"""
    print("\n=== Test: Keyword Database Loading ===")

    from preprocessor.models.keyword_data import KeywordDatabase

    csv_path = os.path.join(
        os.path.dirname(__file__), "preprocessor", "data", "keywords.csv"
    )

    if not os.path.exists(csv_path):
        print(f"❌ Keywords CSV not found at: {csv_path}")
        return False

    db = KeywordDatabase.from_csv_file(csv_path)

    print(f"✅ Loaded database: {db}")
    print(f"   Languages: {db.languages}")
    print(f"   Total entries: {len(db)}")

    # Test keyword lookup
    en_keywords = db.get_keywords_for_language("en")
    print(f"   English keywords: {len(en_keywords)}")

    # Find pregnancy-related keywords
    pregnancy_concept = db.find_keyword("Pregnancy", "en")
    if pregnancy_concept:
        print(
            f"   Found 'Pregnancy': class={pregnancy_concept.css_class}, code={pregnancy_concept.code}"
        )

    return True


def test_keyword_matching():
    """Test keyword matching in text"""
    print("\n=== Test: Keyword Matching ===")

    from preprocessor.models.keyword_data import KeywordDatabase

    csv_path = os.path.join(
        os.path.dirname(__file__), "preprocessor", "data", "keywords.csv"
    )

    db = KeywordDatabase.from_csv_file(csv_path)

    # Test text with keywords
    test_text = (
        "This medication should not be used during pregnancy or while breastfeeding."
    )

    matches = db.find_keywords_in_text(test_text, "en")

    print(f"   Text: '{test_text}'")
    print(f"   Matches found: {len(matches)}")

    for match in matches:
        print(f"      - {match.keyword} (class: {match.css_class})")

    return len(matches) > 0


def test_html_tagging():
    """Test HTML tagging with keywords"""
    print("\n=== Test: HTML Tagging ===")

    from preprocessor.models.keyword_data import KeywordDatabase, set_default_database
    from preprocessor.models.keyword_tagger import tag_html_with_keywords

    csv_path = os.path.join(
        os.path.dirname(__file__), "preprocessor", "data", "keywords.csv"
    )

    db = KeywordDatabase.from_csv_file(csv_path)
    set_default_database(db)

    # Test HTML
    test_html = """
    <div xmlns="http://www.w3.org/1999/xhtml">
        <p>This medication should not be used during pregnancy.</p>
        <p>Do not use if you are breast feeding.</p>
        <ul>
            <li>Patients with hypertension should consult their doctor.</li>
            <li>Children under 12 years should not take this medicine.</li>
        </ul>
    </div>
    """

    result = tag_html_with_keywords(test_html, "en", db, check_readability=False)

    print(f"   Total matches: {result.total_matches}")
    print(f"   Unique keywords: {result.unique_keywords}")
    print(f"   Concepts found: {len(result.concepts)}")

    for keyword, count in result.matches.items():
        print(f"      - {keyword}: {count}")

    # Check if classes were added
    if "pregnancy" in result.tagged_html:
        print("   ✅ HTML was tagged successfully")
    else:
        print("   ❌ HTML tagging may have issues")

    return result.total_matches > 0


def test_composition_tagging():
    """Test tagging a FHIR Composition"""
    print("\n=== Test: Composition Tagging ===")

    from preprocessor.models.keyword_data import KeywordDatabase, set_default_database
    from preprocessor.models.keyword_tagger import (
        add_extension_for_concepts,
        tag_composition_sections,
    )

    csv_path = os.path.join(
        os.path.dirname(__file__), "preprocessor", "data", "keywords.csv"
    )

    db = KeywordDatabase.from_csv_file(csv_path)
    set_default_database(db)

    # Mock Composition resource
    composition = {
        "resourceType": "Composition",
        "language": "en",
        "section": [
            {
                "title": "What is in this leaflet",
                "text": {
                    "status": "extensions",
                    "div": "<div><p>Information about pregnancy precautions.</p></div>",
                },
                "section": [
                    {
                        "title": "Subsection",
                        "text": {
                            "status": "extensions",
                            "div": "<div><p>Children should not use this medicine.</p></div>",
                        },
                    }
                ],
            },
            {
                "title": "Contraindications",
                "text": {
                    "status": "extensions",
                    "div": "<div><p>Not for use during breast feeding.</p></div>",
                },
            },
        ],
    }

    result = tag_composition_sections(composition, "en", db, check_readability=False)

    print(f"   Total matches: {result.total_matches}")
    print(f"   Concepts found: {len(result.concepts)}")

    # Add extensions
    num_extensions = add_extension_for_concepts(composition, result.concepts)
    print(f"   Extensions added: {num_extensions}")

    # Check extensions
    extensions = composition.get("extension", [])
    print(f"   Total extensions in composition: {len(extensions)}")

    return result.total_matches > 0


def test_full_bundle_preprocessing():
    """Test full bundle preprocessing pipeline"""
    print("\n=== Test: Full Bundle Preprocessing ===")

    from preprocessor.models.keyword_data import KeywordDatabase, set_default_database
    from preprocessor.models.keyword_tagger import preprocess_epi_with_keywords

    csv_path = os.path.join(
        os.path.dirname(__file__), "preprocessor", "data", "keywords.csv"
    )

    db = KeywordDatabase.from_csv_file(csv_path)
    set_default_database(db)

    # Mock Bundle
    bundle = {
        "resourceType": "Bundle",
        "type": "document",
        "entry": [
            {
                "resource": {
                    "resourceType": "Composition",
                    "language": "en",
                    "section": [
                        {
                            "title": "Safety",
                            "text": {
                                "status": "extensions",
                                "div": "<div><p>Do not use during pregnancy. Patients with diabetes should monitor blood sugar.</p></div>",
                            },
                        }
                    ],
                }
            }
        ],
    }

    # Process the bundle
    processed = preprocess_epi_with_keywords(bundle, "en", db, check_readability=False)

    # Check if extensions were added
    composition = processed["entry"][0]["resource"]
    extensions = composition.get("extension", [])

    print("   Bundle processed successfully")
    print(f"   Extensions added: {len(extensions)}")

    for ext in extensions:
        if ext.get("url", "").endswith("HtmlElementLink"):
            for inner_ext in ext.get("extension", []):
                if inner_ext.get("url") == "elementClass":
                    print(f"      - Class: {inner_ext.get('valueString')}")

    return len(extensions) > 0


def main():
    """Run all tests"""
    print("=" * 60)
    print("Keyword Tagger Standalone Tests")
    print("=" * 60)

    tests = [
        ("Keyword Database Loading", test_keyword_database_loading),
        ("Keyword Matching", test_keyword_matching),
        ("HTML Tagging", test_html_tagging),
        ("Composition Tagging", test_composition_tagging),
        ("Full Bundle Preprocessing", test_full_bundle_preprocessing),
    ]

    results = []

    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback

            traceback.print_exc()
            results.append((name, False))

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status}: {name}")
        if success:
            passed += 1
        else:
            failed += 1

    print(f"\n   Total: {passed} passed, {failed} failed")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
