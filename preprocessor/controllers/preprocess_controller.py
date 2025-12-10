from preprocessor.models.fhir_epi import FhirEPI
from preprocessor.models.keyword_data import get_default_database
from preprocessor.models.keyword_tagger import (
    detect_language_from_composition,
    preprocess_epi_with_keywords,
)


def preprocess_post(body=None):  # noqa: E501
    """preprocess_post

    Preprocesses an ePI. Receives an ePI and returns it preprocessed. # noqa: E501

    :param body: ePI to preprocess.
    :type body: dict

    :rtype: Union[dict, Tuple[dict, int], Tuple[dict, int, Dict[str, str]]
    """
    try:
        # Parse the incoming FHIR ePI bundle
        if body is None:
            return {"error": "Request body is required"}, 400

        # Convert dict to FhirEPI model instance
        epi = FhirEPI.from_dict(body)

        # Validate the ePI structure
        if epi.resource_type != "Bundle":
            return {"error": "Invalid FHIR resource type. Expected Bundle."}, 400

        if epi.type != "document":
            return {"error": "Invalid Bundle type. Expected document."}, 400

        # TODO: Implement preprocessing logic here
        # This is where you would apply transformations, validations,
        # and modifications to the ePI content
        preprocessed_epi = _apply_preprocessing(epi)

        # Return the preprocessed ePI as a dictionary
        return preprocessed_epi.to_dict(), 200

    except Exception as e:
        return {"error": f"Failed to process ePI: {str(e)}"}, 500


def _apply_preprocessing(epi: FhirEPI) -> FhirEPI:
    """Apply preprocessing transformations to the ePI

    Includes keyword tagging and HtmlElementLink extension generation.

    :param epi: The input FHIR ePI
    :return: The preprocessed FHIR ePI
    """
    # Convert to dictionary for processing
    bundle_dict = epi.to_dict()

    # Detect language from composition
    composition = epi.get_composition()
    language = None

    if composition:
        language = detect_language_from_composition(composition)

    # Default to English if language not detected
    if not language:
        language = "en"

    # Apply keyword tagging preprocessing
    keyword_db = get_default_database()

    # Only process if keyword database is loaded
    if keyword_db.is_loaded:
        bundle_dict = preprocess_epi_with_keywords(
            bundle_dict,
            language=language,
            keyword_db=keyword_db,
            check_readability=True,
            add_extensions=True,
        )

    # Convert back to FhirEPI
    processed_epi = FhirEPI.from_dict(bundle_dict)

    return processed_epi
