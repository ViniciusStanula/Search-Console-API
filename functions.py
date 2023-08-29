import streamlit as st
from PIL import Image

@st.cache_data(show_spinner=False)
def open_image(filename):
    return Image.open(filename)