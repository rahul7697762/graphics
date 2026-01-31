from pydantic import BaseModel, Field
from typing import List

class GenerateRequest(BaseModel):
    property_type: str = Field(
        ...,
        example="Luxury Apartments"
    )
    location: str = Field(
        ...,
        example="Pune"
    )
    price: str = Field(
        ...,
        example="₹2.5 Cr Onwards"
    )
    bhk: str = Field(
        ...,
        example="3 & 4 BHK"
    )
    phone: str = Field(
        ...,
        example="+91 98765 43210"
    )
    amenities: List[str] = Field(
        ...,
        example=["Pool", "Gym", "Clubhouse"]
    )
