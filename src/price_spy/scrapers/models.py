from pydantic import BaseModel, field_validator


class PriceResult(BaseModel):
    name: str
    price: int  # Integer tenge (no floats, Kazakhstan doesn't use tiyn)
    original_price: int | None = None  # Price before discount, if any
    is_available: bool

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Price must be positive")
        return v

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name must not be empty")
        return v.strip()
