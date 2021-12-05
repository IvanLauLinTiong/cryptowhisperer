from logging import PlaceHolder
from modzy import ApiClient
from bs4 import BeautifulSoup
from api_key import API_KEY
import streamlit as st
import streamlit.components.v1 as st_components
import requests
import re
# import base64

# url validator
url_validator = re.compile(
                r'^(?:http)s?://' # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
                r'(?::\d+)?' # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE
)

# init Modzy API Client
client = ApiClient(base_url="https://app.modzy.com/api", api_key=API_KEY)


# @st.cache
# def extract_text(texts):
#     client.extract_text(text)

# src = f"data:audio/wav;base64,{base64.b64encode(open('audio.wav', 'rb').read()).decode()}"
# st_components.html(
#     """
#     <audio controls autoplay>
#         <source src={src} type="audio/wav">
#         Your browser does not support the audio element.
#     </audio>
#     """.format(src=src)
# )

@st.cache(ttl=60*60*24, max_entries=10)
def extract_text(url) -> str:
    # Send GET request to url given
    r = requests.get(url)
    print(r.status_code)
    if r.status_code != 200:
       r.raise_for_status()
    
    # Extracting title & text via bs4
    soup = BeautifulSoup(r.content, features='html.parser')
    headline = soup.find('div', class_='at-headline').text
    article = ''.join([p.text for p in soup.findAll('div',class_='at-text')])
    # print(f"headline: \n{headline}\n")
    # print(f"article: \n{article}")

    # Add inputs
    sources = {}
    sources["input_1"] = {
        "input.txt": article,
    }

    # submit the text summarization job
    print("running text summarization job...")
    job = client.jobs.submit_text("rs2qqwbjwb", "0.0.2", sources)
    print(f"job: {job}")
    result = client.results.block_until_complete(job, timeout=None)
    print("running text summarization job...DONE")

    # Retrieve summary
    summary = result.get_first_outputs()['results.json']['summary']

    return headline, summary


@st.cache(ttl=60*60*24, max_entries=10)
def text_to_speech(text) -> bytes:
    # Add inputs
    sources = {}
    sources["input_1"] = {
        "input.txt": text,
    }

    # submit text2speech job
    print("running text-to-speech job...")
    job = client.jobs.submit_text("uvdncymn6q", "0.0.3", sources)
    print(f"job: {job}")
    result = client.results.block_until_complete(job, timeout=None)
    print("running text-to-speech job...DONE")

    # get result .wav file from modzy server
    # add checks for th ejob status
    headers = {
        'Accept': 'application/json', 
        'Authorization': f'ApiKey {API_KEY}'
    }
    wav =  requests.get(result.get_first_outputs()['results.wav'], headers=headers)
    if wav.status_code != 200:
        wav.raise_for_status()
    return wav.content


st.set_page_config(
    page_title="Crypto Whisperer",
    page_icon="🗣",
    layout="centered",
    initial_sidebar_state="auto",
)


st.markdown(
    """
    <h1 style='text-align: center'>Crypto Whisperer</h1>
    <p>
        Summarizes trending crypto news from <a href="https://www.coindesk.com/markets/" target="_blank" target="_blank" rel="noopener noreferrer"> CoinDesk </a> and 
        gives you short yet highligted audio news based on your search. Thus busy trader can always keep up-to-date with crypto market news
        by listening to it. 
    </p>
    <br />
    <h4>Instructions:</h4>
    <p> 
        You may enter CoinDesk news URL for example: "https://www.coindesk.com/market/..." or enter crypto keyword to 
        whisper relevant Top 3 trending news.
    </p>

    <i>
        Due to backend latency, it might take ~3 min for URL and ~10 min for 
        keyword execution to complete 
    </i>
    """,
    unsafe_allow_html=True,
)
st.write("##")

with st.form(key='crypto whisperer form'):
    text = None
    speeches = []
    search = st.text_input("Enter keyword or URL :", placeholder="")
    clicked = st.form_submit_button("Whisper 🗣")
    # clicked = st.button("Whisper 🗣") 
    
    st.write("##")
    if clicked:   
        try:
            if re.match(url_validator, search):
                # extract text
                headline, summary = extract_text(search)
                summary_with_headline = f"Headline: {headline} Summary: {summary}"
                print(summary_with_headline)

                # text to speech
                speech_bytes = text_to_speech(summary_with_headline)
                speeches.append(speech_bytes)
            else:
                # keyword search
                pass
            
        except requests.exceptions.MissingSchema:
            st.error("Invalid URL! Please enter valid CoinDesk URL (etc. https://www.coindesk.com/market/...)")
        except Exception as e:
            st.exception(e)


        # display outputs
        if speeches:
            for speech in speeches:
                st.subheader(f"1. {headline}")
                col1, col2 = st.columns([2,2])
                with col1:
                    st.audio(speech, format="audio/wav")
                with col2, st.expander("See summary"):
                    st.write(summary)
            st.write("Note: right-clicking '⋮' to download audio.")
    



# //*[@id="queryly_advanced_container"]/div[4]/div[1]/div[1]/div/div/div[1]