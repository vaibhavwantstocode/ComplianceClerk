from pydantic import BaseModel, Field
from typing import Optional

class NAOrderData(BaseModel):
    village: Optional[str] = Field(default="", description="Village name.")
    survey_no: Optional[str] = Field(default="", description="Survey number, including subdivision if present.")
    district: Optional[str] = Field(default="", description="District name.")
    area_na: Optional[str] = Field(default="", description="Total area mentioned in the NA Order, e.g. in SQM.")
    date: Optional[str] = Field(default="", description="Order date (DD/MM/YYYY).")
    na_order_no: Optional[str] = Field(default="", description="NA Order Number identifier.")

class LeaseDocData(BaseModel):
    village: Optional[str] = Field(default="", description="Village name from Annexure-I.")
    survey_no: Optional[str] = Field(default="", description="Survey number from Annexure-I.")
    district: Optional[str] = Field(default="", description="District name from Annexure-I.")
    lease_area: Optional[str] = Field(default="", description="Lease Area extracted from Annexure-I.")
    lease_start: Optional[str] = Field(default="", description="Lease Start date extracted from e-Challan.")
    lease_doc_no: Optional[str] = Field(default="", description="Doc No extracted via DNR stamps majority vote.")

class CombinedRecord(BaseModel):
    village: Optional[str] = ""
    survey_no: Optional[str] = ""
    area_na: Optional[str] = ""
    date: Optional[str] = ""
    na_order_no: Optional[str] = ""
    lease_doc_no: Optional[str] = ""
    lease_area: Optional[str] = ""
    lease_start: Optional[str] = ""
