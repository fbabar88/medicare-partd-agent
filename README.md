# Medicare Part D Agent (MVP)

A minimal Streamlit app that:
- Takes ZIP & medication list
- Calls CMS Plan Finder API
- Uses GPT-4 to generate plain-language summaries

## Setup

1. Clone the repo  
2. Create & activate a Python venv  
3. `pip install -r requirements.txt`  
4. Add your API keys in `.streamlit/secrets.toml`  
5. `streamlit run medicare_partd_agent_streamlit.py`

## Deployment

You can link this repo to Streamlit Cloud for one-click deploy.
