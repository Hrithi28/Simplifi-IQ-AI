# SimplifIQ — AI Lead Intelligence Automation

> **SimplifIQ Assessment Submission**  
> Automates the entire pipeline from lead form submission → company enrichment → PDF report generation → email delivery.

---

## Architecture Overview

```
Lead Form (HTML/JS)
      │
      ▼ POST /submit-lead
Flask Backend (app.py)
      │
      ├─→ enrichment.py
      │       ├─ Scrape company website (homepage + about + services)
      │       ├─ DuckDuckGo Instant Answers API
      │       └─ Gemini AI synthesis → structured JSON profile
      │
      ├─→ report_generator.py
      │       └─ ReportLab → 4-page professional PDF
      │
      ├─→ email_sender.py
      │       ├─ Resend API (primary)
      │       └─ SMTP fallback (Gmail / any)
      │
      └─→ sheets_logger.py (BONUS)
              ├─ Google Sheets — live leads tracker
              └─ Google Drive — PDF archiving
```

---

## Setup & Run

### 1. Clone & Install

```bash
git clone <repo-url>
cd simplifiq
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

**Minimum required keys:**
```
GEMINI_API_KEY=AIza...           # Free at aistudio.google.com (no credit card!)
RESEND_API_KEY=re_...            # For email delivery
FROM_EMAIL=reports@yourdomain.com
```

**Optional (bonus features):**
```
GOOGLE_SHEET_ID=...              # Sheets logging
GOOGLE_DRIVE_FOLDER_ID=...       # Drive archiving
GOOGLE_CREDENTIALS_FILE=credentials.json
```

### 3. Start Backend

```bash
cd backend
python app.py
# Server runs at http://localhost:5000
```

### 4. Open Frontend

Open `frontend/index.html` in your browser, or serve it:
```bash
python -m http.server 8080 --directory frontend
# Open http://localhost:8080
```

---

## API Reference

### `POST /submit-lead`
Triggers the full pipeline.

**Request body:**
```json
{
  "name": "Jane Smith",
  "email": "jane@company.com",
  "company": "Acme Corp",
  "website": "acmecorp.com",
  "industry": "SaaS / Software",
  "role": "CEO",
  "company_size": "51-200",
  "pain_points": "Manual lead qualification and onboarding"
}
```

**Response:**
```json
{
  "success": true,
  "status": "success",
  "message": "Your personalized audit report has been generated.",
  "processing_time_s": 38.5,
  "report_generated": true,
  "company_insights": {
    "name": "Acme Corp",
    "tagline": "...",
    "key_insights_count": 6
  }
}
```

### `GET /health`
Health check endpoint.

---

## Report Structure (4 pages)

| Page | Content |
|------|---------|
| 1 | Hero header · Executive Summary · Company KPI profile · Value Proposition |
| 2 | Core Services · Market Analysis · Industry Trends · Technology Signals |
| 3 | Digital Maturity Scores · AI Solution Recommendations · Simplification Opportunities |
| 4 | Intelligence Insights · Key Challenges · Growth Signals · Confidence Score · CTA |

---

## Technical Decisions & Tradeoffs

### Enrichment Strategy
- **Website scraping** (BeautifulSoup): Primary data source. Handles missing/incomplete pages gracefully.
- **DuckDuckGo Instant Answers**: Free API, no key required, good for company overviews.
- **Gemini AI synthesis**: Converts raw scraped text into a structured 15-field JSON profile. Falls back to rule-based heuristics if API key is not set.

### PDF Generation
- **ReportLab** (Python): Chosen over wkhtmltopdf/puppeteer for pure-Python portability, no browser dependency, and precise layout control. Dark theme with brand colors rendered as custom `Flowable` components.

### Email Delivery
- **Resend** (primary): Modern transactional email API, 100 free emails/day, excellent deliverability.
- **SMTP** (fallback): Works with Gmail (App Password), Mailgun, SendGrid SMTP relay.

### Fallback Handling
- Website unreachable → use company name + industry to generate a sensible profile
- AI API failure → rule-based keyword extraction from scraped text
- Email failure → PDF is still saved to `reports/` folder, success response still returned
- Sheets/Drive → non-blocking; any failure is logged but doesn't affect main pipeline

---

## Bonus Features

### Google Sheets Logging
Each submission appends a row: `Name | Email | Company | Industry | Role | Size | Website | Pain Points | Timestamp | Status`

Setup: Create a Sheet → share with your service account email → set `GOOGLE_SHEET_ID` in `.env`

### Google Drive Archiving
PDF reports are uploaded to a specified Drive folder after generation.

Setup: Create a Drive folder → share with service account → set `GOOGLE_DRIVE_FOLDER_ID`

---

## Project Structure

```
simplifiq/
├── backend/
│   ├── app.py              # Flask API server
│   ├── enrichment.py       # Scraping + AI synthesis
│   ├── report_generator.py # ReportLab PDF builder
│   ├── email_sender.py     # Resend + SMTP email
│   └── sheets_logger.py    # Google Sheets + Drive (bonus)
├── frontend/
│   └── index.html          # Single-page lead intake form
├── reports/                # Generated PDFs (auto-created)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Known Limitations

- **Bot detection**: Some websites (Cloudflare, aggressive WAFs) block scraping. Graceful fallback to rule-based profile.
- **Rate limits**: DuckDuckGo API has undocumented rate limits; heavy usage may need a paid news/search API (Serper, Bing Search).
- **PDF fonts**: ReportLab built-in fonts lack some Unicode characters; emoji are rendered as text fallbacks.
- **Email domains**: Resend free tier requires a verified domain for production; use SMTP fallback for immediate testing.

---

## Time Spent
~8 hours

## Self-Assessment
All core requirements implemented and functional. Bonus Sheets/Drive logging implemented. Report is professional and highly personalized via AI enrichment. The pipeline handles failure at every stage gracefully.
"# Simplifi-IQ" 
#
