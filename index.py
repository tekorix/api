#!/usr/bin/env python3
"""
Returns JSON with detailed parsed phone number info and validity checks.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS  # make sure flask_cors is installed
import phonenumbers
from phonenumbers import PhoneNumberType, PhoneNumberFormat
from phonenumbers import carrier as carrier_mod, geocoder as geocoder_mod, timezone as timezone_mod
import logging
import os

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------- CORS FIX --------------------
# 1. Explicitly allow all origins, methods, and headers for /api/*
CORS(app, resources={r"/*": {"origins": "*"}})
# --------------------------------------------------

# Type mapping
TYPE_MAP = {
    PhoneNumberType.MOBILE: "Mobile",
    PhoneNumberType.FIXED_LINE: "Fixed Line",
    PhoneNumberType.FIXED_LINE_OR_MOBILE: "Fixed Line or Mobile",
    PhoneNumberType.TOLL_FREE: "Toll Free",
    PhoneNumberType.PREMIUM_RATE: "Premium Rate",
    PhoneNumberType.SHARED_COST: "Shared Cost",
    PhoneNumberType.VOIP: "VoIP",
    PhoneNumberType.PERSONAL_NUMBER: "Personal Number",
    PhoneNumberType.PAGER: "Pager",
    PhoneNumberType.UAN: "UAN",
    PhoneNumberType.UNKNOWN: "Unknown"
}


def get_number_info(number_str: str, region: str | None = None, language: str = "en") -> dict:
    """Parse a phone number string and return a structured info dict."""
    try:
        if region:
            parsed = phonenumbers.parse(number_str, region.upper())
        else:
            parsed = phonenumbers.parse(number_str, None)
    except phonenumbers.NumberParseException as e:
        return {"error": "NumberParseException", "message": str(e)}

    # Basic checks
    is_valid = phonenumbers.is_valid_number(parsed)
    is_possible = phonenumbers.is_possible_number(parsed)

    number_type = phonenumbers.number_type(parsed)
    type_str = TYPE_MAP.get(number_type, "Unknown")

    # Formats
    international_format = phonenumbers.format_number(parsed, PhoneNumberFormat.INTERNATIONAL)
    national_format = phonenumbers.format_number(parsed, PhoneNumberFormat.NATIONAL)
    e164_format = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
    rfc3966 = phonenumbers.format_number(parsed, PhoneNumberFormat.RFC3966)

    # Region, country code
    region_code = phonenumbers.region_code_for_number(parsed)
    country_code = parsed.country_code

    # Carrier and geocoding
    try:
        carrier_name = carrier_mod.name_for_number(parsed, language) or ""
    except Exception:
        carrier_name = ""
    try:
        geo_description = geocoder_mod.description_for_number(parsed, language) or ""
    except Exception:
        geo_description = ""

    # Time zones
    try:
        tz = list(timezone_mod.time_zones_for_number(parsed))
    except Exception:
        tz = []

    return {
        "input": number_str,
        "region_hint": (region.upper() if region else None),
        "valid": is_valid,
        "possible": is_possible,
        "type": type_str,
        "type_code": int(number_type),
        "region_code": region_code,
        "country_code": int(country_code),
        "international_format": international_format,
        "national_format": national_format,
        "e164": e164_format,
        "rfc3966": rfc3966,
        "carrier": carrier_name,
        "geolocation": geo_description,
        "time_zones": tz,
    }


@app.route("/", methods=["GET"])
def index():
    return (
        "<h3>Phone number parsing API</h3>"
        "<p>POST JSON to <code>/api/parse</code> with <code>{'number': '+771632960960'}</code></p>"
        "<p>Health check: <code>/api/health</code></p>"
    )


@app.route("/api/health", methods=["GET", "OPTIONS"])
def health():
    """Health check endpoint to keep the function warm."""
    logger.info("Health check called")
    return jsonify({"status": "healthy", "timestamp": __import__('time').time()}), 200


@app.route("/api/parse", methods=["OPTIONS", "POST"])
def api_parse():
    """Handle both OPTIONS preflight and POST requests."""
    
    # Handle OPTIONS preflight request
    if request.method == "OPTIONS":
        logger.info("Handling OPTIONS preflight request")
        response = app.make_default_options_response()
        # CORS headers are already added by @app.after_request
        return response
    
    # Handle POST request
    logger.info("Processing POST request")
    
    # Accept JSON or form-encoded data
    data = None
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict() or request.get_json(silent=True) or {}

    number = data.get("number") or data.get("phone")
    if not number:
        return jsonify({
            "success": False, 
            "error": "missing_parameter", 
            "message": "`number` is required in JSON body or form data."
        }), 400

    region = data.get("region")
    language = data.get("language", "en")

    logger.info(f"Parsing number={number} region={region}")
    info = get_number_info(number, region, language)

    if "error" in info:
        return jsonify({"success": False, "error": info}), 400

    return jsonify({"success": True, "data": info}), 200


# This is for local development
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
