import re
from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

CURRENCIES = Literal["INR", "USD", "EUR", "GBP", "AED", "SGD"]
CHANNELS = Literal["NEFT", "RTGS", "IMPS", "UPI", "SWIFT", "CASH", "CHEQUE", "POS"]
RISK_CATS = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
ACCT_TYPES = Literal["SAVINGS", "CURRENT", "NRI", "SALARY", "FIXED_DEPOSIT"]


class TransactionEvent(BaseModel):
    txnId: Optional[str] = Field(None, max_length=50)
    fromAccountId: str = Field(..., max_length=50)
    toAccountId: str = Field(..., max_length=50)
    amount: float = Field(..., gt=0, le=100_000_000)
    currency: CURRENCIES = "INR"
    channel: CHANNELS
    merchantId: Optional[str] = Field(None, max_length=50)
    country: str = Field("IN", min_length=2, max_length=2)
    timestamp: Optional[str] = None
    description: Optional[str] = Field(None, max_length=200)

    @field_validator("country")
    @classmethod
    def uppercase_country(cls, v: str) -> str:
        return v.upper()


class CustomerEvent(BaseModel):
    customerId: Optional[str] = Field(None, max_length=50)
    fullName: str = Field(..., max_length=100)
    pan: str
    dob: str
    address: str = Field(..., max_length=300)
    mobile: str
    email: EmailStr
    kycRiskScore: float = Field(0, ge=0, le=100)
    onboardingDate: Optional[str] = None

    @field_validator("pan")
    @classmethod
    def validate_pan(cls, v: str) -> str:
        if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", v.upper()):
            raise ValueError("Invalid PAN format (e.g. ABCDE1234F)")
        return v.upper()

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        if not re.match(r"^[6-9]\d{9}$", v):
            raise ValueError("Invalid mobile (10 digits, starts with 6-9)")
        return v


class AccountEvent(BaseModel):
    accountId: Optional[str] = Field(None, max_length=50)
    customerId: str = Field(..., max_length=50)
    accountType: ACCT_TYPES
    openDate: Optional[str] = None
    currentBalance: float = Field(0, ge=0)
    currency: CURRENCIES = "INR"
    branch: str = Field(..., max_length=100)
    ifscCode: str

    @field_validator("ifscCode")
    @classmethod
    def validate_ifsc(cls, v: str) -> str:
        if not re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", v.upper()):
            raise ValueError("Invalid IFSC code (e.g. HDFC0001234)")
        return v.upper()


class MerchantEvent(BaseModel):
    merchantId: Optional[str] = Field(None, max_length=50)
    name: str = Field(..., max_length=100)
    mcc: str = Field(..., max_length=10)
    country: str = Field("IN", min_length=2, max_length=2)
    riskCategory: RISK_CATS = "LOW"
    gstin: Optional[str] = Field(None, max_length=20)

    @field_validator("country")
    @classmethod
    def uppercase_country(cls, v: str) -> str:
        return v.upper()


class BatchItem(BaseModel):
    type: str
    data: dict


class BatchRequest(BaseModel):
    events: List[BatchItem] = Field(..., min_length=1, max_length=500)
