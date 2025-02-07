from wagtail.models import Page
from wagtail.admin.panels import FieldPanel
from django.http import JsonResponse
from django.shortcuts import render
from django.db import models
from dataclasses import dataclass
from typing import Optional, Dict, List, Any, Tuple, Set
from datetime import datetime
import requests
import logging
from myproject.utils.models import BasePage

logger = logging.getLogger(__name__)


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

    content_panels = BasePage.content_panels + [
        FieldPanel("header"),
        FieldPanel("instructions"),
    ]

    parent_page_types = ["home.HomePage"]
    subpage_types = []

    def serve(self, request):
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            address = request.GET.get("address", "").strip()
            zip_code = request.GET.get("zip_code", "").strip()
            count = request.GET.get("count", "").strip()
            category = request.GET.get("category", "").strip()

            # Debug: Log and print the searched address and zip code.
            logger.debug(f"Search requested: Address='{address}', Zip Code='{zip_code}'")
            print(f"[DEBUG] Search requested: Address='{address}', Zip Code='{zip_code}'")

            if not address or not zip_code:
                return JsonResponse(
                    {"success": False, "error": "Address and zip code are required."},
                    status=400
                )

            try:
                service = AddressService()
                data = service.get_address_data(address, zip_code)

                # Determine the count value; if count is "all", return all entries, else default to 5.
                if count == "all":
                    count = max(len(items) for items in data.values())
                else:
                    count = int(count) if count.isdigit() else 5

                # If a category is specified (for load-more operations), only return that category.
                filtered_data = {category: data[category]} if category and category in data else data

                # Serialize the data.
                serialized_data = {
                    key: {
                        "entries": [item.to_dict() for item in value[:count]],
                        "total": len(value)
                    }
                    for key, value in filtered_data.items()
                }

                # Gather unique location info if available.
                unique_locations = set()
                for items in data.values():
                    for item in items:
                        location = item.additional_info.get("location")
                        if location:
                            if isinstance(location, dict):
                                lat = location.get("latitude", "N/A")
                                lon = location.get("longitude", "N/A")
                                unique_locations.add(f"{lat}, {lon}")
                            else:
                                unique_locations.add(location)

                response_data = {
                    "success": True,
                    "data": serialized_data,
                    "unique_locations": list(unique_locations),
                }
                return JsonResponse(response_data)
            except Exception as e:
                logger.error(f"Error fetching data: {e}")
                print(f"[ERROR] Error fetching data: {e}")
                return JsonResponse(
                    {"success": False, "error": "Internal server error. Please try again later."},
                    status=500
                )

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
        except Exception as e:
            logger.error(f"Error parsing date: {e}")
            return None

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "type": self.type,
            "description": self.description,
            "resolution_description": self.resolution_description,
            "status": self.status,
            "additional_info": self.additional_info,
        }
        if self.type not in ["311 Complaint", "Housing Violation"]:
            d.pop("status", None)
        if self.type == "Bedbug Report":
            d["Number of infested units"] = d.pop("description")
        if self.type == "311 Complaint":
            if not d["resolution_description"] or d["resolution_description"].strip() == "":
                d["resolution_description"] = d.get("status", "No resolution")
        if self.type == "Housing Violation":
            d.pop("resolution_description", None)
            d.pop("status", None)
            d["Current Status"] = self.additional_info.get("currentstatus", "Unknown")
            d["Issue still outstanding"] = self.additional_info.get("violationstatus", "No resolution")
            d["Is the Violation Rent-Impariring?"] = self.additional_info.get("rentimpairing", "Unknown")
        return d


class AddressService:
    def __init__(self):
        self.session = requests.Session()
        self.timeout = 30

    def generate_address_variants(self, address: str) -> Set[str]:
        """
        Given an address string (e.g. "67 W 45th St"), generate a set of possible
        normalized variants to improve matching.
        """
        tokens = address.strip().upper().split()
        variants = set()
        if not tokens:
            return variants

        # Assume the first token is the house number.
        house_number = tokens[0]

        # Initialize directional possibilities.
        direction_variants = []
        if len(tokens) >= 2 and tokens[1] in {"W", "WEST", "E", "EAST", "N", "NORTH", "S", "SOUTH"}:
            abbr = tokens[1]
            full = {"W": "WEST", "E": "EAST", "N": "NORTH", "S": "SOUTH"}.get(abbr, abbr)
            direction_variants = [abbr, full]
            rest_tokens = tokens[2:]
        else:
            rest_tokens = tokens[1:]

        # Assume the next token is the street number (possibly with an ordinal suffix).
        street_number_variants = []
        if rest_tokens:
            street_number = rest_tokens[0]
            suffixes = ("ST", "ND", "RD", "TH")
            if any(street_number.endswith(suf) for suf in suffixes):
                street_number_variants = [street_number, street_number.rstrip("".join(suffixes))]
            else:
                street_number_variants = [street_number]
            rest_tokens = rest_tokens[1:]
        else:
            street_number_variants = [""]

        # Assume the final token is the street type (if present).
        street_type_variants = []
        if rest_tokens:
            street_type = rest_tokens[-1]
            if street_type in {"ST", "STREET"}:
                street_type_variants = ["ST", "STREET"]
                rest_tokens = rest_tokens[:-1]
            else:
                street_type_variants = [street_type]
        else:
            street_type_variants = [""]

        middle = " ".join(rest_tokens).strip()

        dir_list = direction_variants if direction_variants else [""]
        for d in dir_list:
            for sn in street_number_variants:
                for st in street_type_variants:
                    variant = " ".join(filter(None, [house_number, d, sn, middle, st])).strip()
                    if variant:
                        variants.add(variant)
        return variants

    def standardize_address(self, full_address: str) -> Tuple[str, str, str, str]:
        """
        Standardizes an address by converting directional abbreviations,
        stripping ordinal suffixes, and normalizing street types.
        
        Returns a tuple: (house_number, street_name, apt, full_standard)
        """
        try:
            parts = full_address.strip().upper().split()
            if not parts:
                return "", "", "", ""

            apt = ""
            if "APT" in parts:
                apt_index = parts.index("APT")
                if apt_index + 1 < len(parts):
                    apt = parts[apt_index + 1]
                parts = parts[:apt_index]

            direction_map = {"N": "NORTH", "S": "SOUTH", "E": "EAST", "W": "WEST"}
            if parts[0] in direction_map:
                parts[0] = direction_map[parts[0]]

            def strip_ordinal(num_str: str) -> str:
                for suffix in ["ST", "ND", "RD", "TH"]:
                    if num_str.endswith(suffix):
                        return num_str[:-len(suffix)]
                return num_str

            if len(parts) > 1:
                parts[1] = strip_ordinal(parts[1])

            if parts[-1] == "STREET":
                parts[-1] = "ST"

            parts[-1] = parts[-1].rstrip(".")

            house_number = parts[0]
            street_name = " ".join(parts[1:])
            full_standard = f"{house_number} {street_name}".title()

            logger.debug(f"Standardized address: house_number='{house_number}', street_name='{street_name}', apt='{apt}', full_standard='{full_standard}'")
            print(f"[DEBUG] Standardized address: house_number='{house_number}', street_name='{street_name}', apt='{apt}', full_standard='{full_standard}'")
            return house_number, street_name, apt, full_standard

        except Exception as e:
            logger.error(f"Error standardizing address: {e}")
            print(f"[ERROR] Error standardizing address: {e}")
            raise ValueError(f"Error standardizing address: {e}")

    def fetch_data(self, url: str, where_clause: str, key_mappings: Dict[str, str], order_field: str) -> List[DataItem]:
        try:
            query_params = {
                "$where": where_clause,
                "$limit": 1000,
                "$order": order_field,
            }
            logger.debug(f"Querying {url} with params: {query_params}")
            print(f"[DEBUG] Querying {url} with params: {query_params}")

            response = self.session.get(url, params=query_params, timeout=self.timeout)
            response.raise_for_status()
            logger.debug(f"Response JSON from {url}: {response.text[:1000]}")
            print(f"[DEBUG] Response JSON (first 1000 chars): {response.text[:1000]}")

            return [
                DataItem(
                    id=item.get(key_mappings["id"], ""),
                    date=DataItem.parse_date(item.get(key_mappings["date"])),
                    type=key_mappings["type"],
                    description=item.get(key_mappings["description"], ""),
                    resolution_description=item.get("resolution_description", ""),
                    status=item.get(key_mappings.get("status", ""), "Unknown"),
                    additional_info={
                        k: item.get(k, "")
                        for k in item.keys()
                        if k not in key_mappings.values() or k in ["currentstatus", "violationstatus", "rentimpairing"]
                    },
                )
                for item in response.json()
            ]
        except Exception as e:
            logger.error(f"Error fetching data from {url}: {e}")
            print(f"[ERROR] Error fetching data from {url}: {e}")
            return []

    def get_address_data(self, address: str, zip_code: str) -> Dict[str, List[DataItem]]:
        # Generate address variants.
        variants = self.generate_address_variants(address)
        logger.debug(f"Address variants: {variants}")
        print(f"[DEBUG] Address variants: {variants}")

        # For APIs with a combined address field, build an IN clause.
        variants_in_clause = ", ".join(f"'{v}'" for v in variants)
        # For APIs splitting house number and street name.
        house_numbers = {v.split()[0] for v in variants if v.split()}
        street_names = {" ".join(v.split()[1:]) for v in variants if len(v.split()) > 1}

        house_numbers_clause = ", ".join(f"'{hn}'" for hn in house_numbers)
        street_names_clause = ", ".join(f"'{sn}'" for sn in street_names)

        # Build where clauses.
        where_311 = f"upper(incident_address) IN ({variants_in_clause}) AND incident_zip = '{zip_code}'"
        where_hv = f"upper(housenumber) IN ({house_numbers_clause}) AND upper(streetname) IN ({street_names_clause}) AND zip = '{zip_code}'"
        where_lv = f"upper(lowhousenumber) IN ({house_numbers_clause}) AND upper(streetname) IN ({street_names_clause}) AND zip = '{zip_code}'"
        where_bedbug = f"upper(house_number) IN ({house_numbers_clause}) AND upper(street_name) IN ({street_names_clause}) AND postcode = '{zip_code}'"

        logger.debug(f"311 where clause: {where_311}")
        logger.debug(f"Housing violations where clause: {where_hv}")
        logger.debug(f"Lead violations where clause: {where_lv}")
        logger.debug(f"Bedbug reports where clause: {where_bedbug}")
        print(f"[DEBUG] 311 where clause: {where_311}")
        print(f"[DEBUG] Housing violations where clause: {where_hv}")
        print(f"[DEBUG] Lead violations where clause: {where_lv}")
        print(f"[DEBUG] Bedbug reports where clause: {where_bedbug}")

        return {
            "311_complaints": self.fetch_data(
                "https://data.cityofnewyork.us/resource/erm2-nwe9.json",
                where_311,
                {
                    "id": "unique_key",
                    "date": "created_date",
                    "type": "311 Complaint",
                    "description": "descriptor",
                    "status": "status"
                },
                "created_date DESC"
            ),
            "housing_violations": self.fetch_data(
                "https://data.cityofnewyork.us/resource/wvxf-dwi5.json",
                where_hv,
                {
                    "id": "violationid",
                    "date": "inspectiondate",
                    "type": "Housing Violation",
                    "description": "novdescription",
                    "status": "currentstatus"
                },
                "inspectiondate DESC"
            ),
            "lead_violations": self.fetch_data(
                "https://data.cityofnewyork.us/resource/v574-pyre.json",
                where_lv,
                {
                    "id": "violationid",
                    "date": "inspectiondate",
                    "type": "Lead Violation",
                    "description": "novdescription",
                },
                "inspectiondate DESC"
            ),
            "bedbug_reports": self.fetch_data(
                "https://data.cityofnewyork.us/resource/wz6d-d3jb.json",
                where_bedbug,
                {
                    "id": "building_id",
                    "date": "filing_date",
                    "type": "Bedbug Report",
                    "description": "infested_dwelling_unit_count",
                },
                "filing_date DESC"
            ),
        }
