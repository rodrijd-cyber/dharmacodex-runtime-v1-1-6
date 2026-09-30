from __future__ import annotations

from datetime import date, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReadingInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    full_name: str = Field(min_length=2, max_length=160)
    birth_date: date
    birth_time: time
    city: str = Field(min_length=1, max_length=120)
    country: str = Field(min_length=1, max_length=120)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = Field(min_length=1, max_length=80)
    focus: str = Field(min_length=1, max_length=120)
    experience: str = Field(min_length=1, max_length=120)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("timezone must be a valid IANA zone") from exc
        return value

    def master_input(self) -> dict:
        return {
            "name": self.full_name,
            "full_name": self.full_name,
            "year": self.birth_date.year,
            "month": self.birth_date.month,
            "day": self.birth_date.day,
            "hour": self.birth_time.hour,
            "minute": self.birth_time.minute,
            "city": self.city,
            "country": self.country,
            "timezone": self.timezone,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "lat": self.latitude,
            "lon": self.longitude,
            "location_source": "MANUAL_RUNTIME_INPUT",
            "geocoding_match": None,
            "focus": self.focus,
            "experience": self.experience,
        }

