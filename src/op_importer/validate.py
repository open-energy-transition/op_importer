"""Validate the provided data for creating a work package in OpenProject.

This module contains functions to validate the data required for creating a
work package in OpenProject.
It checks for the presence of required fields, correct data types,
and valid values according to the OpenProject API specifications.
"""

from logging import getLogger
from os import getenv
from typing import Any

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from .data_model import ValidationResponse, WorkPackage
from .get_data import get_projects, get_types

logger = getLogger(__name__)
load_dotenv()

API_URL: str = getenv("OPENPROJECT_API_URL", "")
API_KEY: str = getenv("OPENPROJECT_API_KEY", "")

HEADERS = {"Content-Type": "application/json"}
AUTH = HTTPBasicAuth("apikey", API_KEY)


class Validate:
    """Base class for validating data for OpenProject API requests."""

    def __init__(self, payload: WorkPackage):
        self._payload: WorkPackage = payload
        self._errors: list[dict[str, str]] = []
        self.validated_response: dict = {}

    def validate_project_id(self) -> bool:
        """Validate that the provided project ID exists in OpenProject."""
        project_id = self.payload.project
        projects = get_projects()
        project_ids = [project["id"] for project in projects["_embedded"]["elements"]]
        if project_id not in project_ids:
            self.errors.append(
                {
                    "field": "project",
                    "message": f"Project with ID {project_id} does not exist.",
                }
            )
            return False
        return True

    def validate_type_id(self) -> bool:
        """Validate that the provided type ID exists in OpenProject."""
        type_id = self.payload.work_package_type
        types = get_types()
        type_ids = [type_["id"] for type_ in types["_embedded"]["elements"]]
        if type_id not in type_ids:
            self.errors.append(
                {
                    "field": "work_package_type",
                    "message": f"Type with ID {type_id} does not exist.",
                }
            )
            return False
        return True

    def validate(self) -> bool:
        """Validate the provided payload against the OpenProject API form.

        If validation is successful, stores the validated response
        in ``self.validated_response``
        """

        result = self.validate_project_id()
        if not result:
            return False
        result = self.validate_type_id()
        if not result:
            return False

        status, response = self.get_form()
        print("Status:", status)
        logger.info(f"Validation response: {response}")
        if status == 200:
            print(response["_embedded"]["validationErrors"])
            if errors := response["_embedded"]["validationErrors"]:
                for field, error in errors.items():
                    self.errors.append({"field": field, "message": error["message"]})
                return False
            else:
                self.validated_response = response["_embedded"]["payload"]
                return True
        else:
            error_message = response.get("message", "Unknown error")
            raise ValueError(f"Failed to fetch form: {error_message}")

    @property
    def errors(self) -> list[dict[str, str]]:
        return self._errors

    @errors.setter
    def errors(self, value: list[dict[str, str]]):
        self._errors = value

    @property
    def payload(self) -> WorkPackage:
        return self._payload

    @property
    def payload_json(self) -> dict[str, Any]:
        return self._payload.model_dump(by_alias=True)

    def get_form(self) -> tuple[int, dict]:
        """Method to be implemented by subclasses to fetch form for validation.

        Method should access ``self.payload_json`` to get the serialized
        payload for validation.
        """
        raise NotImplementedError("Subclasses must implement get_form.")


class ValidateWorkPackage(Validate):

    def get_form(self) -> tuple[int, dict]:
        """Validates the provided payload against the OpenProject API form"""
        url = f"{API_URL}/work_packages/form"
        response = requests.post(url, headers=HEADERS, auth=AUTH, json=self.payload_json)
        return response.status_code, response.json()


class ValidateProjectWorkPackage(Validate):

    def get_form(self) -> tuple[int, dict]:
        """Validates the provided payload against the OpenProject API form"""
        project_id = self.payload.project
        url = f"{API_URL}/work_spaces/{project_id}/work_packages/form"
        response = requests.post(url, headers=HEADERS, auth=AUTH, json=self.payload_json)
        return response.status_code, response.json()


class GetValidator:

    def select_validator(self, payload: WorkPackage) -> Validate:
        if isinstance(payload, WorkPackage):
            validator = ValidateWorkPackage(payload)
        elif isinstance(payload, WorkPackage) and hasattr(payload, "project"):
            validator = ValidateProjectWorkPackage(payload)
        else:
            raise NotImplementedError("Validation for asset type is not implemented.")
        return validator


def validate(payload: WorkPackage) -> ValidationResponse:

    validator = GetValidator()
    validator_instance = validator.select_validator(payload)
    status = validator_instance.validate()

    response = ValidationResponse(
        validation_status=status,
        validation_errors=validator_instance.errors,
        validation_results=validator_instance.validated_response if status else None,
    )
    return response
