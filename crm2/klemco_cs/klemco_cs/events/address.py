# Address server-side events — tag each address with a sales Zone derived from its State.
# One Zone field serves both bill-to and ship-to (same Address doctype). Auto-filled when blank
# (editable override persists); the client mirrors this live via zone_for_state.

import frappe

# Standard India 4-zone split over all states / UTs. Spellings match India Compliance's
# Address.gst_state options. Editable later per Klemco's official bifurcation.
STATE_ZONE = {
    # North
    "Delhi": "North", "Punjab": "North", "Haryana": "North", "Himachal Pradesh": "North",
    "Jammu and Kashmir": "North", "Ladakh": "North", "Uttarakhand": "North",
    "Uttar Pradesh": "North", "Rajasthan": "North", "Chandigarh": "North",
    # South
    "Andhra Pradesh": "South", "Telangana": "South", "Karnataka": "South", "Tamil Nadu": "South",
    "Kerala": "South", "Puducherry": "South", "Lakshadweep": "South",
    "Andaman and Nicobar Islands": "South",
    # East (incl. North-East)
    "Bihar": "East", "Jharkhand": "East", "Odisha": "East", "West Bengal": "East",
    "Sikkim": "East", "Assam": "East", "Arunachal Pradesh": "East", "Manipur": "East",
    "Meghalaya": "East", "Mizoram": "East", "Nagaland": "East", "Tripura": "East",
    # West
    "Maharashtra": "West", "Gujarat": "West", "Goa": "West", "Madhya Pradesh": "West",
    "Chhattisgarh": "West", "Dadra and Nagar Haveli": "West", "Daman and Diu": "West",
    "Dadra and Nagar Haveli and Daman and Diu": "West",
}


def _norm(state):
    """Strip an India Compliance 'NN-State' prefix and surrounding whitespace."""
    if not state:
        return None
    s = str(state).strip()
    if "-" in s and s.split("-", 1)[0].strip().isdigit():
        s = s.split("-", 1)[1].strip()
    return s


def zone_for(state):
    return STATE_ZONE.get(_norm(state))


def validate(doc, method=None):
    # Auto-fill the zone from the state only when it's blank, so a manual override persists.
    if doc.get("zone"):
        return
    z = zone_for(doc.get("gst_state") or doc.get("state"))
    if z:
        doc.zone = z


@frappe.whitelist()
def zone_for_state(state):
    """Return the sales zone for a state (used by the Address form for live fill)."""
    return zone_for(state)
