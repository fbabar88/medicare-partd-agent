import streamlit as st
import requests
import openai

# Configure your API keys in .streamlit/secrets.toml:
# CMS_PLAN_FINDER_KEY = "your_cms_api_key_here"
# OPENAI_API_KEY       = "your_openai_api_key_here"

openai.api_key = st.secrets["OPENAI_API_KEY"]

st.set_page_config(page_title="Medicare Part D Advisor", layout="centered")
st.title("Medicare Part D Plan Advisor MVP")

# ------- Helper Functions ------- #

def lookup_partd_plans(zip_code, meds_list):
    """
    Call the CMS Plan Finder API to fetch Part D plans matching the given ZIP and medications.
    Returns a list of dicts: [{"plan_name": ..., "premium": ..., "tier_info": ...}, ...]
    """
    endpoint = "https://api.cms.gov/plan-finder/v1/part-d"  # placeholder
    headers = {"Authorization": f"Bearer {st.secrets['CMS_PLAN_FINDER_KEY']}"}
    payload = {
        "zipCode": zip_code,
        "medications": meds_list,
        "topN": 3
    }
    try:
        resp = requests.post(endpoint, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json().get("plans", [])
        plans = []
        for p in data:
            plans.append({
                "plan_name": p.get("planDisplayName"),
                "premium": p.get("monthlyPremium"),
                "tier_info": ", ".join([f"{d['drugName']}: Tier {d['tier']}" for d in p.get("drugList", [])])
            })
        return plans
    except Exception as e:
        st.error(f"Error fetching plans: {e}")
        return []


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
            st.warning("No plans found. Please check your inputs and try again.")

# ------- End of MVP ------- #

st.markdown("---")
st.caption("MVP prototype: ZIP + meds to Part D lookup + LLM summary")
