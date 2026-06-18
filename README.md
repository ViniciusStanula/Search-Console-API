# Google Search Console API

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://search-console-api.streamlit.app/)

![GSC-API](https://github.com/ViniciusStanula/Search-Console-API/assets/48488978/77cb04de-fb46-4350-8d45-524decd2939f)

Pull your Google Search Console data into a dashboard — up to 500,000 rows per query, with filters, charts, and Excel export. Built with Python and Streamlit.

The GSC interface caps you at 1,000 rows. This app uses the Search Analytics API to batch-fetch up to 500k rows across keywords, pages, or both.

## How to Use

1. Go to [search-console-api.streamlit.app](https://search-console-api.streamlit.app/)
2. Log in with your Google account and click **Grant API access**
3. Enter your domain or property URL exactly as it appears in GSC
4. Pick your metric, set the date range, hit **Fetch Data ✨**

## What It Does

- Fetches up to **500,000 rows** via batched API requests (25k per call)
- Dimensions: Keywords, Pages, Pages per Keyword, Keywords per Page
- Filter by URL or keyword — contains, not contains, or regex
- Date range up to 16 months back
- Daily breakdown mode for the table view
- Clicks / Impressions / CTR / Position chart over time
- Export to Excel

## Running Locally

```bash
pip install -r requirements.txt
streamlit run home.py
```

You'll need your own OAuth credentials:

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials
2. Create an **OAuth 2.0 Client ID** (Web Application) with the Search Console API enabled
3. Add `http://localhost:8501/` as an authorized redirect URI
4. Add your credentials to `.streamlit/secrets.toml`:

```toml
clientId = "your-client-id"
clientSecret = "your-client-secret"
```

5. Update `REDIRECT_URI` in `views/gsc_api.py` to `http://localhost:8501/`

The row limit defaults to 500,000. Change `ROW_LIMIT` in `views/gsc_api.py` if needed.

## Get in Touch

<p align="left">
  <a href="https://www.linkedin.com/in/vinicius-stanula/" target="_blank">
    <img src="https://img.shields.io/badge/-LinkedIn-0e76a8?style=flat-square&logo=Linkedin&logoColor=white" />
  </a>
</p>
