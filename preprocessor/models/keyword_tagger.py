"""
Keyword Tagger Module

Tags HTML content with CSS classes based on keyword matches.
Integrates with the HtmlElementLink extension system.

This module refactors the original fhir-epi-tools/preprocessor code
to work with the preprocessing-service architecture.
"""

from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

from preprocessor.models.html_element_link import (
    CodeableReference,
    Coding,
)
from preprocessor.models.html_element_link_manager import add_html_element_link
from preprocessor.models.keyword_data import (
    KeywordConcept,
    KeywordDatabase,
    get_default_database,
)

# Optional: Readability analysis for difficult text detection
try:
    import textstat

    HAS_TEXTSTAT = True
except ImportError:
    HAS_TEXTSTAT = False


# Default settings for readability analysis
READABILITY_THRESHOLD = 20  # Flesch Reading Ease: lower = harder
READABILITY_LENGTH_THRESHOLD = 100  # Minimum text length for readability check
DIFFICULT_CSS_CLASS = "difficult"
DIFFICULT_CODE = "diff001"
DIFFICULT_SYSTEM = "http://hl7.eu/fhir/ig/gravitate-health/CodeSystem/difficulty"
DIFFICULT_DISPLAY = "Difficult text"


class TaggingResult:
    """
    Result of a tagging operation

    Attributes:
        tagged_html: The HTML with CSS classes added
        matches: Counter of keyword matches {keyword: count}
        concepts: List of unique KeywordConcept objects found
        difficult_sections: Number of sections flagged as difficult
    """

    def __init__(self):
        self.tagged_html: str = ""
        self.matches: Counter = Counter()
        self.concepts: List[KeywordConcept] = []
        self.difficult_sections: int = 0

    @property
    def total_matches(self) -> int:
        """Get total number of matches"""
        return sum(self.matches.values())

    @property
    def unique_keywords(self) -> int:
        """Get number of unique keywords matched"""
        return len(self.matches)

    def __repr__(self):
        return f"TaggingResult(matches={self.total_matches}, unique={self.unique_keywords}, difficult={self.difficult_sections})"


def tag_html_with_keywords(
    html: str,
    language: str,
    keyword_db: Optional[KeywordDatabase] = None,
    check_readability: bool = True,
    readability_threshold: float = READABILITY_THRESHOLD,
    readability_length_threshold: int = READABILITY_LENGTH_THRESHOLD,
) -> TaggingResult:
    """
    Tag HTML elements with CSS classes based on keyword matches

    Processes HTML from deepest elements first to avoid double-tagging.
    Adds CSS classes to elements containing matched keywords.

    Args:
        html: HTML content to process
        language: Language code (e.g., 'en', 'es', 'pt')
        keyword_db: KeywordDatabase to use (uses default if None)
        check_readability: Whether to check for difficult text
        readability_threshold: Flesch Reading Ease threshold (lower = harder)
        readability_length_threshold: Minimum text length for readability check

    Returns:
        TaggingResult with tagged HTML and match statistics
    """
    result = TaggingResult()

    # Get keyword database
    if keyword_db is None:
        keyword_db = get_default_database()

    if not keyword_db.is_loaded:
        result.tagged_html = html
        return result

    # Get keywords for the language
    keywords = keyword_db.get_keywords_for_language(language)

    if not keywords:
        result.tagged_html = html
        return result

    # Parse HTML
    soup = BeautifulSoup(html, "lxml")

    # Get all known CSS classes for skipping already-tagged elements
    known_classes = list(set(concept.css_class for concept in keywords.values()))

    def matches_keywords(tag_text: str) -> List[Tuple[str, KeywordConcept]]:
        """Find all keyword matches in tag text"""
        matches = []
        tag_text_lower = tag_text.lower()

        for keyword_lower, concept in keywords.items():
            if keyword_lower in tag_text_lower:
                matches.append((concept.keyword, concept))

        return matches

    def is_text_difficult(text: str) -> bool:
        """Check if text is difficult to read"""
        if not HAS_TEXTSTAT or not check_readability:
            return False

        if len(text) < readability_length_threshold:
            return False

        score = textstat.flesch_reading_ease(text)
        return score < readability_threshold

    # Process elements from deepest to top
    for tag in reversed(soup.find_all(["li", "p", "span", "div", "td", "th"])):
        # Skip if any child already has one of our classes
        if tag.find(
            attrs={
                "class": lambda c: c and any(cls in c.split() for cls in known_classes)
            }
        ):
            continue

        tag_text = tag.get_text(strip=True)

        if not tag_text:
            continue

        # Find keyword matches
        matches = matches_keywords(tag_text)

        # Check for difficult text
        if is_text_difficult(tag_text):
            result.difficult_sections += 1
            matches.append(
                (
                    DIFFICULT_CSS_CLASS,
                    KeywordConcept(
                        keyword="difficult_text",
                        css_class=DIFFICULT_CSS_CLASS,
                        system=DIFFICULT_SYSTEM,
                        code=DIFFICULT_CODE,
                        display=DIFFICULT_DISPLAY,
                    ),
                )
            )

        # Apply CSS classes
        for keyword, concept in matches:
            result.matches[keyword] += 1

            # Track unique concepts
            if concept not in result.concepts:
                result.concepts.append(concept)

            # Add CSS class to element
            existing_classes = tag.get("class", [])
            if isinstance(existing_classes, str):
                existing_classes = existing_classes.split()

            if concept.css_class not in existing_classes:
                tag["class"] = existing_classes + [concept.css_class]

    result.tagged_html = str(soup)
    return result


def tag_composition_sections(
    composition: Dict[str, Any],
    language: str,
    keyword_db: Optional[KeywordDatabase] = None,
    check_readability: bool = True,
) -> TaggingResult:
    """
    Tag all HTML sections in a FHIR Composition resource

    Processes all section.text.div fields recursively.

    Args:
        composition: FHIR Composition resource dictionary
        language: Language code
        keyword_db: KeywordDatabase to use
        check_readability: Whether to check for difficult text

    Returns:
        Combined TaggingResult for all sections
    """
    result = TaggingResult()

    def process_sections(sections: List[Dict[str, Any]]):
        """Recursively process sections"""
        if not sections:
            return

        for section in sections:
            if not isinstance(section, dict):
                continue

            # Process section HTML
            if "text" in section and isinstance(section["text"], dict):
                div_html = section["text"].get("div", "")

                if div_html:
                    section_result = tag_html_with_keywords(
                        div_html, language, keyword_db, check_readability
                    )

                    # Update section HTML
                    section["text"]["div"] = section_result.tagged_html

                    # Merge results
                    result.matches.update(section_result.matches)
                    result.difficult_sections += section_result.difficult_sections

                    for concept in section_result.concepts:
                        if concept not in result.concepts:
                            result.concepts.append(concept)

            # Process nested subsections
            if "section" in section and isinstance(section["section"], list):
                process_sections(section["section"])

    # Process all sections
    if "section" in composition and isinstance(composition["section"], list):
        process_sections(composition["section"])

    return result


def add_extension_for_concepts(
    composition: Dict[str, Any],
    concepts: List[KeywordConcept],
    replace_if_exists: bool = False,
) -> int:
    """
    Add HtmlElementLink extensions for tagged concepts

    Creates FHIR extensions linking CSS classes to clinical concepts.

    Args:
        composition: FHIR Composition resource (modified in-place)
        concepts: List of KeywordConcept objects to add
        replace_if_exists: Whether to replace existing extensions

    Returns:
        Number of extensions added
    """
    added = 0

    for concept in concepts:
        # Create CodeableReference with concept coding
        coding = Coding(
            system=concept.system_uri, code=concept.code, display=concept.display
        )
        codeable_ref = CodeableReference(codings=[coding])

        # Add the extension
        was_added = add_html_element_link(
            composition,
            element_class=concept.css_class,
            concept=codeable_ref,
            replace_if_exists=replace_if_exists,
        )

        if was_added:
            added += 1

    return added


def preprocess_epi_with_keywords(
    bundle: Dict[str, Any],
    language: str,
    keyword_db: Optional[KeywordDatabase] = None,
    check_readability: bool = True,
    add_extensions: bool = True,
) -> Dict[str, Any]:
    """
    Full preprocessing pipeline for an ePI Bundle

    1. Extracts the Composition from the Bundle
    2. Tags all HTML sections with keywords
    3. Adds HtmlElementLink extensions
    4. Returns the modified Bundle

    Args:
        bundle: FHIR Bundle containing the ePI
        language: Language code for keyword matching
        keyword_db: KeywordDatabase to use
        check_readability: Whether to flag difficult text
        add_extensions: Whether to add HtmlElementLink extensions

    Returns:
        Modified Bundle dictionary
    """
    # Find Composition in bundle
    composition = None

    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Composition":
            composition = resource
            break

    if not composition:
        return bundle

    # Tag all sections
    result = tag_composition_sections(
        composition, language, keyword_db, check_readability
    )

    # Add extensions for found concepts
    if add_extensions and result.concepts:
        add_extension_for_concepts(composition, result.concepts)

    return bundle


def detect_language_from_composition(composition: Dict[str, Any]) -> Optional[str]:
    """
    Try to detect language from Composition resource

    Checks the 'language' field of the Composition.

    Args:
        composition: FHIR Composition resource

    Returns:
        Language code or None if not found
    """
    language = composition.get("language")

    if language:
        # Handle codes like "en-US" -> "en"
        return language.split("-")[0].lower()

    return None
