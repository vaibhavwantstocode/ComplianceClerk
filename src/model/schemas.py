from pydantic import BaseModel, Field
from typing import Optional

class NAOrderData(BaseModel):
    district: Optional[str] = Field(default="", description="District name.")
    taluka: Optional[str] = Field(default="", description="Taluka name.")
    village: Optional[str] = Field(default="", description="Village name.")
    survey_no: Optional[str] = Field(default="", description="Survey number, including subdivision if present.")
    area_na: Optional[str] = Field(default="", description="Total area mentioned in the NA Order, e.g. in SQM.")
    dated: Optional[str] = Field(default="", description="Order date (DD/MM/YYYY).")
    na_order_no: Optional[str] = Field(default="", description="NA Order Number identifier.")

class LeaseDocData(BaseModel):
    district: Optional[str] = Field(default="", description="District name from Annexure-I.")
    taluka: Optional[str] = Field(default="", description="Taluka name from Annexure-I.")
    village: Optional[str] = Field(default="", description="Village name from Annexure-I.")
    survey_no: Optional[str] = Field(default="", description="Survey number from Annexure-I.")
    lease_area: Optional[str] = Field(default="", description="Lease Area extracted from Annexure-I.")
    lease_doc_no: Optional[str] = Field(default="", description="Doc No extracted via DNR stamps majority vote.")
    lease_start: Optional[str] = Field(default="", description="Lease Start date extracted from page bottom date.")

class CombinedRecord(BaseModel):
    village: Optional[str] = ""
    survey_no: Optional[str] = ""
    area_na: Optional[str] = ""
    dated: Optional[str] = ""
    na_order_no: Optional[str] = ""
    lease_doc_no: Optional[str] = ""
    lease_area: Optional[str] = ""
    lease_start: Optional[str] = ""
