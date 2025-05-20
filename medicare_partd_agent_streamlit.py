import streamlit as st
import requests
import openai
from requests.exceptions import RequestException

# Configure your API keys in .streamlit/secrets.toml:
# OPENAI_API_KEY = "your_openai_api_key_here"
# CMS_PLAN_FINDER_KEY = "your_cms_api_key_here"

openai.api_key = st.secrets.get("OPENAI_API_KEY", "")

st.set_page_config(page_title="Medicare Part D Advisor", layout="centered")
st.title("Medicare Part D Plan Advisor MVP")

# ------- Helper Functions ------- #
def get_sample_plans(meds_list):
    """Return static sample plans for demo purposes."""
    return [
        {"plan_name": "Sample Plan A", "premium": 0, "tier_info": ", ".join([f"{m}: Tier 1" for m in meds_list])},
        {"plan_name": "Sample Plan B", "premium": 12, "tier_info": ", ".join([f"{m}: Tier 2" for m in meds_list])},
        {"plan_name": "Sample Plan C", "premium": 25, "tier_info": ", ".join([f"{m}: Tier 3" for m in meds_list])}
    ]


def lookup_partd_plans(zip_code, meds_list):
    """
    Fetch Part D plans via CMS API if a key is provided; otherwise, return sample plans.
    On any API error, fall back to sample data without retrying.
    """
    key = st.secrets.get('CMS_PLAN_FINDER_KEY', '')
    if not key:
        st.warning("No CMS API key found; displaying sample plans.")
        return get_sample_plans(meds_list)

    endpoint = "https://api.cms.gov/plan-finder/v1/part-d"
    headers = {"Authorization": f"Bearer {key}"}
    payload = {"zipCode": zip_code, "medications": meds_list, "topN": 3}

    try:
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("plans", [])
    except RequestException as e:
        st.error(f"Error fetching real plans: {e}. Showing sample data.")
        return get_sample_plans(meds_list)

    # Parse API response
    plans = []
    for p in data:
        plans.append({
            "plan_name": p.get("planDisplayName", "N/A"),
            "premium": p.get("monthlyPremium", 0),
            "tier_info": ", ".join([f"{d.get('drugName')}: Tier {d.get('tier')}" for d in p.get("drugList", [])])
        })
    if not plans:
        st.info("No plans returned from CMS; displaying sample data.")
        return get_sample_plans(meds_list)

    return plans


def make_prompt(zip_code, meds_list, plans):
    header = f"User in {zip_code} takes: {', '.join(meds_list)}.\nHere are three Part D plans:\n"
    body_lines = [f"- {p['plan_name']}: ${p['premium']} premium, {p['tier_info']}" for p in plans]
    tail = "\nPlease summarize in plain language which plan is best for this user and why." 
    return header + "\n".join(body_lines) + tail

# ------- UI ------- #
zip_code = st.text_input("Enter Your ZIP Code")
meds_input = st.text_area("List Your Medications (comma-separated)")

if st.button("Find My Plans"):
    if not zip_code or not meds_input:
        st.error("Please provide both ZIP code and at least one medication.")
    else:
        meds_list = [m.strip() for m in meds_input.split(",") if m.strip()]
        with st.spinner("Looking up Part D plans..."):
            plans = lookup_partd_plans(zip_code, meds_list)
        if plans:
            st.subheader("Top 3 Plans")
            for idx, p in enumerate(plans, 1):
                st.markdown(f"**{idx}. {p['plan_name']}**")
                st.write(f"- Monthly Premium: ${p['premium']}")
                st.write(f"- Drug Tiers: {p['tier_info']}")

            # LLM Explanation
            if openai.api_key:
                prompt = make_prompt(zip_code, meds_list, plans)
                with st.spinner("Generating plain-language summary..."):
                    response = openai.ChatCompletion.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "You are a friendly Medicare advisor."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=200
                    )
                    explanation = response.choices[0].message.content
                    st.subheader("Why This Plan?")
                    st.write(explanation)
            else:
                st.info("OpenAI API key not found; skip LLM summary.")
        else:
            st.warning("No plans found. Please check your inputs and try again.")

st.markdown("---")
st.caption("MVP prototype: ZIP + meds → Part D lookup → LLM summary (or sample data)")
