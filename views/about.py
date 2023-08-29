import streamlit as st
import functions as fc
from streamlit_extras.badges import badge

me = fc.open_image("./assets/me.png")

def create_social_media_links():
    social_media_links = (
        "<div class='social-media-container' style='text-align: center;'>"
        "<a href='https://github.com/ViniciusStanula'><img src='https://img.icons8.com/?size=32&id=AZOZNnY73haj&format=png' alt='GitHub'></a>"
        "<a href='https://linkedin.com/in/vinicius-stanula'><img src='https://img.icons8.com/?size=32&id=qNUNvR9aEWql&format=png' alt='LinkedIn'></a>"
                "<a href='https://viniciusstanula.com'><img src='https://img.icons8.com/?size=32&id=VJz2Ob51dvZJ&format=png' alt='Instagram'></a>"
        "<a href='https://twitter.com/stanula_seo'><img src='https://img.icons8.com/?size=32&id=bUGbDbW2XLqs&format=png' alt='Twitter'></a>"
        "<a href='https://www.instagram.com/viniciusstanula/'><img src='https://img.icons8.com/?size=32&id=Xy10Jcu1L2Su&format=png' alt='Instagram'></a>"
        "</div>"
    )
    st.markdown(social_media_links, unsafe_allow_html=True)

def createPage():
    col1, col2 = st.columns(2)

    with col1:
        with st.columns(3)[1]:
            st.image(me)
            create_social_media_links()
    with col2:
        st.header('About me')
        st.markdown("Hey there, I'm Vinicius, a Python enthusiast with a side hustle of being a full-time cat aficionado. It all started when one of my furballs needed some serious medical care, and I made a vow to dive headfirst into programming to fund those gourmet cat treats. This little project you see before you is just the tip of the iceberg, a sneak peek into my grand plan of conquering the digital realm and revolutionizing SEO.")
        st.markdown("So, don't be shy, unleash those feedbacks – trust me, I've dealt with sassier critics (aka my cats).")
        badge(type="buymeacoffee", name="viniciusstanula")
    return True