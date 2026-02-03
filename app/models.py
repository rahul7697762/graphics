from pydantic import BaseModel, Field
from typing import List, Optional

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
        default="2 & 3 BHK",
        example="3 & 4 BHK"
    )
    phone: str = Field(
        ...,
        example="+91 98765 43210"
    )
    email: Optional[str] = Field(
        default=None,
        example="sales@example.com"
    )
    builder: Optional[str] = Field(
        default=None,
        example="Skyline Developers"
    )
    address: Optional[str] = Field(
        default=None,
        example="Hinjewadi, Pune"
    )
    amenities: List[str] = Field(
        default=["Premium Amenities", "24/7 Security", "Parking"],
        example=["Pool", "Gym", "Clubhouse"]
    )
    template_id: str = Field(
        default="random",
        example="classic"
    )

class GenerateResponse(BaseModel):
    success: bool = Field(
        ...,
        example=True
    )
    status: str = Field(
        ...,
        example='success'
    )
    image_url: str = Field(
        ...,
        example='/outputs/poster_123.png'
    )
    image_base64: Optional[str] = Field(
        default=None,
        description="Base64 encoded image content"
    )
    template_used: str = Field(
        ...,
        example='template1.render'
    )

