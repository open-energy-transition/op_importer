"""Validate the provided data for creating a work package in OpenProject.

This module contains functions to validate the data required for creating a
work package in OpenProject.
It checks for the presence of required fields, correct data types,
and valid values according to the OpenProject API specifications.
"""

from logging import getLogger
from os import getenv

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from .data_model import WorkPackage

logger = getLogger(__name__)
load_dotenv()

API_URL = getenv("OPENPROJECT_API_URL", "https://oet.openproject.com/api/v3")
API_KEY = getenv("OPENPROJECT_API_KEY", "")

HEADERS = {"Content-Type": "application/json"}
AUTH = HTTPBasicAuth("apikey", API_KEY)


class Validate:
    """Base class for validating data for OpenProject API requests."""

    def __init__(self, payload: dict):
        self.payload = payload
        self._errors: list[dict[str, str]] = []
        self.validated_response: dict = {}

    def validate(self) -> bool:

        status, response = self.get_form(self.payload)
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

    def get_form(self, payload: dict) -> tuple[int, dict]:
        """Method to be implemented by subclasses to fetch the appropriate form for validation."""
        raise NotImplementedError("Subclasses must implement the get_form method.")


class ValidateWorkPackage(Validate):

    def get_form(self, payload_json: dict) -> tuple[int, dict]:
        """Validates the provided payload against the OpenProject API form"""
        url = f"{API_URL}/work_packages/form"
        response = requests.post(url, headers=HEADERS, auth=AUTH, json=payload_json)
        return response.status_code, response.json()


class ValidateProjectWorkPackage(Validate):

    def get_form(self, payload_json: dict) -> tuple[int, dict]:
        """Validates the provided payload against the OpenProject API form"""
        project_id = payload_json["project"]["href"].split("/")[-1]
        url = f"{API_URL}/work_spaces/{project_id}/work_packages/form"
        response = requests.post(url, headers=HEADERS, auth=AUTH, json=payload_json)
        return response.status_code, response.json()


class GetValidator:

    # def return_validator(self, asset: str) -> Validate:
    #     raise NotImplementedError(
    #             f"Validation for asset type '{asset}' is not implemented."
    #         )

    def select_validator(self, payload: WorkPackage) -> Validate:
        payload_json = payload.model_dump(by_alias=True)
        if isinstance(payload, WorkPackage):
            validator = ValidateWorkPackage(payload_json)
        elif isinstance(payload, WorkPackage) and hasattr(payload, "project"):
            validator = ValidateProjectWorkPackage(payload_json)
        else:
            raise NotImplementedError("Validation for asset type is not implemented.")
        return validator


# class GetWorkPackageValidator(GetValidator):

#     def return_validator(self, asset: str) -> Validate:
#         return ValidateWorkPackage


# class GetProjectWorkPackageValidator(GetValidator):

#     def return_validator(self, asset: str) -> Validate:
#         return ValidateProjectWorkPackage


def validate(payload: WorkPackage) -> list:

    validator = GetValidator()
    validator_instance = validator.select_validator(payload)
    status = validator_instance.validate()
    if status is True:
        return []
    else:
        return validator_instance.errors
