from pydantic import BaseModel, Field
from typing import Optional

class NAOrderData(BaseModel):
    district: Optional[str] = Field(default=None, description="District parsed from the NA order header.")
    taluka: Optional[str] = Field(default=None, description="Taluka parsed from the NA order header.")
    village: Optional[str] = Field(default=None, description="Village name.")
    survey_no: Optional[str] = Field(default=None, description="Survey number, including subdivision if present.")
    area_na: Optional[str] = Field(default=None, description="Total area mentioned in the NA Order, e.g. in SQM.")
    date: Optional[str] = Field(default=None, description="Order date (DD/MM/YYYY).")
    order_no: Optional[str] = Field(default=None, description="NA Order Number identifier.")

class LeaseDocData(BaseModel):
    lease_start: Optional[str] = Field(default=None, description="Lease Start date extracted from e-Challan.")
    lease_area: Optional[str] = Field(default=None, description="Lease Area extracted from Annexure-I.")
    lease_doc_no: Optional[str] = Field(default=None, description="Doc No extracted via DNR stamps majority vote.")

class CombinedRecord(BaseModel):
    village: Optional[str] = None
    survey_no: Optional[str] = None
    area_na: Optional[str] = None
    date: Optional[str] = None
    order_no: Optional[str] = None
    lease_doc_no: Optional[str] = None
    lease_area: Optional[str] = None
    lease_start: Optional[str] = None
