import streamlit as st
import os
import pandas as pd
from datetime import date as date_today
from dateutil.relativedelta import relativedelta
from io import BytesIO
import time
import urllib.parse

import requests as rq
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from googleapiclient import discovery
from pyexcelerate import Workbook
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from pandas.api.types import (
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)
import functions as fc

today = date_today.today()
DATE_END = today - relativedelta(days=2)
DATE_START = today - relativedelta(months=16)
DATE_DEFAULT = today - relativedelta(months=1)

CLIENT_SECRET = st.secrets["clientSecret"]
CLIENT_ID = st.secrets["clientId"]
REDIRECT_URI = 'https://search-console-api.streamlit.app'

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
TOKEN_URI = "https://oauth2.googleapis.com/token"

AUTH_HREF = (
    "https://accounts.google.com/o/oauth2/auth"
    f"?response_type=code&client_id={CLIENT_ID}"
    f"&redirect_uri={REDIRECT_URI}"
    f"&scope={SCOPES[0]}"
    "&access_type=offline&prompt=consent"
)

OAUTH_CLIENT_CONFIG = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uris": [],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": TOKEN_URI,
    }
}

flow = Flow.from_client_config(
    OAUTH_CLIENT_CONFIG,
    scopes=SCOPES,
    redirect_uri=REDIRECT_URI,
)
flow.code_verifier = None
auth_url, _ = flow.authorization_url(prompt="consent")

METRICS_TO_DIMENSIONS = {
    "Keywords": ["query"],
    "Pages": ["page"],
    "Pages per Keyword": ["query", "page"],
    "Keywords per Page": ["page", "query"],
}

DIMENSION_KEY_MAP = {"page": "Page", "query": "Keyword", "date": "Date"}

FILTER_OPTIONS = ("contains", "notcontains", "includingRegex", "excludingRegex")

ROW_LIMIT = 300_000
BATCH_SIZE = 25_000

CHART_COLORS = {
    "clicks": "#8be9fd",
    "impressions": "#ffb86c",
    "ctr": "#50fa7b",
    "position": "#ff79c6",
    "bg": "#282a36",
    "text": "#f8f8f2",
    "grid": "#44475a",
}


def button_callback():
    try:
        code = urllib.parse.unquote(st.query_params["code"])
        token_response = rq.post(
            TOKEN_URI,
            data={
                "code": code,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        token_data = token_response.json()
        if "error" in token_data:
            st.error(f"⚠️ Token exchange failed: {token_data.get('error_description', token_data['error'])}")
            return
        st.session_state.my_token_received = True
        st.session_state.my_token_input = code
        st.session_state.google_creds = {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
        }
    except (KeyError, ValueError):
        st.error("⚠️ The parameter 'code' was not found in the URL. Please log in.")


def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    modify = st.checkbox("Add Filters")
    if not modify:
        return df

    df = df.copy()

    for col in df.columns:
        if is_object_dtype(df[col]):
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass
        if is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    modification_container = st.container()
    with modification_container:
        to_filter_columns = st.multiselect("Filter Dataframe for:", df.columns)
        for column in to_filter_columns:
            left, right = st.columns((1, 20))
            is_ctr_column = column == 'CTR' and is_numeric_dtype(df[column])

            if isinstance(df[column].dtype, pd.CategoricalDtype) or df[column].nunique() < 10:
                user_cat_input = right.multiselect(
                    f"Values for: {column}",
                    df[column].unique(),
                    default=list(df[column].unique()),
                )
                df = df[df[column].isin(user_cat_input)]

            elif is_numeric_dtype(df[column]):
                _min = float(df[column].min())
                _max = float(df[column].max())
                step = (_max - _min) / 100

                if is_ctr_column:
                    user_num_input = right.slider(
                        f"Values for: {column}",
                        min_value=_min * 100,
                        max_value=_max * 100,
                        value=(_min * 100, _max * 100),
                        step=step * 100,
                    )
                    user_num_input = (user_num_input[0] / 100, user_num_input[1] / 100)
                else:
                    user_num_input = right.slider(
                        f"Values for: {column}",
                        min_value=_min,
                        max_value=_max,
                        value=(_min, _max),
                        step=step,
                        format="%.2f",
                    )
                df = df[df[column].between(*user_num_input)]

            elif is_datetime64_any_dtype(df[column]):
                user_date_input = right.date_input(
                    f"Values for: {column}",
                    value=(df[column].min(), df[column].max()),
                )
                if len(user_date_input) == 2:
                    start_date, end_date = map(pd.to_datetime, user_date_input)
                    df = df.loc[df[column].between(start_date, end_date)]

            else:
                user_text_input = right.text_input(f"String or Regex for: {column}")
                if user_text_input:
                    df = df[df[column].astype(str).str.contains(user_text_input)]

    return df


def to_excel(df):
    output = BytesIO()
    wb = Workbook()
    ws = wb.new_sheet("GSC-API-Data")  # Original: "Dados-API-GSC"

    columns = df.columns.tolist()
    data = [columns] + df.values.tolist()

    for row_index, row_data in enumerate(data, start=1):
        for col_index, cell_value in enumerate(row_data, start=1):
            ws[row_index][col_index].value = cell_value

    wb.save(output)
    return output.getvalue()


def check_input_url(input_url):
    if "https://" in input_url or "http://" in input_url:
        return input_url
    return f'sc-domain:{input_url}'


def _build_dimension_filters(url_filter, url_operator, keyword_filter, keyword_operator):
    filter_groups = []
    if url_filter and url_operator:
        filter_groups.append({
            'filters': [{'dimension': 'PAGE', 'operator': url_filter, 'expression': url_operator}]
        })
    if keyword_filter and keyword_operator:
        filter_groups.append({
            'filters': [{'dimension': 'QUERY', 'operator': keyword_filter, 'expression': keyword_operator}]
        })
    return filter_groups or None


def _run_progress_bar(label="Retrieving Metrics. Please Wait. 🐈"):
    bar = st.progress(0, text=label)

    def update(current, total):
        progress = min(current / total, 1.0)
        bar.progress(progress, text=label)

    def finish():
        bar.progress(1.0, text="Processing is now finished 😸")
        time.sleep(2)
        bar.empty()

    return update, finish


def _rows_to_dataframe(data, dimensions):
    key_names = [DIMENSION_KEY_MAP.get(d, d.capitalize()) for d in dimensions]

    records = []
    for row in data:
        record = {name: row['keys'][i] for i, name in enumerate(key_names)}
        record.update({
            'Clicks': row['clicks'],
            'Impressions': row['impressions'],
            'CTR': row['ctr'],
            'Position': row['position'],
        })
        records.append(record)

    return pd.DataFrame(records)


@st.cache_resource(show_spinner=False)
def get_webproperty(_creds_dict):
    creds = Credentials(
        token=_creds_dict["access_token"],
        refresh_token=_creds_dict.get("refresh_token"),
        token_uri=TOKEN_URI,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )
    return discovery.build(
        serviceName="webmasters",
        version="v3",
        credentials=creds,
        cache_discovery=False,
    )


def _fetch_gsc_data(property_url, dimensions, start_date, end_date,
                     url_filter=None, url_operator=None,
                     keyword_filter=None, keyword_operator=None,
                     row_limit=ROW_LIMIT):
    service = get_webproperty(st.session_state.google_creds)
    dimension_filters = _build_dimension_filters(url_filter, url_operator, keyword_filter, keyword_operator)
    update_progress, finish_progress = _run_progress_bar()

    data = []
    start_row = 0

    while start_row == 0 or (start_row % BATCH_SIZE == 0 and start_row < row_limit):
        request_body = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': dimensions,
            'rowLimit': BATCH_SIZE,
            'startRow': start_row,
        }
        if dimension_filters:
            request_body['dimensionFilterGroups'] = dimension_filters

        response = service.searchanalytics().query(siteUrl=property_url, body=request_body).execute()
        rows = response.get('rows', [])
        start_row += len(rows)
        data.extend(rows)
        update_progress(start_row, row_limit)

    finish_progress()
    return data


@st.cache_data(show_spinner=False)
def get_data(property_url, dimensions, start_date, end_date,
             url_filter=None, url_operator=None,
             keyword_filter=None, keyword_operator=None):
    data = _fetch_gsc_data(
        property_url, dimensions, start_date, end_date,
        url_filter, url_operator, keyword_filter, keyword_operator,
    )
    return _rows_to_dataframe(data, dimensions)


@st.cache_data(show_spinner=False)
def get_data_date(property_url, start_date, end_date,
                  url_filter=None, url_operator=None,
                  keyword_filter=None, keyword_operator=None):
    data = _fetch_gsc_data(
        property_url, ['date'], start_date, end_date,
        url_filter, url_operator, keyword_filter, keyword_operator,
        row_limit=1000,
    )
    return _rows_to_dataframe(data, ['date'])


@st.cache_data(show_spinner=False)
def get_data_daily(property_url, dimensions, start_date, end_date,
                   url_filter=None, url_operator=None,
                   keyword_filter=None, keyword_operator=None):
    daily_dimensions = ['date'] + list(dimensions)
    data = _fetch_gsc_data(
        property_url, daily_dimensions, start_date, end_date,
        url_filter, url_operator, keyword_filter, keyword_operator,
    )
    return _rows_to_dataframe(data, daily_dimensions)


@st.cache_data(show_spinner=False)
def plot_metrics_chart(df_grouped):
    df_grouped = df_grouped.copy()
    df_grouped['CTR'] = df_grouped['CTR'] * 100
    df_grouped['Position'] = df_grouped['Position'].round(2)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    traces = [
        ("Clicks", CHART_COLORS["clicks"], False, False),
        ("Impressions", CHART_COLORS["impressions"], True, False),
        ("CTR", CHART_COLORS["ctr"], False, True),
        ("Position", CHART_COLORS["position"], True, True),
    ]

    for name, color, secondary, legend_only in traces:
        fig.add_trace(
            go.Scatter(
                x=df_grouped['Date'], y=df_grouped[name], name=name,
                line=dict(width=2.4, color=color, shape='spline'), mode='lines',
                visible='legendonly' if legend_only else True,
            ),
            secondary_y=secondary,
        )

    fig.update_layout(
        plot_bgcolor=CHART_COLORS["bg"],
        paper_bgcolor=CHART_COLORS["bg"],
        font_color=CHART_COLORS["text"],
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        height=400,
        margin=dict(l=65, r=65, t=45, b=50),
        hovermode='x unified',
    )
    fig.update_xaxes(gridcolor=CHART_COLORS["grid"])
    fig.update_yaxes(title_text="Clicks", gridcolor=CHART_COLORS["grid"], secondary_y=False)
    fig.update_yaxes(title_text="Impressions", gridcolor=CHART_COLORS["grid"], showgrid=False, secondary_y=True)

    st.plotly_chart(fig, use_container_width=True)


def display_metric_cards(df):
    met1, met2, met3, met4 = st.columns(4)
    with met1:
        st.metric('Clicks:', f'{df["Clicks"].sum():,}')
    with met2:
        st.metric('Impressions:', f'{df["Impressions"].sum():,}')
    with met3:
        st.metric('CTR:', f'{df["CTR"].mean() * 100:.2f}%')
    with met4:
        st.metric('Position:', f'{df["Position"].mean():.1f}')


def excel_download_button(df, key):
    if st.checkbox('Generate Excel', key=key):
        excel_filename = f'API-GSC-{st.session_state.domain}.xlsx'
        st.download_button(
            label='📥 Download Excel',
            data=to_excel(df),
            file_name=excel_filename,
            key=f'download_{key}',
        )


def _section_divider(label):
    st.markdown(
        f'<p style="font-size:0.7rem; font-weight:600; color:rgba(150,150,150,0.7); '
        f'letter-spacing:0.05em; text-transform:uppercase; margin:0.6rem 0 0.4rem; '
        f'padding-bottom:0.25rem; border-bottom:1px solid rgba(150,150,150,0.15);">'
        f'{label}</p>',
        unsafe_allow_html=True,
    )


def init_session_state():
    defaults = {
        "my_token_input": "",
        "my_token_received": False,
        "dataframe": None,
        "domain": None,
        "dataframeData": None,
        "dataframe_daily": None,
        "clicked": False,
        "auth_code": "",
        "google_creds": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def createPage():
    col_icon, col_title = st.columns([0.06, 0.99])
    with col_icon:
        st.image(fc.open_image("./assets/robozin2.png"))
    with col_title:
        st.header("Google Search Console API")
        st.markdown(
            '<p class="minha-classe">By '
            '<a href="https://www.linkedin.com/in/vinicius-stanula/?locale=en-US">Vinicius Stanula</a>'
            ', made in Streamlit 🎈</p>',
            unsafe_allow_html=True,
        )

    init_session_state()

    def click_button():
        st.session_state.clicked = True

    st.markdown("----")

    with st.expander("🔑 Log in to Google Search Console"):
        link_style = (
            "text-decoration: none; color: #FFF; padding: 8px 20px; "
            "border-radius: 4px; background-color: #DD4B39; font-size: 16px;"
        )
        st.markdown('1 - Log in to your Google account:')
        st.markdown(
            f'<a href="{AUTH_HREF}" target="_blank" style="{link_style}">'
            f'<img src="https://s3-us-west-2.amazonaws.com/s.cdpn.io/14082/icon_google.png" '
            f'alt="Google" style="vertical-align: middle; margin-right: 10px;">'
            f'Login With Google</a>',
            unsafe_allow_html=True,
        )
        st.markdown('2 - Click the Button to grant API access:')
        st.button(label="Grant API access", on_click=button_callback)
        st.markdown('This is your OAuth token:')
        st.text_input("", key="my_token_input", label_visibility="collapsed")

    c1, c2 = st.columns([1.2, 4])

    with c1:

        _section_divider("Source")

        url = st.text_input(
            'Domain:',
            help='The desired domain or URL for data extraction, precisely as it appears in Google Search Console.',
        )
        property_url = check_input_url(url)
        st.session_state.domain = property_url

        _section_divider("Report type")

        metric_choice = st.selectbox(
            'Metrics:',
            list(METRICS_TO_DIMENSIONS.keys()),
            help='Specify the metric you are interested in filtering for.',
        )
        dimensions = METRICS_TO_DIMENSIONS[metric_choice]

        daily_breakdown = st.radio(
            "Daily Breakdown:",
            ("Off", "On"),
            horizontal=True,
            help='When enabled, the Table tab will show data broken down by individual days within the selected date range.',
        )

        _section_divider("Filters")

        cf1, cf2 = st.columns(2)
        with cf1:
            use_url_filter = st.checkbox(
                "Filter URL",
                help='Enable to filter results by specific URL patterns.',
            )
        with cf2:
            use_keyword_filter = st.checkbox(
                "Filter Keyword",
                help='Enable to filter results by specific keyword patterns.',
            )

        c1_1, c1_2 = st.columns(2)
        url_filter = url_operator = keyword_filter = keyword_operator = None

        if use_url_filter:
            with c1_1:
                url_filter = st.selectbox('URL', FILTER_OPTIONS)
            with c1_2:
                url_operator = st.text_input('Filter', key='URL_Operator')

        if use_keyword_filter:
            with c1_1:
                keyword_filter = st.selectbox('Keywords', FILTER_OPTIONS)
            with c1_2:
                keyword_operator = st.text_input('Filter', key='Keyword_Operator')

        _section_divider("Time range")

        day = st.date_input(
            "Period:",
            (DATE_DEFAULT, DATE_END),
            min_value=DATE_START,
            max_value=DATE_END,
            format="DD/MM/YYYY",
            help='The available time range is the same as what is available in Google Search Console. DD/MM/YYYY Format',
        )

        button = st.button('Fetch Data ✨', on_click=click_button)  # Original: "Buscar Dados ✨"

    filter_kwargs = dict(
        url_filter=url_filter, url_operator=url_operator,
        keyword_filter=keyword_filter, keyword_operator=keyword_operator,
    )
    date_range = (day[0].strftime("%Y-%m-%d"), day[1].strftime("%Y-%m-%d"))

    use_daily = daily_breakdown == "On"

    with c2:
        tab_date, tab_table = st.tabs(["📅 Date", "📃 Table"])

        with tab_date:
            if button:
                try:
                    df_date = get_data_date(property_url, *date_range, **filter_kwargs)
                    st.session_state.dataframeData = df_date
                except ValueError as e:
                    if "Please supply either code or authorization_response parameters" in str(e):
                        st.error("⚠️ Please grant API access. (If you are seeing a chart, it is a cached version)")
                    else:
                        raise

            if st.session_state.dataframeData is not None:
                try:
                    df_date = st.session_state.dataframeData
                    df_grouped = df_date.groupby('Date').agg({
                        'Clicks': 'sum',
                        'Impressions': 'sum',
                        'CTR': 'mean',
                        'Position': 'mean',
                    }).reset_index()

                    display_metric_cards(df_date)
                    with st.container():
                        plot_metrics_chart(df_grouped)
                        excel_download_button(df_grouped, key='date')
                except AttributeError:
                    pass

        with tab_table:
            if button:
                try:
                    df = get_data(property_url, dimensions, *date_range, **filter_kwargs)
                    st.session_state.dataframe = df
                    if use_daily:
                        df_daily = get_data_daily(property_url, dimensions, *date_range, **filter_kwargs)
                        st.session_state.dataframe_daily = df_daily
                except ValueError as e:
                    if "Please supply either code or authorization_response parameters" in str(e):
                        st.error("⚠️ Please grant API access. (If you are seeing a chart, it is a cached version)")
                    else:
                        raise

            active_df_key = "dataframe_daily" if use_daily and st.session_state.get("dataframe_daily") is not None else "dataframe"
            active_df = st.session_state.get(active_df_key)

            if active_df is not None:
                try:
                    filtered_df = filter_dataframe(active_df)
                    display_metric_cards(filtered_df)

                    st.dataframe(
                        filtered_df.assign(CTR=lambda x: x['CTR'].apply(lambda v: f"{v * 100:.2f}%")),
                        use_container_width=True,
                    )
                    excel_download_button(filtered_df, key='table')

                except TypeError as e:
                    if "NoneType" not in str(e):
                        raise
                except AttributeError:
                    st.error("⚠️ There's no data to be filtered, please fill in the fields on the side.")
                except ValueError as e:
                    if "Please supply either code or authorization_response parameters" in str(e):
                        st.warning("Please supply either code or authorization_response parameters")
                    else:
                        raise

    return True
