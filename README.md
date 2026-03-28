# GOOGLE SEARCH CONSOLE API

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://search-console-api.streamlit.app/)

![GSC-API](https://github.com/ViniciusStanula/Search-Console-API/assets/48488978/77cb04de-fb46-4350-8d45-524decd2939f)

> A Streamlit web application that connects to the Google Search Console API and presents over 200,000 rows of data in charts and tables.

## 📋 Recent Changes

- **Replaced ECharts with Plotly** — Simplified charting with a lighter, more maintainable Plotly implementation.
- **Removed deprecated Streamlit values** — Updated deprecated API calls to align with current Streamlit versions.
- **Added daily breakdown filter** — New toggle to display table data broken down by individual days within the selected date range.
- **Pinned dependency versions** — The `requirements.txt` now specifies exact versions for all libraries to ensure reproducible builds.

## ☕ How to Use

1. Go to the [web application](https://search-console-api.streamlit.app/).
2. Click **"Log in to Google Search Console"** and enter your credentials.
3. Click **"Grant API Access"**.
4. Choose your metrics and click **"Fetch Data ✨"**.

Alternatively, clone this repository and run it locally.

## 🔧 Running Locally & Changing the Row Limit

The app fetches up to **300,000 rows** by batching multiple 25,000-row requests to the GSC API. If your site has fewer rows, the process simply finishes earlier.

To increase the limit or use your own credentials:

1. Replace `CLIENT_SECRET`, `CLIENT_ID`, and `REDIRECT_URI` with your own values.
   - Create OAuth **Web Application** credentials for the Search Console API in [Google Cloud Console](https://console.cloud.google.com/).
   - Set `REDIRECT_URI` to your app's URL (e.g., `http://localhost:8501/` for local development).
2. Update the row limit in the code:

```python
ROW_LIMIT = 300_000  # change to your desired value
```

### Work in Progress

The app is fully functional but still evolving — new charts and deeper analysis are planned. Feedback is welcome!

### Get in Touch

<p align="left">
  <a href="https://www.linkedin.com/in/vinicius-stanula/" target="_blank" alt="LinkedIn">
    <img src="https://img.shields.io/badge/-Linkedin-0e76a8?style=flat-square&logo=Linkedin&logoColor=white&link=LINK-DO-SEU-LINKEDIN" />
  </a>
</p>