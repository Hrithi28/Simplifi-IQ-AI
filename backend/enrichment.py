"""
enrichment.py — Company Data Enrichment
Scrapes company website + web search results,
then uses Google Gemini (free) to synthesize a structured intelligence profile.
"""

import os
import re
import json
import logging
import requests
from dotenv import load_dotenv
load_dotenv()
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
TIMEOUT = 10


def safe_get(url: str) -> str | None:
    """GET request with graceful failure."""
    try:
        normalized = url if url.startswith("http") else f"https://{url}"
        r = requests.get(normalized, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code == 200:
            return r.text
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
    return None


def extract_text(html: str, max_chars: int = 6000) -> str:
    """Clean and extract readable text from HTML."""
    soup = BeautifulSoup(html, 'lxml')
    for tag in soup(['script', 'style', 'nav', 'footer', 'iframe', 'noscript']):
        tag.decompose()
    text = soup.get_text(separator=' ', strip=True)
    text = re.sub(r'\s+', ' ', text)
    return text[:max_chars]


def scrape_website(website: str) -> dict:
    """Scrape homepage + about/services pages."""
    result = {"homepage": "", "about": "", "services": "", "title": "", "meta_description": ""}
    
    base = website if website.startswith("http") else f"https://{website}"
    html = safe_get(base)
    if not html:
        return result

    soup = BeautifulSoup(html, 'lxml')
    result["title"] = soup.title.string.strip() if soup.title else ""
    meta = soup.find("meta", attrs={"name": "description"})
    if meta:
        result["meta_description"] = meta.get("content", "")[:300]
    result["homepage"] = extract_text(html, 4000)

    # Try to fetch about / services pages
    links = soup.find_all('a', href=True)
    for anchor in links:
        href = anchor['href'].lower()
        text = anchor.get_text().lower()
        if any(kw in href or kw in text for kw in ['about', 'services', 'solutions', 'what-we-do']):
            full_url = urljoin(base, anchor['href'])
            if urlparse(full_url).netloc == urlparse(base).netloc:
                sub_html = safe_get(full_url)
                if sub_html:
                    key = "about" if "about" in href else "services"
                    if not result[key]:
                        result[key] = extract_text(sub_html, 2000)
                        break

    return result


def search_company_web(company: str, industry: str) -> str:
    """DuckDuckGo instant answers (no API key required)."""
    try:
        query = f"{company} {industry} company overview"
        url = f"https://api.duckduckgo.com/?q={requests.utils.quote(query)}&format=json&no_html=1"
        r = requests.get(url, headers=HEADERS, timeout=8)
        data = r.json()
        abstract = data.get("AbstractText", "")
        related = " | ".join(
            r.get("Text", "") for r in data.get("RelatedTopics", [])[:3] if isinstance(r, dict)
        )
        return f"{abstract} {related}".strip()[:1500]
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")
        return ""


def _build_prompt(lead: dict, scraped: dict, web_summary: str) -> str:
    """Build the shared prompt for any AI provider."""
    context = f"""
Company: {lead['company']}
Website: {lead['website']}
Industry: {lead['industry']}
Company Size: {lead['company_size']}
Contact: {lead['name']} ({lead['role']})
Stated Pain Points: {lead['pain_points'] or 'Not provided'}

--- Website Homepage ---
{scraped.get('homepage', '')[:2500]}

--- About Page ---
{scraped.get('about', '')[:1500]}

--- Services Page ---
{scraped.get('services', '')[:1500]}

--- Web Research ---
{web_summary[:1000]}
"""
    return f"""You are a senior business analyst preparing a company intelligence brief.

Based on the following data about a prospect company, produce a detailed JSON intelligence profile.

{context}

Return ONLY valid JSON (no markdown, no preamble) with this exact structure:
{{
  "company_name": "Official company name",
  "tagline": "One-line company positioning statement",
  "founding_year": "Year or 'Unknown'",
  "headquarters": "City, Country or 'Unknown'",
  "employee_count": "Estimated headcount range",
  "business_model": "B2B / B2C / B2B2C / SaaS / etc.",
  "core_services": ["service 1", "service 2", "service 3"],
  "target_market": "Description of their primary customers",
  "value_proposition": "2-3 sentence description of their unique value",
  "competitive_landscape": "Key competitors and market positioning",
  "growth_signals": ["signal 1", "signal 2"],
  "technology_stack_hints": ["tech 1", "tech 2"],
  "digital_maturity": "Low / Medium / High — with 1-line rationale",
  "opportunities_for_simplification": ["opportunity 1", "opportunity 2", "opportunity 3"],
  "recommended_ai_solutions": [
    {{"title": "Solution Name", "rationale": "Why it fits their business", "impact": "High/Medium/Low"}},
    {{"title": "Solution Name", "rationale": "Why it fits their business", "impact": "High/Medium/Low"}},
    {{"title": "Solution Name", "rationale": "Why it fits their business", "impact": "High/Medium/Low"}}
  ],
  "key_challenges": ["challenge 1", "challenge 2"],
  "insights": [
    "Insight 1 — specific, data-backed observation about their business",
    "Insight 2 — specific observation",
    "Insight 3 — specific observation",
    "Insight 4 — specific observation",
    "Insight 5 — specific observation"
  ],
  "executive_summary": "3-4 sentence executive summary of the company and the opportunity for engagement",
  "industry_trends": ["trend 1 relevant to their industry", "trend 2", "trend 3"],
  "sentiment": "Positive / Neutral / Cautious",
  "confidence_score": 0.85
}}"""


def _parse_json_response(text: str) -> dict:
    """Strip markdown fences and parse JSON."""
    text = re.sub(r'^```json\s*|^```\s*|```\s*$', '', text, flags=re.MULTILINE).strip()
    return json.loads(text)


def ai_synthesize(lead: dict, scraped: dict, web_summary: str) -> dict:
    """
    Use Google Gemini (free) to produce a structured company intelligence profile.
    Falls back to a rule-based profile if API key is not set.

    Get a free key at: https://aistudio.google.com
    Set: GEMINI_API_KEY=AIzaSyCvfbokUTmY-qsZi_AU16Bt4TJW94Bfkwo
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")
    prompt = _build_prompt(lead, scraped, web_summary)

    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                model_name="gemini-pro",          # Free tier model
                generation_config={"temperature": 0.3}, # Lower = more consistent JSON
            )
            response = model.generate_content(prompt)
            text = response.text.strip()
            result = _parse_json_response(text)
            logger.info("Gemini synthesis successful")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error from Gemini: {e}")
        except Exception as e:
            logger.error(f"Gemini synthesis failed: {e}")

    # Fallback: rule-based profile
    logger.warning("No GEMINI_API_KEY set or AI failed — using rule-based fallback profile")
    return _fallback_profile(lead, scraped)


def _fallback_profile(lead: dict, scraped: dict) -> dict:
    """Rule-based profile when AI is not available."""
    homepage_text = scraped.get("homepage", "")
    
    # Simple keyword-based service extraction
    services = []
    kws = {
        "consulting": ["consulting", "advisory", "strategy"],
        "software development": ["software", "development", "engineering"],
        "marketing": ["marketing", "brand", "digital"],
        "analytics": ["analytics", "data", "insights"],
        "automation": ["automation", "workflow", "process"],
    }
    for svc, words in kws.items():
        if any(w in homepage_text.lower() for w in words):
            services.append(svc)
    if not services:
        services = ["Professional Services", "Business Solutions"]

    return {
        "company_name": lead["company"],
        "tagline": scraped.get("meta_description", f"Leading solutions in {lead['industry']}"),
        "founding_year": "Unknown",
        "headquarters": "Unknown",
        "employee_count": lead.get("company_size", "Unknown"),
        "business_model": "B2B",
        "core_services": services[:4],
        "target_market": f"Businesses in the {lead['industry']} sector",
        "value_proposition": f"{lead['company']} provides professional services to help businesses achieve their goals efficiently.",
        "competitive_landscape": "Operating in a competitive market with opportunities for differentiation through AI-powered automation.",
        "growth_signals": ["Active web presence", "Engaged leadership team"],
        "technology_stack_hints": ["Web technologies", "Cloud infrastructure"],
        "digital_maturity": "Medium — Website present; automation opportunities identified",
        "opportunities_for_simplification": [
            "Lead intake and follow-up automation",
            "Client reporting and document generation",
            "Internal workflow optimization",
        ],
        "recommended_ai_solutions": [
            {"title": "AI Lead Qualification", "rationale": "Automate prospect scoring and outreach", "impact": "High"},
            {"title": "Document Automation", "rationale": "Generate proposals and reports at scale", "impact": "High"},
            {"title": "Process Intelligence", "rationale": "Identify and eliminate bottlenecks", "impact": "Medium"},
        ],
        "key_challenges": ["Manual processes slowing growth", "Scaling personalization"],
        "insights": [
            f"{lead['company']} operates in the {lead['industry']} space with clear growth potential.",
            "Digital transformation represents a key competitive differentiator.",
            "Automation of repetitive tasks could free significant team capacity.",
            "AI-driven personalization can improve client retention.",
            "Data-led decision-making would accelerate strategic growth.",
        ],
        "executive_summary": (
            f"{lead['company']} is an active player in the {lead['industry']} industry. "
            f"Based on our analysis, there are compelling opportunities to leverage AI automation "
            f"to streamline operations and drive growth. SimplifIQ is well-positioned to partner "
            f"on this transformation journey."
        ),
        "industry_trends": [
            f"AI adoption accelerating across {lead['industry']}",
            "Demand for personalized, data-driven client experiences",
            "Workflow automation becoming a competitive necessity",
        ],
        "sentiment": "Positive",
        "confidence_score": 0.65,
    }


def enrich_company(lead: dict) -> dict:
    """Main enrichment pipeline."""
    logger.info(f"Enriching: {lead['company']} ({lead['website']})")
    
    # Step 1: Scrape website
    scraped = scrape_website(lead['website'])
    logger.info(f"Website scraped — homepage: {len(scraped['homepage'])} chars")

    # Step 2: Web search
    web_summary = search_company_web(lead['company'], lead['industry'])
    logger.info(f"Web research: {len(web_summary)} chars")

    # Step 3: AI synthesis
    profile = ai_synthesize(lead, scraped, web_summary)
    
    # Add metadata
    profile["_scraped_title"] = scraped.get("title", "")
    profile["_scraped_meta"] = scraped.get("meta_description", "")
    profile["_enriched_at"] = __import__('datetime').datetime.utcnow().isoformat()

    return profile
