from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class InvoiceLine(BaseModel):
    item: str
    rate: float
    quantity: float = Field(default=1.0, gt=0)
    description: Optional[str] = None
    category: Optional[str] = None

    @property
    def amount(self) -> float:
        return self.rate * self.quantity


class InvoiceDraft(BaseModel):
    vendor_display_name: str
    vendor_company_name: Optional[str] = None
    line_items: List[InvoiceLine]
    memo: Optional[str] = None
    tax: Optional[float] = None
    total_amount: Optional[float] = None
    due_date: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    is_receipt: Optional[bool] = False
    job_site_address: Optional[str] = None
    customer_name: Optional[str] = None  # QuickBooks customer name


class InvoiceData(BaseModel):
    vendor_display_name: str
    memo: Optional[str] = None
    line_items: List[InvoiceLine]
    tax: Optional[float] = None
    total_amount: Optional[float] = None
    due_date: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    is_receipt: Optional[bool] = False
    job_site_address: Optional[str] = None
    customer_name: Optional[str] = None  # AI-matched customer name


class ShippingItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    weight: Optional[str] = None


class ShippingData(BaseModel):
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    order_number: Optional[str] = None
    shipment_date: Optional[str] = None
    estimated_delivery: Optional[str] = None
    delivery_status: Optional[str] = None
    origin_address: Optional[str] = None
    destination_address: Optional[str] = None
    items: List[ShippingItem] = []
    vendor_name: Optional[str] = None
    notes: Optional[str] = None


class ClientData(BaseModel):
    client_name: Optional[str] = None
    subject: Optional[str] = None
    project_name: Optional[str] = None
    summary: str
    action_items: List[str] = []
    key_dates: List[str] = []
    response_needed: Optional[bool] = False
    urgency: Optional[Literal["low", "medium", "high"]] = None
    notes: Optional[str] = None


class LabelSort(BaseModel):
    label: Literal["invoice", "shipping", "insurance", "client_communications", "none"]
