from __future__ import annotations
from datetime import date as Date
from typing import List, Optional
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict

# ══════════════════════════════════════════════════════════════
#  USER
# ══════════════════════════════════════════════════════════════
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = ""

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    phone: str = ""

    model_config = ConfigDict(from_attributes=True)

# ══════════════════════════════════════════════════════════════
#  CATEGORY
# ══════════════════════════════════════════════════════════════
class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = ""

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class CategoryOut(BaseModel):
    id: int
    name: str
    description: str = ""

    model_config = ConfigDict(from_attributes=True)

# ══════════════════════════════════════════════════════════════
#  EXPENSE
# ══════════════════════════════════════════════════════════════
class ExpenseCreate(BaseModel):
    title: str
    amount: float
    date: Date
    user_id: int
    category_id: int
    notes: Optional[str] = ""
    payment_method: Optional[str] = ""

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

class ExpenseUpdate(BaseModel):
    title: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[Date] = None
    user_id: Optional[int] = None
    category_id: Optional[int] = None
    notes: Optional[str] = None
    payment_method: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

class ExpenseOut(BaseModel):
    id: int
    title: str
    amount: float
    date: Date
    user_id: int
    category_id: int
    notes: str = ""
    payment_method: str = ""

    model_config = ConfigDict(from_attributes=True)

# ══════════════════════════════════════════════════════════════
#  REPORT RESPONSE SHAPES
# ══════════════════════════════════════════════════════════════
class CategoryTotal(BaseModel):
    category_id: int
    total: float

class MonthTotal(BaseModel):
    month: int
    total: float

class YearTotal(BaseModel):
    year: int
    total: float

class UserTotal(BaseModel):
    user_id: int
    name: str
    total: float

class MonthlySummaryOut(BaseModel):
    year: int
    month: int
    total: float
    categories: List[CategoryTotal]

class YearlySummaryOut(BaseModel):
    year: int
    total: float
    categories: List[CategoryTotal]
    monthly: List[MonthTotal]

class TimeseriesOut(BaseModel):
    from_year: int
    to_year: int
    years: List[YearTotal]

class ByUserOut(BaseModel):
    year: int
    month: Optional[int]
    users: List[UserTotal]