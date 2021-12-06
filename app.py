from backend import Backend
from api_key import API_KEY
from typing import Any, List, Dict
import streamlit as st
import requests


# create backend instance
backend = Backend(API_KEY)


@st.cache(ttl=60*60*24, max_entries=10)
def extract_text(search: Any) -> List[Dict]:
        return backend.extract_text(search)

@st.cache(ttl=60*60*24, max_entries=10)
def summarize_text(text: List[str]) -> List[str]:
    return backend.summarize_text(text)

    
@st.cache(ttl=60*60*24, max_entries=10)
def text_to_speech(text: List[str]) -> List[bytes]:
    return backend.text_to_speech(text)


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
        Summarizes trending crypto news from <a href="https://www.coindesk.com/" target="_blank" target="_blank" rel="noopener noreferrer"> CoinDesk </a> and 
        gives you short yet highligted audio news based on your search. Thus busy people can always keep up-to-date with crypto news
        by listening on-the-fly or pre download it. 
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
    unsafe_allow_html=True
)
st.write("##")

with st.form(key='crypto whisperer form'):
    text = None
    speeches = []
    search = st.text_input("Enter keyword or URL :", placeholder="")
    clicked = st.form_submit_button("Whisper 🗣")
    st.write("##")
    if clicked:   
        try:
            news = extract_text(search)
            temp = [n['text'] for n in news]
            summaries = summarize_text(temp)
            temp.clear()
            temp = [f"Title: {n['title']} Date: {n['published']} Summary: {summ}" for n, summ in zip(news, summaries)]
            speeches = text_to_speech(temp)         
        except requests.exceptions.MissingSchema:
            st.error("Invalid URL! Please enter valid CoinDesk URL (etc. https://www.coindesk.com/market/...)")
        except Exception as e:
            st.error(str(e))

        # display audio players
        if speeches:
            st.write("Note: right-clicking '⋮' on audio player to download audio.")
            for i, (n, summ, speech) in enumerate(zip(news, summaries, speeches)):
                st.header(f"{i+1}.")
                st.subheader(f"{n['title']}")
                st.markdown(f"<i>published: {n['published']}</i>", unsafe_allow_html=True)
                col1, col2 = st.columns([2,2])
                with col1:
                    st.audio(speech, format="audio/wav")
                with col2, st.expander("See summary"):
                    st.write(summ)
