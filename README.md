# GOOGLE SEARCH CONSOLE API

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://search-console-api.streamlit.app/)

![GSC-API](https://github.com/ViniciusStanula/Search-Console-API/assets/48488978/77cb04de-fb46-4350-8d45-524decd2939f)
> A Streamlit web application that connects to the Google Search Console API and presents more than 200,000 rows of data in charts and tables.

### Work in Progress

This application is fully functional but still a work in progress as I plan to insert new charts and conduct further analysis. I would appreciate any feedback on this application.

## ☕ How to Use it

* Simply go to the [web application](https://search-console-api.streamlit.app/).
* Click on "Log in to Google Search Console."
* Insert your credentials.
* Click on "Grant API Access".
* Choose your metrics and click on "Get Data ✨".

Or if you prefer, clone this repository and run it locally on your machine.

## 🔧 How to run it locally and Change row Limitation

This application has a limit of 300,000 rows of data, which is significantly more than the 25,000 rows we can obtain per request using the GSC API. What this script does is run several requests, each fetching 25,000 rows, until it reaches the 300,000 limit. If your website doesn't have all the data (which is often the case), the request simply ends sooner.

If you want to retrieve more than 300,000 rows of data, follow these steps:

* Change three variables: clientSecret, clientId, and redirectUri.
* For clientSecret and clientId, you'll need to create new credentials for the Google Search Console API on Google Cloud. Ensure that you create them as OAuth client IDs for a Web Application.
* redirectUri is the URL where your app will redirect after the user logs in. If you're running the app locally, it should be something like http://localhost:8501/.
  
After completing these steps, make one more change in the code.

```
row_limit = 300000
```
### If you want to get in touch or be the first to know about my development ideas: ⤵️

<p align="left">
  <a href="https://viniciusstanula.com/en/" target="_blank" alt="Gmail">
  <img src="https://img.shields.io/badge/Website-006E93?style=flat-square&logo=wordpress&logoColor=white&link=LINK-DO-SEU-GMAIL" /></a>
  
  <a href="mailto:vinicius.stanula.seo@gmail.com" target="_blank" alt="Gmail">
  <img src="https://img.shields.io/badge/-Gmail-FF0000?style=flat-square&labelColor=FF0000&logo=gmail&logoColor=white&link=LINK-DO-SEU-GMAIL" /></a>

  <a href="https://www.linkedin.com/in/vinicius-stanula/" target="_blank" alt="LinkedIn">
  <img src="https://img.shields.io/badge/-Linkedin-0e76a8?style=flat-square&logo=Linkedin&logoColor=white&link=LINK-DO-SEU-LINKEDIN" /></a>

  <a href="https://www.instagram.com/viniciusstanula/" target="_blank" alt="Instagram">
  <img src="https://img.shields.io/badge/-Instagram-DF0174?style=flat-square&labelColor=DF0174&logo=instagram&logoColor=white&link=LINK-DO-SEU-INSTAGRAM"/></a>

  <a href="https://www.buymeacoffee.com/viniciusstanula" target="_blank" alt="Buy Me a Coffee">
    <img src="https://img.shields.io/badge/-Buy%20Me%20a%20Coffee-FF813F?style=flat-square&labelColor=FF813F&logo=buy-me-a-coffee&logoColor=white" />
  </a>
  
</p>
