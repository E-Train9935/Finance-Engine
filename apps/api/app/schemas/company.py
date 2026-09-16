from pydantic import BaseModel, Field


class DcfAssumptions(BaseModel):
    growth_rate: float = Field(default=5.0, ge=-50, le=100)
    discount_rate: float = Field(default=10.0, gt=0, le=50)
    terminal_growth_rate: float = Field(default=2.5, ge=-5, le=10)
    years: int = Field(default=5, ge=1, le=10)
