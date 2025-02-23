import streamlit as st
import pandas as pd
import requests
from transformers import pipeline, TFAutoModelForSeq2SeqLM, AutoTokenizer
from login import login_portal
from dotenv import load_dotenv
from mongo_auth import store_api, get_bookmarked_papers, bookmark_paper, add_search_history, get_search_history, get_free_search, increment_free_search
import os
import time

DEFAULT_API = st.secrets.SEMANTIC_API_KEY

def main():
    # Session state management
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if 'username' not in st.session_state:
        st.session_state.username = ""
    
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []

    if 'summarize_click' not in st.session_state:
        st.session_state.summarize_click = None
    
    if 'bookmark_click' not in st.session_state:
        st.session_state.bookmark_click = None
    
    # Login portal
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

    st.set_page_config(page_title='Lucid - AI Research Assistant')

    st.title(":green[Lucid] - An AI-Powered :blue[Research Assistant]")
    st.write(f"### Welcome! :orange[{st.session_state.username}]")
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
        summary = summarizer(text, max_length=60, min_length=30, do_sample=False)[0]["summary_text"]
        return summary
    
    def search():
        if api_key and search_query:
            # Update search history
            add_search_history(st.session_state.username, search_query)

            papers = search_papers(search_query, api_key)
            if papers:
                st.session_state.search_results = papers  # Store search results in session state
                st.session_state.summarize_click = None
                st.session_state.bookmark_click = None

                # Display search results
                # st.header("Search Results")
                # for paper in papers:
                #     st.subheader(paper["title"])
                #     st.write(paper["abstract"])
                #     st.write(f"[Read more]({paper['url']})")
                    
                #     if st.button(f"Summarize {paper['title']}"):
                #         summary = summarize_text(paper["abstract"])
                #         st.write(f"**Summary:** {summary}")
                    
                #     if st.button("Bookmark", key=paper['paperId']):
                #         bookmark_paper(st.session_state.username, paper['paperId'], paper['title'], paper['abstract'])
                #         st.success("Paper bookmarked successfully!")

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
            if get_free_search(st.session_state.username) >= 2:
                st.error("You have used your 2 free searches. Please use your own API key.")

            else:
                increment_free_search(st.session_state.username)
                api_key = DEFAULT_API

        search()
    
    if st.session_state.search_results:
        for i, paper in enumerate(st.session_state.search_results):
            st.write(f"### {paper['title']}")
            st.write(paper['abstract'])
            if st.button(f"Summarize {paper['title']}", key=f"summarize_{i}"):
                st.session_state.summarize_click = i
                # st.rerun()
            if st.button(f"Bookmark {paper['title']}", key=f"bookmark_{i}"):
                st.session_state.bookmark_click = i
                # st.rerun()

    # Handle button clicks
    if st.session_state.summarize_click is not None:
        paper = st.session_state.search_results[st.session_state.summarize_click]
        summary = summarize_text(paper['abstract'])
        st.write(f"**Summary of {paper['title']}**: {summary}")
        st.session_state.summarize_click = None

    if st.session_state.bookmark_click is not None:
        paper = st.session_state.search_results[st.session_state.bookmark_click]
        bookmark_paper(st.session_state.username, paper['paperId'], paper['title'], paper['abstract'])
        st.success("Paper bookmarked successfully!")
        st.session_state.bookmark_click = None

    # Display Search history
    st.sidebar.subheader("Search History")
    for past_query in get_search_history(st.session_state.username)[::-1]:
        st.sidebar.write(f"{past_query['query']} :grey[at {past_query['timestamp'].time().hour}:{past_query['timestamp'].time().minute}, {past_query['timestamp'].date()}]")
    
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