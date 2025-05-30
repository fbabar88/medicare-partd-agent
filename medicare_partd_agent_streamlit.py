import streamlit as st
import socket
import requests
import openai
import xml.etree.ElementTree as ET
from requests.exceptions import RequestException

# DNS resolution check for api.cms.gov
try:
    ip = socket.gethostbyname("api.cms.gov")
    st.write(f"api.cms.gov resolves to {ip}")
except Exception as e:
    st.error(f"DNS lookup failed: {e}")

# Configure your API keys in .streamlit/secrets.toml:
# OPENAI_API_KEY      = "sk-...your OpenAI key..."
# CMS_PLAN_FINDER_KEY = "eyJhbGciOi...your CMS key..."

openai.api_key = st.secrets.get("OPENAI_API_KEY", "")

st.set_page_config(page_title="Medicare Part D Advisor", layout="centered")
st.title("Medicare Part D Plan Advisor MVP")

# ------- XML Request & Parsing Helpers ------- #
def build_xml_request(zip_code, meds_list, top_n=3):
    """Constructs the XML payload for CMS Part D Plan Finder."""
    root = ET.Element("FindPlansRequest")
    ET.SubElement(root, "ZipCode").text = zip_code
    ET.SubElement(root, "ServiceType").text = "PartD"
    ET.SubElement(root, "TopN").text = str(top_n)

    drugs = ET.SubElement(root, "Drugs")
    for med in meds_list:
        drug = ET.SubElement(drugs, "Drug")
        ET.SubElement(drug, "DrugName").text = med

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def lookup_partd_plans_xml(zip_code, meds_list):
    """
    Sends the XML request to CMS Plan Finder and returns the XML response string.
    """
    xml_payload = build_xml_request(zip_code, meds_list)
    headers = {
        "Authorization": f"Bearer {st.secrets['CMS_PLAN_FINDER_KEY']}",
        "Content-Type":  "application/xml",
        "Accept":        "application/xml",
    }
    try:
        resp = requests.post(
            "https://api.cms.gov/plan-finder/v1/part-d",
            data=xml_payload,
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        return resp.text
    except RequestException as e:
        st.error(f"API request failed: {e}")
        return None


def parse_plans_from_xml(xml_str):
    """
    Parses the CMS XML response into a list of plan dicts.
    """
    if not xml_str:
        return []

    root = ET.fromstring(xml_str)
    plans = []
    for plan in root.findall(".//Plan"):
        name    = plan.findtext("PlanDisplayName", default="N/A")
        premium = plan.findtext("MonthlyPremium", default="0")
        try:
            premium = float(premium)
        except ValueError:
            premium = 0.0

        tier_info = []
        for d in plan.findall(".//Drug"):
            drug_name = d.findtext("DrugName", default="Unknown")
            tier       = d.findtext("Tier", default="Unknown")
            tier_info.append(f"{drug_name}: Tier {tier}")

        plans.append({
            "plan_name": name,
            "premium": premium,
            "tier_info": ", ".join(tier_info)
        })

    # Return top 3 by lowest premium
    return sorted(plans, key=lambda x: x["premium"])[:3]

# ------- LLM Prompt Helper ------- #
def make_prompt(zip_code, meds_list, plans):
    header
