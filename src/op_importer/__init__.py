from collections import OrderedDict
from logging import getLogger

from pydantic import ValidationError

from . import validate
from .data_model import WorkPackage

logger = getLogger(__name__)


def extract_validation_errors(validation_errors: list) -> list:
    """Extract validation errors from the results returned by the API.

    Parameters
    ----------
    validation_results : list
        A list of validation results returned by the API. Each item in the list is a dictionary
        containing a 'field' key and a 'message' key.

    Returns
    -------
    list
        A list of dictionaries, where each dictionary contains a 'field' key and a 'message' key,
        representing the validation errors extracted from the API response.
    """
    errors = []
    for error in validation_errors:
        logger.info(f" - Field: {error['field']}, Message: {error['message']}")
    errors.append(error)
    return errors


def main(input_file: list[dict]) -> dict:
    """Validate and Ingest a list of work packages

    Parameters
    ----------
    input_file : list
        A list of dictionaries where the keys correspond to the fields
        required for defining a work package. Required fields are ``subject``,
        ``task`` and ``status``.

    Returns
    -------
    dict
        A dictionary containing keys ``validation errors``, and ``validation_status``.
        If ``validation_status`` is True, then all the provided work packages in the
        ``input_file`` are validated by the API and the work packages are
        ingested.
    """

    validation_errors: OrderedDict = OrderedDict()
    result = {"validation_errors": validation_errors, "validation_status": True}

    for index, item in enumerate(input_file):
        validation_results = []
        # Use Pydantic model to validate the input data structure and types
        # before sending to API
        try:
            payload = WorkPackage(**item)
        except ValidationError as exc:
            for error in exc.errors():
                validation_results.append(
                    {"field": error["loc"][0], "message": error["msg"]}
                )
                logger.info(
                    f"Validation error for item {error['loc'][0]} - {error['msg']}"
                )
            result["validation_status"] = False
        else:
            errors = validate.validate(payload)
            if errors:
                validation_results.extend(extract_validation_errors(errors))
                result["validation_status"] = False
            else:
                logger.info(f"Item '{item.get('subject', 'Unknown')}' is valid.")

        result["validation_errors"][index] = validation_results

    return result
