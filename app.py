import streamlit as st
import pandas as pd
import requests
from transformers import pipeline, TFAutoModelForSeq2SeqLM, AutoTokenizer
from login import login_portal
from dotenv import load_dotenv
from mongo_auth import store_api, get_bookmarked_papers, bookmark_paper
import os
import time

load_dotenv()
DEFAULT_API = os.getenv("SEMANTIC_API_KEY")

def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if 'free_search' not in st.session_state:
        st.session_state.free_search = 0
    
    if 'search_history' not in st.session_state:
        st.session_state.search_history = []

    if 'username' not in st.session_state:
        st.session_state.username = ""

    if not st.session_state.logged_in:
        login_portal()
    
    else:
        display_main_app()

def display_main_app():
    # Loading the LLM 
    model_name = "facebook/bart-large-cnn"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = TFAutoModelForSeq2SeqLM.from_pretrained(model_name)
    summarizer = pipeline("summarization", model=model, tokenizer=tokenizer)

    st.title(":green[Lucid] - An AI-Powered :blue[Research Assistant]")
    st.write(f"### Welcome! {st.session_state.username}")
    st.write("This web app is designed to help you discover and summarize research papers on your topic of interest.")
    st.write(f"Enter the topic you are interested in and your Semantic Scholar API Key in the input fields on the sidebar. In case you don't have an API key, you can get it from [this link](https://www.semanticscholar.org/product/api).")
    st.write(f"Wanna give it a try before getting your API Key? You can use our default API Key for 2 free searches!")

    # Sidebar
    st.sidebar.header("Research Settings")
    search_query = st.sidebar.text_input("Search Query", "Machine Learning")

    def search_papers(query, api_key):
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&fields=title,abstract,url"
        headers = {"x-api-key": api_key}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if "data" in data:
                return data.get("data", [])
            else:
                st.error("Unexpected response format from the API.")
                st.text(data)
                return []
        else:
            st.error(f"API request failed with status code {response.status_code}")
            return []
            
    def summarize_text(text):
        summary = summarizer(text, max_length=150, min_length=30, do_sample=False)[0]["summary_text"]
        return summary
    
    def search():
        if api_key and search_query:
            # Update search history
            st.session_state.search_history.append(search_query)
            if len(st.session_state.search_history) > 5:
                st.session_state.search_history.pop(0)

            papers = search_papers(search_query, api_key)
            if papers:
                # Display search results
                st.header("Search Results")
                for paper in papers:
                    st.subheader(paper["title"])
                    st.write(paper["abstract"])
                    st.write(f"[Read more]({paper['url']})")
                    
                    if st.button(f"Summarize {paper['title']}"):
                        summary = summarize_text(paper["abstract"])
                        st.write(f"**Summary:** {summary}")
                    
                    if st.button("Bookmark", key=paper['paperId']):
                        bookmark_paper(st.session_state.username, paper['paperId'], paper['title'], paper['abstract'])
                        st.success("Paper bookmarked successfully!")

            else:
                st.error("No papers found.")
        else:
            st.warning("Please enter a valid API Key and a search query.")


    api_key_option = st.sidebar.selectbox(
        "Choose an option",
        ("Use a free search (upto 2)", "Use your own API key")
    )

    if api_key_option == "Use your own API key":
        api_key = st.sidebar.text_input("Enter your Semantic Scholar API key", type="password")
        store_api(st.session_state.username, api_key)
        
    else:
        api_key = None

    if st.sidebar.button("Search"):
        if api_key_option == "Use a free search (upto 2)":
            if st.session_state.free_search >= 2:
                st.error("You have used your 2 free searches. Please use your own API key.")

            else:
                st.session_state.free_search += 1
                api_key = DEFAULT_API

        search()
    
    # Display Search history
    st.sidebar.subheader("Search History")
    for past_query in st.session_state.search_history[::-1]:
        st.sidebar.write(past_query)
    
    # Display bookmarked papers
    if st.sidebar.button("View Bookmarked Papers"):
        st.subheader("Bookmarked Papers")
        bookmarked_papers = get_bookmarked_papers(st.session_state.username)
        for paper in bookmarked_papers:
            st.write(f"### {paper['title']}")
            st.write(paper['abstract'])
            if st.button(f"Summarize {paper['title']}", key=paper['title']):
                summary = summarize_text(paper['abstract'])
                st.write(f"**Summary**: {summary}")
            
if __name__ == '__main__':
    main()