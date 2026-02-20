from pydantic import BaseModel, Field, PositiveInt, field_serializer


class WorkPackage(BaseModel):
    subject: str
    description: str | None = None
    project: PositiveInt | None = None
    work_package_type: PositiveInt = Field(..., serialization_alias="type")
    status: PositiveInt | None = None

    @field_serializer("description", mode="plain")
    def serialize_description(self, value: str | None) -> dict | None:
        return {"raw": value, "format": "markdown"}

    @field_serializer("project", mode="plain")
    def serialize_project(self, value: PositiveInt) -> dict:
        return {"href": f"/api/v3/projects/{value}"}

    @field_serializer("work_package_type", mode="plain")
    def serialize_work_package_type(self, value: PositiveInt) -> dict:
        return {"href": f"/api/v3/types/{value}"}

    @field_serializer("status", mode="plain")
    def serialize_status(self, value: PositiveInt) -> dict:
        return {"href": f"/api/v3/statuses/{value}"}
