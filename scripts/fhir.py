"""Records Stream Check-up writes to the OneAquaHealth health-data system (HL7 FHIR R4).

Pure builders, no network. Two kinds of record:
  - Location       one per research stream, carrying the code the map data uses,
                   so the two systems finally share a name for each stream.
  - DetectedIssue  a note pinned to a record that cannot be right, with the likely
                   correction. The original record is never changed.
"""
SITE_CODES = "https://api.enora-oah.eu/api/sites"
TAGS = "urn:stream-checkup:tags"
ISSUE_IDS = "urn:stream-checkup:record-problem"
LOCATION_PROFILE = "http://hl7.eu/fhir/ig/oah/StructureDefinition/location-oah"
RIVER = {"system": "http://snomed.info/sct", "code": "420531007", "display": "River"}


def tag(code, display):
    return {"system": TAGS, "code": code, "display": display}


def location(stream):
    return {
        "resourceType": "Location",
        "meta": {"profile": [LOCATION_PROFILE], "tag": [tag("site-link", "Stream Check-up site link")]},
        "identifier": [{"system": SITE_CODES, "value": stream["code"]}],
        "status": "active",
        "name": stream["name"],
        "description": f"OneAquaHealth research site {stream['code']}, {stream['city']}",
        "mode": "instance",
        "type": [{"coding": [RIVER]}],
        "address": {"city": stream["city"]},
        "position": {"longitude": stream["lon"], "latitude": stream["lat"]},
    }


def record_problem(found, today):
    """A note about one impossible value. `found` is an item from checkup.impossible_values."""
    detail = (f"Recorded {found['what']} of {found['value']:,.0f}. "
              f"The possible range is {found['low']:g} to {found['high']:g}.")
    if found["likely"] is not None:
        action = (f"Likely meant {found['likely']:g} (the recorded value divided by {found['factor']:,}). "
                  "Confirm against the original lab sheet before changing the record.")
    else:
        action = "Check the original lab sheet. No simple correction fits."
    return {
        "resourceType": "DetectedIssue",
        "meta": {"tag": [tag("record-problem", "Stream Check-up record problem")]},
        "identifier": [{"system": ISSUE_IDS, "value": found["id"]}],
        "status": "preliminary",
        "code": {"text": "Value outside the possible range"},
        "severity": "high",
        "identifiedDateTime": today,
        "author": {"display": "Stream Check-up"},
        "implicated": [{"reference": f"Observation/{found['id']}"}],
        "detail": detail,
        "mitigation": [{"action": {"text": action}}],
    }


def create_if_absent(resources):
    """One all-or-nothing bundle. Each record is created only if its identifier is not there yet,
    so sending twice never makes duplicates."""
    entries = []
    for res in resources:
        ident = res["identifier"][0]
        entries.append({
            "resource": res,
            "request": {
                "method": "POST",
                "url": res["resourceType"],
                "ifNoneExist": f"identifier={ident['system']}|{ident['value']}",
            },
        })
    return {"resourceType": "Bundle", "type": "transaction", "entry": entries}
