from wagtail.models import Page
from wagtail.admin.panels import FieldPanel
from django.http import JsonResponse
from dataclasses import dataclass
from typing import Optional, Dict, List, Any
from datetime import datetime
import requests
from myproject.home.models import HomePage


@dataclass
class DataItem:
    id: str
    date: Optional[datetime]
    type: str
    description: str
    status: Optional[str]
    additional_info: Dict[str, Any]

    @staticmethod
    def parse_date(date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            from dateutil.parser import parse
            return parse(date_str)
        except Exception:
            return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "type": self.type,
            "description": self.description,
            "status": self.status,
            "additional_info": self.additional_info,
        }


class AddressService:
    def __init__(self):
        self.session = requests.Session()
        self.timeout = 30

    def fetch_data(self, url: str, where_clause: str, key_mappings: Dict[str, str]) -> List[DataItem]:
        try:
            response = self.session.get(
                url,
                params={"$where": where_clause, "$limit": 1000},
                timeout=self.timeout
            )
            response.raise_for_status()
            return [
                DataItem(
                    id=item.get(key_mappings["id"], ""),
                    date=DataItem.parse_date(item.get(key_mappings["date"])),
                    type=key_mappings["type"],
                    description=item.get(key_mappings["description"], ""),
                    status=item.get(key_mappings["status"], "Unknown"),
                    additional_info=item.get("additional_info", {}),
                )
                for item in response.json()
            ]
        except Exception:
            return []

    def get_address_data(self, house_number: str, street_name: str) -> Dict[str, List[DataItem]]:
        base_query = f"{house_number} {street_name}%"
        return {
            "311_complaints": self.fetch_data(
                "https://data.cityofnewyork.us/resource/erm2-nwe9.json",
                f"incident_address like '{base_query}' AND created_date >= '2010-01-01'",
                {
                    "id": "unique_key",
                    "date": "created_date",
                    "type": "311 Complaint",
                    "description": "complaint_type",
                    "status": "status",
                }
            ),
            "lead_violations": self.fetch_data(
                "https://data.cityofnewyork.us/resource/v574-pyre.json",
                f"lowhousenumber='{house_number}' AND streetname='{street_name}'",
                {
                    "id": "violationid",
                    "date": "inspectiondate",
                    "type": "Lead Violation",
                    "description": "novdescription",
                    "status": "currentstatus",
                }
            ),
            "bedbug_reports": self.fetch_data(
                "https://data.cityofnewyork.us/resource/wz6d-d3jb.json",
                f"house_number='{house_number}' AND street_name like '{street_name}%'",
                {
                    "id": "building_id",
                    "date": "filing_date",
                    "type": "Bedbug Report",
                    "description": "bedbug_infestation_count",
                    "status": "filing_status",
                }
            ),
            "housing_violations": self.fetch_data(
                "https://data.cityofnewyork.us/resource/wvxf-dwi5.json",
                f"housenumber='{house_number}' AND streetname like '{street_name}%'",
                {
                    "id": "violationid",
                    "date": "inspectiondate",
                    "type": "Housing Violation",
                    "description": "novdescription",
                    "status": "violationstatus",
                }
            ),
            "nycha_data": self.fetch_data(
                "https://data.cityofnewyork.us/resource/evjd-dqpz.json",
                f"development like '{base_query}'",
                {
                    "id": "tds",
                    "date": None,
                    "type": "NYCHA Development",
                    "description": "development",
                    "status": "Active",
                }
            ),
        }


class NYCAddressLookupPage(Page):
    parent_page_types = ["home.HomePage"]  # This page can only exist under HomePage
    subpage_types = []  # No children allowed

    def serve(self, request):
        # Get the address from the query string
        address = request.GET.get("address", "").strip()
        if not address:
            return JsonResponse({"success": False, "error": "No address provided"}, status=400)

        # Split the address into house number and street name
        try:
            house_number, street_name = address.split(" ", 1)
        except ValueError:
            return JsonResponse({"success": False, "error": "Invalid address format. Use '123 Main St'."}, status=400)

        # Fetch data
        service = AddressService()
        data = service.get_address_data(house_number, street_name)

        # Return JSON response
        return JsonResponse({"success": True, "data": {k: [item.to_dict() for item in v] for k, v in data.items()}})
