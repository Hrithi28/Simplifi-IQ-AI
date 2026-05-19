"""
SimplifIQ — AI-Powered Lead Intake & Automation Backend
Handles: lead capture → data enrichment → PDF report → email delivery
"""

import os
import json
import time
import re
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

from enrichment import enrich_company
from report_generator import generate_report
from email_sender import send_report_email
from sheets_logger import log_to_sheets, archive_to_drive

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

REPORTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)


def validate_lead(data: dict) -> tuple[bool, str]:
    required = ['name', 'email', 'company', 'website', 'industry']
    for field in required:
        if not data.get(field, '').strip():
            return False, f"Missing required field: {field}"
    email_re = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_re, data['email']):
        return False, "Invalid email address"
    return True, ""


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


@app.route('/submit-lead', methods=['POST'])
def submit_lead():
    start_time = time.time()
    data = request.get_json(force=True)
    logger.info(f"New lead submission: {data.get('email', 'unknown')}")

    # 1. Validate
    valid, err = validate_lead(data)
    if not valid:
        return jsonify({"success": False, "error": err}), 400

    lead = {
        "name": data['name'].strip(),
        "email": data['email'].strip().lower(),
        "company": data['company'].strip(),
        "website": data['website'].strip(),
        "industry": data['industry'].strip(),
        "role": data.get('role', 'Decision Maker').strip(),
        "pain_points": data.get('pain_points', '').strip(),
        "company_size": data.get('company_size', 'Unknown'),
        "submitted_at": datetime.utcnow().isoformat(),
    }

    report_status = "success"
    pdf_path = None
    enriched = {}

    try:
        # 2. Enrich
        logger.info("Starting enrichment...")
        enriched = enrich_company(lead)
        logger.info(f"Enrichment complete: {len(enriched)} data points")

        # 3. Generate PDF
        logger.info("Generating PDF report...")
        pdf_path = generate_report(lead, enriched, REPORTS_DIR)
        logger.info(f"PDF generated: {pdf_path}")

        # 4. Archive PDF to Google Drive (bonus - non-fatal)
        try:
            drive_url = archive_to_drive(pdf_path)
            if drive_url:
                logger.info(f"PDF archived to Drive: {drive_url}")
        except Exception as e:
            logger.warning(f"Drive archiving skipped: {e}")

        # 5. Send email
        logger.info("Sending email...")
        email_sent = send_report_email(lead, pdf_path, enriched)
        if not email_sent:
            logger.warning("Email delivery failed (non-fatal)")

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        report_status = "partial_failure"

    # 5. Log to Sheets (bonus - non-fatal)
    try:
        log_to_sheets(lead, report_status)
    except Exception as e:
        logger.warning(f"Sheets logging skipped: {e}")

    elapsed = round(time.time() - start_time, 2)
    logger.info(f"Lead pipeline completed in {elapsed}s — status: {report_status}")

    return jsonify({
        "success": True,
        "status": report_status,
        "message": "Your personalized audit report has been generated and will be sent to your email.",
        "lead_id": lead['email'],
        "processing_time_s": elapsed,
        "report_generated": pdf_path is not None,
        "company_insights": {
            "name": enriched.get("company_name", lead["company"]),
            "tagline": enriched.get("tagline", ""),
            "key_insights_count": len(enriched.get("insights", [])),
        }
    })


@app.route('/demo-report', methods=['POST'])
def demo_report():
    """Returns a demo/preview of the enrichment output."""
    data = request.get_json(force=True)
    valid, err = validate_lead(data)
    if not valid:
        return jsonify({"success": False, "error": err}), 400

    lead = {
        "name": data['name'].strip(),
        "email": data['email'].strip().lower(),
        "company": data['company'].strip(),
        "website": data['website'].strip(),
        "industry": data['industry'].strip(),
        "role": data.get('role', '').strip(),
        "pain_points": data.get('pain_points', '').strip(),
        "company_size": data.get('company_size', 'Unknown'),
        "submitted_at": datetime.utcnow().isoformat(),
    }

    enriched = enrich_company(lead)
    return jsonify({"success": True, "enriched": enriched, "lead": lead})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
