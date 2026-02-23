from datetime import datetime

from pydantic import BaseModel, Field, PositiveInt, field_serializer


class ValidationResponse(BaseModel):
    validation_status: bool
    validation_errors: list[dict[str, str]]
    validation_results: dict | None = None


class ValidationResponseList(BaseModel):
    validation_status: bool
    validation_errors: dict[int, list[dict[str, str]]]
    validation_results: dict[int, dict] | None = None


class WorkPackage(BaseModel):
    subject: str
    description: str | None = None
    project: PositiveInt | None = None
    work_package_type: PositiveInt = Field(..., serialization_alias="type")
    status: PositiveInt | None = None
    startDate: datetime | None = None
    dueDate: datetime | None = None

    @field_serializer("description", mode="plain")
    def serialize_description(self, value: str | None) -> dict | None:
        if value:
            return {"raw": value, "format": "markdown"}
        else:
            return {}

    @field_serializer("project", mode="plain")
    def serialize_project(self, value: PositiveInt) -> dict:
        if value:
            return {"href": f"/api/v3/projects/{value}"}
        else:
            return {}

    @field_serializer("work_package_type", mode="plain")
    def serialize_work_package_type(self, value: PositiveInt) -> dict:
        if value:
            return {"href": f"/api/v3/types/{value}"}
        else:
            return {}

    @field_serializer("status", mode="plain")
    def serialize_status(self, value: PositiveInt) -> dict:
        if value:
            return {"href": f"/api/v3/statuses/{value}"}
        else:
            return {}

    @field_serializer("startDate", mode="plain")
    def serialize_start_date(self, value: datetime) -> str:
        if value is not None:
            return value.date().isoformat()
        else:
            return None

    @field_serializer("dueDate", mode="plain")
    def serialize_due_date(self, value: datetime) -> str:
        if value is not None:
            return value.date().isoformat()
        else:
            return None
