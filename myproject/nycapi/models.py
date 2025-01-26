from wagtail.models import Page
from wagtail.admin.panels import FieldPanel
from django.http import JsonResponse
from django.shortcuts import render
from django.db import models
from dataclasses import dataclass
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
import requests
from myproject.utils.models import BasePage


class NYCAddressLookupPage(BasePage):
    template = "pages/nyc_address_lookup_page.html"

    header = models.CharField(
        max_length=255,
        help_text="Header displayed at the top of the page.",
        default="NYC Address Lookup Tool",
    )
    instructions = models.TextField(
        help_text="Instructions displayed to users on how to use the tool.",
        blank=True,
        default=(
            "Enter an address and zip code to retrieve NYC OpenData information, "
            "including 311 complaints, lead violations, bedbug reports, "
            "housing violations, and NYCHA data."
        ),
    )

    # Wagtail admin panels
    content_panels = BasePage.content_panels + [
        FieldPanel("header"),
        FieldPanel("instructions"),
    ]

    parent_page_types = ["home.HomePage"]
    subpage_types = []

    def serve(self, request):
        # Check if it's an AJAX request
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            address = request.GET.get("address", "").strip()
            zip_code = request.GET.get("zip_code", "").strip()

            if not address or not zip_code:
                return JsonResponse({"success": False, "error": "Address and zip code are required."}, status=400)

            # Fetch data
            try:
                service = AddressService()
                data = service.get_address_data(address, zip_code)  # Pass two arguments here

                # Extract unique coordinates
                unique_locations = set()
                for complaint in data.get("311_complaints", []):
                    location = complaint.additional_info.get("location")
                    if location:
                        if isinstance(location, dict):
                            lat = location.get("latitude", "N/A")
                            lon = location.get("longitude", "N/A")
                            unique_locations.add(f"{lat}, {lon}")
                        else:
                            unique_locations.add(location)

                response_data = {
                    "success": True,
                    "data": {k: [item.to_dict() for item in v] for k, v in data.items()},
                    "unique_locations": list(unique_locations),
                }
                return JsonResponse(response_data)
            except Exception as e:
                print(f"Error fetching data: {e}")
                return JsonResponse({"success": False, "error": "Internal server error. Please try again later."}, status=500)

        return render(request, self.template, {"page": self})


@dataclass
class DataItem:
    id: str
    date: Optional[datetime]
    type: str
    description: str
    resolution_description: Optional[str]
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
            "resolution_description": self.resolution_description,
            "status": self.status,
            "additional_info": self.additional_info,
        }


class AddressService:
    def __init__(self):
        self.session = requests.Session()
        self.timeout = 30

    def standardize_address(self, full_address: str) -> Tuple[str, str, str, str]:
        try:
            parts = full_address.strip().upper().split()
            if not parts:
                return "", "", "", ""

            # Extract apartment number if present
            apt = ""
            if "APT" in parts:
                apt_index = parts.index("APT")
                if apt_index + 1 < len(parts):
                    apt = parts[apt_index + 1]
                parts = parts[:apt_index]

            # Get house number
            house_number = parts[0]

            # Remove ordinal suffixes (TH, ST, ND, RD) from street numbers
            street_parts = []
            for part in parts[1:]:
                if part.rstrip("THSTNDRD").isdigit():
                    street_parts.append(part.rstrip("THSTNDRD"))
                else:
                    street_parts.append(part)

            street_name = " ".join(street_parts)
            standardized = f"{house_number} {street_name}"

            return house_number, street_name, apt, standardized
        except Exception as e:
            raise ValueError(f"Error standardizing address: {e}")

    def fetch_data(self, url: str, where_clause: str, key_mappings: Dict[str, str], order_field: str) -> List[DataItem]:
        try:
            query_params = {
                "$where": where_clause,
                "$limit": 1000,
                "$order": order_field,
            }
            print(f"Querying {url} with params: {query_params}")  # Debugging
            response = self.session.get(url, params=query_params, timeout=self.timeout)
            response.raise_for_status()
            return [
                DataItem(
                    id=item.get(key_mappings["id"], ""),
                    date=DataItem.parse_date(item.get(key_mappings["date"])),
                    type=key_mappings["type"],
                    description=item.get(key_mappings["description"], ""),
                    resolution_description=item.get("resolution_description", ""),
                    status=item.get(key_mappings.get("status", ""), "Unknown"),
                    additional_info={k: item.get(k, "") for k in item.keys() if k not in key_mappings.values()},
                )
                for item in response.json()
            ]
        except requests.exceptions.HTTPError as e:
            print(f"HTTPError for {url}: {e.response.text}")
            return []
        except Exception as e:
            print(f"Error fetching data from {url}: {e}")
            return []

    def get_address_data(self, address: str, zip_code: str) -> Dict[str, List[DataItem]]:
        house_number, street_name, apt, standardized = self.standardize_address(address)

        return {
            "311_complaints": self.fetch_data(
                "https://data.cityofnewyork.us/resource/erm2-nwe9.json",
                f"upper(incident_address) = '{house_number} {street_name}' AND incident_zip = '{zip_code}' AND created_date >= '2010-01-01'",
                {
                    "id": "unique_key",
                    "date": "created_date",
                    "type": "311 Complaint",
                    "description": "descriptor",
                    "resolution_description": "resolution_description",
                },
                "created_date DESC",
            ),
            "lead_violations": self.fetch_data(
                "https://data.cityofnewyork.us/resource/v574-pyre.json",
                f"upper(lowhousenumber) = '{house_number}' AND upper(streetname) = '{street_name}' AND zip = '{zip_code}'",
                {
                    "id": "violationid",
                    "date": "inspectiondate",
                    "type": "Lead Violation",
                    "description": "novdescription",
                },
                "inspectiondate DESC",
            ),
            "bedbug_reports": self.fetch_data(
                "https://data.cityofnewyork.us/resource/wz6d-d3jb.json",
                f"upper(house_number) = '{house_number}' AND upper(street_name) = '{street_name}' AND postcode = '{zip_code}'",
                {
                    "id": "building_id",
                    "date": "filing_date",
                    "type": "Bedbug Report",
                    "description": "infested_dwelling_unit_count",
                },
                "filing_date DESC",
            ),
            "housing_violations": self.fetch_data(
                "https://data.cityofnewyork.us/resource/wvxf-dwi5.json",
                f"upper(housenumber) = '{house_number}' AND upper(streetname) = '{street_name}' AND zip = '{zip_code}'",
                {
                    "id": "violationid",
                    "date": "inspectiondate",
                    "type": "Housing Violation",
                    "description": "novdescription",
                },
                "inspectiondate DESC",
            ),
        }
