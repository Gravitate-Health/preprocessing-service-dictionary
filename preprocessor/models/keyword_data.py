"""
Keyword Data Module

Loads and manages keyword data from CSV files for text tagging/annotation.

The CSV format expects columns:
- keyword_<lang>: Keyword in that language (e.g., keyword_en, keyword_es, keyword_pt)
- class: CSS class to apply when keyword is found
- system: Terminology system (e.g., $sct for SNOMED CT)
- code: Terminology code
- display: Display text for the concept

Example CSV:
keyword_en;class;system;code;display;keyword_es;keyword_pt
Pregnancy;pregnancy;$sct;77386006;Pregnancy;Embarazo;Gravidez
"""

import csv
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional

# Map system shortcuts to full URIs
SYSTEM_MAP = {
    "$sct": "http://snomed.info/sct",
    "snomed": "http://snomed.info/sct",
    "icpc-2": "https://icpc2.icd.com/",
    "loinc": "http://loinc.org",
    "icd-10": "http://hl7.org/fhir/sid/icd-10",
}


@dataclass
class KeywordConcept:
    """Represents a keyword with its associated terminology concept"""

    keyword: str
    css_class: str
    system: str
    code: str
    display: str

    @property
    def system_uri(self) -> str:
        """Get the full system URI"""
        return SYSTEM_MAP.get(self.system, self.system)

    def to_coding_dict(self) -> Dict[str, str]:
        """Convert to FHIR Coding dictionary"""
        return {"system": self.system_uri, "code": self.code, "display": self.display}

    def __repr__(self):
        return f"KeywordConcept({self.keyword!r}, class={self.css_class!r})"


class KeywordDatabase:
    """
    Database of keywords for multiple languages

    Provides lookup by keyword text and language.
    """

    def __init__(self):
        """Initialize empty keyword database"""
        # Structure: {language: {keyword_lower: KeywordConcept}}
        self._keywords: Dict[str, Dict[str, KeywordConcept]] = defaultdict(dict)
        self._loaded = False

    @classmethod
    def from_csv_file(cls, filepath: str, delimiter: str = ";") -> "KeywordDatabase":
        """
        Load keyword database from CSV file

        Args:
            filepath: Path to CSV file
            delimiter: CSV delimiter character (default: ";")

        Returns:
            KeywordDatabase instance
        """
        db = cls()
        db.load_from_csv(filepath, delimiter)
        return db

    @classmethod
    def from_csv_string(
        cls, csv_content: str, delimiter: str = ";"
    ) -> "KeywordDatabase":
        """
        Load keyword database from CSV string content

        Args:
            csv_content: CSV content as string
            delimiter: CSV delimiter character (default: ";")

        Returns:
            KeywordDatabase instance
        """
        db = cls()
        db.load_from_csv_string(csv_content, delimiter)
        return db

    def load_from_csv(self, filepath: str, delimiter: str = ";"):
        """
        Load keywords from a CSV file

        Args:
            filepath: Path to CSV file
            delimiter: CSV delimiter character
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Keyword CSV file not found: {filepath}")

        with open(filepath, newline="", encoding="utf-8") as csvfile:
            self._parse_csv(csvfile, delimiter)

        self._loaded = True

    def load_from_csv_string(self, csv_content: str, delimiter: str = ";"):
        """
        Load keywords from CSV string content

        Args:
            csv_content: CSV content as string
            delimiter: CSV delimiter character
        """
        import io

        csvfile = io.StringIO(csv_content)
        self._parse_csv(csvfile, delimiter)
        self._loaded = True

    def _parse_csv(self, csvfile, delimiter: str):
        """Parse CSV content from file-like object"""
        reader = csv.DictReader(csvfile, delimiter=delimiter)

        for row in reader:
            concept_metadata = {
                "class": row.get("class", "").strip(),
                "code": row.get("code", "").strip(),
                "system": row.get("system", "").strip(),
                "display": row.get("display", "").strip(),
            }

            # Process all keyword columns (keyword_<lang>)
            for col in row:
                if col.startswith("keyword_"):
                    lang = col.split("_")[1]
                    keyword = row[col].strip()

                    if keyword:
                        concept = KeywordConcept(
                            keyword=keyword,
                            css_class=concept_metadata["class"],
                            system=concept_metadata["system"],
                            code=concept_metadata["code"],
                            display=concept_metadata["display"] or keyword,
                        )
                        self._keywords[lang][keyword.lower()] = concept

    @property
    def languages(self) -> List[str]:
        """Get list of available languages"""
        return list(self._keywords.keys())

    @property
    def is_loaded(self) -> bool:
        """Check if keywords have been loaded"""
        return self._loaded

    def get_keywords_for_language(self, language: str) -> Dict[str, KeywordConcept]:
        """
        Get all keywords for a specific language

        Args:
            language: Language code (e.g., 'en', 'es', 'pt')

        Returns:
            Dictionary mapping keyword (lowercase) to KeywordConcept
        """
        return dict(self._keywords.get(language, {}))

    def find_keyword(self, text: str, language: str) -> Optional[KeywordConcept]:
        """
        Find exact keyword match in text

        Args:
            text: Text to search
            language: Language code

        Returns:
            KeywordConcept if found, None otherwise
        """
        text_lower = text.lower()
        lang_keywords = self._keywords.get(language, {})
        return lang_keywords.get(text_lower)

    def find_keywords_in_text(self, text: str, language: str) -> List[KeywordConcept]:
        """
        Find all keywords that appear in the given text

        Args:
            text: Text to search in
            language: Language code

        Returns:
            List of matching KeywordConcept objects
        """
        matches = []
        text_lower = text.lower()

        lang_keywords = self._keywords.get(language, {})

        for keyword_lower, concept in lang_keywords.items():
            if keyword_lower in text_lower:
                matches.append(concept)

        return matches

    def get_all_css_classes(self, language: Optional[str] = None) -> List[str]:
        """
        Get all unique CSS classes in the database

        Args:
            language: Optional language to filter by

        Returns:
            List of unique CSS class names
        """
        classes = set()

        if language:
            for concept in self._keywords.get(language, {}).values():
                if concept.css_class:
                    classes.add(concept.css_class)
        else:
            for lang_keywords in self._keywords.values():
                for concept in lang_keywords.values():
                    if concept.css_class:
                        classes.add(concept.css_class)

        return list(classes)

    def __len__(self) -> int:
        """Get total number of keyword entries"""
        return sum(len(keywords) for keywords in self._keywords.values())

    def __repr__(self):
        langs = ", ".join(self.languages)
        return f"KeywordDatabase(languages=[{langs}], total_entries={len(self)})"


# Default keywords database instance
_default_database: Optional[KeywordDatabase] = None


def get_default_database() -> KeywordDatabase:
    """
    Get or create the default keyword database

    Loads from keywords.csv in the data directory if not already loaded.

    Returns:
        KeywordDatabase instance
    """
    global _default_database

    if _default_database is None:
        _default_database = KeywordDatabase()

        # Try to load from default location
        default_csv_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "keywords.csv"
        )

        if os.path.exists(default_csv_path):
            _default_database.load_from_csv(default_csv_path)

    return _default_database


def set_default_database(db: KeywordDatabase):
    """
    Set the default keyword database

    Args:
        db: KeywordDatabase instance to use as default
    """
    global _default_database
    _default_database = db
