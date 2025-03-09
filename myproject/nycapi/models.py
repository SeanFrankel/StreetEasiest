import os
import csv
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, List, Any, Tuple, Set

import requests
from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page

from myproject.utils.models import BasePage  # Adjust if necessary
from myproject.standardpages.models import BasePage as StandardBasePage

logger = logging.getLogger(__name__)

def parse_house_number(house_str: str) -> Optional[int]:
    """Converts a house number string (e.g. '99-15') to an integer (9915)."""
    try:
        return int(house_str.replace("-", ""))
    except Exception as e:
        logger.error(f"Error parsing house number '{house_str}': {e}")
        return None

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
        if self.type == "311 Complaint" and (not d["resolution_description"] or d["resolution_description"].strip() == ""):
            d["resolution_description"] = d.get("status", "No resolution")
        if self.type == "Housing Violation":
            d.pop("resolution_description", None)
            d.pop("status", None)
            d["Current Status"] = self.additional_info.get("currentstatus", "Unknown")
            d["Issue still outstanding"] = self.additional_info.get("violationstatus", "No resolution")
            d["Is the Violation Rent-Impariring?"] = self.additional_info.get("rentimpairing", "Unknown")
        return d

class NYCAddressLookupPage(BasePage):
    template = "pages/nyc_address_lookup_page.html"

    header = models.TextField(
        help_text="Header displayed at the top of the page.",
        default="NYC Address Lookup Tool",
    )
    instructions = RichTextField(
        help_text="Instructions displayed to users on how to use the tool.",
        blank=True,
        default=(
            "Enter an address and zip code to retrieve NYC OpenData information, "
            "including 311 complaints, lead violations, bedbug reports, housing violations, "
            "and NYCHA data. A rent stabilized lookup is also provided."
        ),
    )
    data_faqs = RichTextField(
        blank=True,
        help_text="Data FAQs content for the page."
    )
    how_to_use = RichTextField(
        blank=True,
        help_text="Instructions on how to use the page."
    )

    content_panels = BasePage.content_panels + [
        FieldPanel("header"),
        FieldPanel("instructions"),
        FieldPanel("data_faqs"),
        FieldPanel("how_to_use"),
    ]

    parent_page_types = ["home.HomePage"]
    subpage_types = []

    def serve(self, request):
        # If AJAX (XHR) request with address and zip_code, return lookup data.
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" and 'address' in request.GET and 'zip_code' in request.GET:
            from myproject.nycapi.views import building_lookup_view
            return building_lookup_view(request)
        return super().serve(request)

class AddressService:
    def __init__(self):
        self.session = requests.Session()
        self.timeout = 30

    def generate_address_variants(self, address: str) -> Set[str]:
        """Generates multiple variants of an address to improve matching."""
        tokens = address.strip().upper().split()
        variants = set()
        if not tokens:
            return variants

        house_number = tokens[0]
        rest_tokens = tokens[1:]
        if rest_tokens and rest_tokens[0] in {"W", "WEST", "E", "EAST", "N", "NORTH", "S", "SOUTH"}:
            direction_variants = [rest_tokens[0], {"W": "WEST", "E": "EAST", "N": "NORTH", "S": "SOUTH"}[rest_tokens[0]]]
            rest_tokens = rest_tokens[1:]
        else:
            direction_variants = [""]

        if rest_tokens:
            street_number = rest_tokens[0]
            suffixes = ("ST", "ND", "RD", "TH")
            if any(street_number.endswith(suf) for suf in suffixes):
                street_number_variants = [street_number, street_number[:-2]]
            else:
                street_number_variants = [street_number]
            rest_tokens = rest_tokens[1:]
        else:
            street_number_variants = [""]

        if rest_tokens:
            possible_type = rest_tokens[-1]
            if possible_type in {"ST", "STREET"}:
                street_type_variants = ["ST", "STREET"]
                rest_tokens = rest_tokens[:-1]
            else:
                street_type_variants = [possible_type]
        else:
            street_type_variants = [""]

        middle = " ".join(rest_tokens).strip()
        for d in direction_variants:
            for sn in street_number_variants:
                for st in street_type_variants:
                    variant = " ".join(filter(None, [house_number, d, sn, middle, st])).strip()
                    if variant:
                        variants.add(variant)
        return variants

    def standardize_address(self, full_address: str) -> Tuple[str, str, str, str]:
        """Standardizes an address by handling apartment numbers, directional abbreviations, and ordinals."""
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
                if len(num_str) > 2 and num_str[:-2].isdigit() and num_str[-2:] in {"ST", "ND", "RD", "TH"}:
                    return num_str[:-2]
                return num_str
            if len(parts) > 1:
                parts[1] = strip_ordinal(parts[1])
            full_standard = " ".join(parts).title()
            logger.debug(f"Standardized address: house_number='{parts[0]}', street_name='{' '.join(parts[1:])}', apt='{apt}', full_standard='{full_standard}'")
            return parts[0], " ".join(parts[1:]), apt, full_standard
        except Exception as e:
            logger.error(f"Error standardizing address: {e}")
            raise ValueError(f"Error standardizing address: {e}")

    def get_rent_stabilized_data(self, address: str, zip_code: str) -> dict:
        """Looks up rent-stabilized data from a CSV file based on address variants."""
        from django.conf import settings
        import csv

        def normalize_street(text: str) -> str:
            mapping = {"AVENUE": "AVE", "BOULEVARD": "BLVD", "STREET": "ST", "ROAD": "RD"}
            for full, abbr in mapping.items():
                text = text.upper().replace(full, abbr)
            return text.strip()

        csv_path = os.path.join(settings.BASE_DIR, "static", "data", "all_boroughs.csv")
        if not os.path.exists(csv_path):
            return {"has_rent_stabilized": "No", "official_definition": "N/A", "tax_abatement": "N/A"}

        tokens = address.strip().upper().split()
        input_variants = {" ".join(tokens)}
        _, _, _, std_address = self.standardize_address(address)
        input_variants.add(std_address.upper().strip())
        normalized_variants = {normalize_street(v) for v in input_variants}
        logger.debug(f"Normalized address variants: {normalized_variants}")

        found_row = None
        with open(csv_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                csv_address = " ".join(filter(None, [
                    row.get("BLDGNO1", "").strip(),
                    row.get("STREET1", "").strip(),
                    row.get("STSUFX1", "").strip()
                ])).upper().strip()
                if row.get("ZIP", "").strip() == zip_code and normalize_street(csv_address) in normalized_variants:
                    found_row = row
                    break

        if found_row:
            status2 = found_row.get("STATUS2", "").strip()
            status3 = found_row.get("STATUS3", "").strip()
            if not status2 and not status3:
                combined_tax = "N/A"
            elif status2 and status3:
                combined_tax = f"{status2} and {status3}"
            elif status2:
                combined_tax = status2
            else:
                combined_tax = status3
            return {
                "has_rent_stabilized": "Yes",
                "official_definition": found_row.get("STATUS1", "N/A"),
                "tax_abatement": combined_tax,
            }
        return {"has_rent_stabilized": "No", "official_definition": "N/A", "tax_abatement": "N/A"}

    def fetch_data(self, url: str, where_clause: str, key_mappings: Dict[str, str], order_field: str) -> List[DataItem]:
        """Fetches data from a given endpoint and maps the JSON response to DataItem instances."""
        try:
            query_params = {"$where": where_clause, "$order": order_field}
            logger.debug(f"Querying {url} with params: {query_params}")
            response = self.session.get(url, params=query_params, timeout=self.timeout)
            response.raise_for_status()
            logger.debug(f"Response JSON (first 1000 chars): {response.text[:1000]}")
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
            return []

    def get_address_data(self, address: str, zip_code: str) -> Dict[str, List[Any]]:
        """Fetches address-related data; currently, only rent-stabilized data is returned."""
        variants = self.generate_address_variants(address)
        data = {
            "rent_stabilized": [self.get_rent_stabilized_data(address, zip_code)]
        }
        return data

class HPDLookupPage(StandardBasePage):
    template = "nycapi/hpd_lookup_page.html"

    header = models.TextField(
        help_text="Header displayed at the top of the page.",
        default="NYC HPD Lookup Tool",
    )
    instructions = RichTextField(
        help_text="Instructions displayed to users on how to use the tool.",
        blank=True,
        default=(
            "Enter an address and zip code to scrape housing violation information "
            "directly from HPD Online. This tool will retrieve 311 complaints and "
            "housing violations by accessing the official HPD website."
        ),
    )
    data_faqs = RichTextField(blank=True, help_text="Data FAQs content for the page.")
    how_to_use = RichTextField(blank=True, help_text="Instructions on how to use the page.")

    content_panels = StandardBasePage.content_panels + [
        FieldPanel("header"),
        FieldPanel("instructions"),
        FieldPanel("data_faqs"),
        FieldPanel("how_to_use"),
    ]

    parent_page_types = ["home.HomePage"]
    subpage_types = []
