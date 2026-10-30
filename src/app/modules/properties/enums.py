from enum import StrEnum


class PropertyListingType(StrEnum):
    SALE = "sale"
    RENT = "rent"


class PropertyType(StrEnum):
    APARTMENT = "apartment"
    VILLA = "villa"
    TOWNHOUSE = "townhouse"
    PENTHOUSE = "penthouse"
    COMMERCIAL = "commercial"
    LAND = "land"


class PropertyStatus(StrEnum):
    AVAILABLE = "available"
    UNDER_OFFER = "under_offer"
    SOLD = "sold"
    RENTED = "rented"