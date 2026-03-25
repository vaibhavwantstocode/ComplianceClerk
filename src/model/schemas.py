from pydantic import BaseModel, Field
from typing import Optional

class NAOrderData(BaseModel):
    village: Optional[str] = Field(default=None, description="Village name.")
    survey_no: Optional[str] = Field(default=None, description="Survey number, including subdivision if present.")
    district: Optional[str] = Field(default=None, description="District name.")
    area_na: Optional[str] = Field(default=None, description="Total area mentioned in the NA Order, e.g. in SQM.")
    date: Optional[str] = Field(default=None, description="Order date (DD/MM/YYYY).")
    na_order_no: Optional[str] = Field(default=None, description="NA Order Number identifier.")

class LeaseDocData(BaseModel):
    village: Optional[str] = Field(default=None, description="Village name from Annexure-I.")
    survey_no: Optional[str] = Field(default=None, description="Survey number from Annexure-I.")
    district: Optional[str] = Field(default=None, description="District name from Annexure-I.")
    lease_area: Optional[str] = Field(default=None, description="Lease Area extracted from Annexure-I.")
    lease_start: Optional[str] = Field(default=None, description="Lease Start date extracted from e-Challan.")
    lease_doc_no: Optional[str] = Field(default=None, description="Doc No extracted via DNR stamps majority vote.")

class CombinedRecord(BaseModel):
    village: Optional[str] = None
    survey_no: Optional[str] = None
    area_na: Optional[str] = None
    date: Optional[str] = None
    na_order_no: Optional[str] = None
    lease_doc_no: Optional[str] = None
    lease_area: Optional[str] = None
    lease_start: Optional[str] = None
