# Preprocessing Service

![Docker Publish (GHCR)](https://github.com/Gravitate-Health/preprocessing-service-example-python/actions/workflows/docker-publish.yml/badge.svg?branch=main)

## Overview

This service provides robust preprocessing for FHIR ePI (electronic Product Information) bundles, supporting extraction, validation, and modification of both FHIR extensions and embedded HTML content. It is designed for pharmaceutical and healthcare data pipelines, enabling safe and flexible manipulation of FHIR R4 resources, including custom extensions and XHTML narratives.

### Key Features

- FhirEPI model for structured ePI bundle parsing
- HtmlElementLink extension management (CRUD operations)
- **Recursive HTML content extraction** from nested composition sections
- HTML content extraction, analysis, and modification (from `Composition.text.div`)
- Section-level HTML manipulation with automatic nesting level detection
- Standalone test runners for all major components
- Dockerized deployment with Python 3.12 and OpenAPI integration
- Extensive documentation and examples

## Usage Guide

### 1. Local Setup

#### Prerequisites

- Python 3.12+
- (Optional) Docker
- (Optional) Virtual environment

#### Install dependencies

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

#### Run tests

```powershell
python test_html_element_link_standalone.py
python test_html_content_manager_standalone.py
```

### 2. Docker Usage

#### Build and run the service

```bash
docker build -t preprocessing-service .
docker run --rm -p 8080:8080 preprocessing-service
```

**Note:** The Docker image uses Python 3.12-alpine for compatibility with the service dependencies.

#### Generate server code from OpenAPI (if needed)

```powershell
docker run --rm -v ${PWD}:/local openapitools/openapi-generator-cli generate -i https://raw.githubusercontent.com/Gravitate-Health/preprocessing-service-example/refs/heads/main/openapi.yaml -g python-flask -o /local/ --additional-properties=packageName=preprocessor
```

### 2.1 GHCR Image (recommended)

Images are published automatically to GitHub Container Registry (GHCR) by CI for this repo and any forks.

- Canonical image for this repo: `ghcr.io/gravitate-health/preprocessing-service-example-python`
- For forks: `ghcr.io/<your-github-username-or-org>/<your-fork-repo>`

#### Pull

```powershell
docker pull ghcr.io/gravitate-health/preprocessing-service-example-python:main
# or a release tag, when available
docker pull ghcr.io/gravitate-health/preprocessing-service-example-python:v1.0.0
```

#### Run

```powershell
docker run --rm -p 8080:8080 ghcr.io/gravitate-health/preprocessing-service-example-python:main
```

#### Authenticate (if needed)

If the image is private or your org requires auth, login to GHCR:

```powershell
$env:CR_PAT = "<YOUR_GH_PAT_WITH_packages:read>"
$env:CR_PAT | docker login ghcr.io -u <YOUR_GH_USERNAME> --password-stdin
```

### 3. API Endpoints

- See `openapi/openapi.yaml` for full specification.
- Main endpoint: `/preprocess` (accepts FHIR Bundle, returns processed bundle)

## Manager Guides & Examples

### HtmlElementLink Manager

**Purpose:** Manage FHIR HtmlElementLink extensions in Composition resources.

**Key Functions:**

- `list_html_element_links(composition)`
- `add_html_element_link(composition, element_class, concept, replace_if_exists=False)`
- `remove_html_element_link(composition, element_class)`
- `get_html_element_link(composition, element_class)`

**Example Usage:**

```python
from preprocessor.models.html_element_link_manager import (
 list_html_element_links, add_html_element_link, remove_html_element_link
)

# List all HtmlElementLink extensions
links = list_html_element_links(composition)

# Add a new HtmlElementLink
add_html_element_link(composition, 'section-title', {'code': 'title', 'display': 'Section Title'})

# Remove an HtmlElementLink by class
remove_html_element_link(composition, 'section-title')
```

### HTML Content Manager

**Purpose:** Extract, analyze, and modify HTML content in FHIR Composition `text.div` and nested sections.

**Key Functions:**

- `get_html_content(composition)` - Extract HTML from composition text.div
- `get_all_html_content(composition)` - **Recursively extract HTML from all sections and subsections**
- `update_html_content(composition, new_html)` - Update composition HTML
- `update_section_html(sections, section_title, new_html, recursive=True)` - Update specific section HTML
- `extract_all_html_from_sections(sections)` - Recursively extract all section HTML with metadata
- `find_elements_by_class(html, class_name)` - Find elements by CSS class
- `replace_html_section(html, start_marker, end_marker, replacement)` - Replace HTML sections
- `get_html_structure_summary(html)` - Analyze HTML structure

**Example Usage:**

```python
from preprocessor.models.html_content_manager import (
    get_html_content, get_all_html_content, update_section_html, 
    find_elements_by_class, get_html_structure_summary
)

# Extract HTML from composition
html = get_html_content(composition)

# Recursively extract ALL HTML content from nested sections
all_html = get_all_html_content(composition)
print(f"Total sections: {all_html['total_sections']}")
print(f"Max nesting level: {all_html['max_nesting_level']}")

for section in all_html['sections']:
    print(f"Level {section['level']}: {section['title']}")
    print(f"  HTML length: {len(section['html'])} chars")
    print(f"  Has subsections: {section['has_subsections']}")

# Update a specific section by title (searches recursively)
update_section_html(
    composition['section'], 
    'What is in this leaflet',
    '<div>New content</div>',
    recursive=True
)

# Find all elements with a specific class
elements = find_elements_by_class(html, 'epi-section')

# Get a summary of the HTML structure
summary = get_html_structure_summary(html)
print(summary)
```

**FhirEPI Model Integration:**

```python
from preprocessor.models.fhir_epi import FhirEPI

# Load and parse ePI bundle
epi = FhirEPI.from_dict(bundle_dict)

# Extract all HTML content including nested sections
all_html = epi.get_all_html_content()
```

## Testing

Standalone test runners are provided for all major components:

- `test_html_element_link_standalone.py` - Test HtmlElementLink extension management
- `test_html_content_manager_standalone.py` - Test HTML content operations
- `test_recursive_html_extraction.py` - **Test recursive HTML extraction from nested sections**

Run with:

```bash
python3 test_html_element_link_standalone.py
python3 test_html_content_manager_standalone.py
python3 test_recursive_html_extraction.py
```

### Examples

Comprehensive examples demonstrating all features:

- `example_recursive_html_extraction.py` - **Recursive HTML extraction examples with 5 different use cases**

Run examples:

```bash
python3 example_recursive_html_extraction.py
```

## Documentation

See the following markdown files for detailed guides and examples:

- `HTMLELEMENTLINK_GUIDE.md`
- `HTMLELEMENTLINK_QUICK_REFERENCE.md`
- `HTMLELEMENTLINK_EXAMPLES.md`
- `HTMLELEMENTLINK_SUMMARY.md`
- `HTMLELEMENTLINK_INDEX.md`
- `HTMLELEMENTLINK_DELIVERABLES.md`

## License

See `LICENSE` for details.
