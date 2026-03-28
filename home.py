import streamlit as st
from views import gsc_api
from PIL import Image

favicon = Image.open("./assets/favicon.png")

st.set_page_config(
    page_title="Google Search Console Python API",
    page_icon=favicon,
    layout="wide",
    initial_sidebar_state='collapsed',
)

st.markdown('<style>' + open('./style.css').read() + '</style>', unsafe_allow_html=True)
 
gsc_api.createPage()
