import streamlit as st
import json
import re
import math
import os
from collections import Counter
from google import genai

# Page Configuration
st.set_page_config(page_title="OroWise AI - Afaan Oromoo Proverbs", page_icon="🌿", layout="centered")

st.title("🌿 OroWise Hybrid AI Engine")
st.caption("Search 3,351+ Afaan Oromoo Proverbs by Keyword or Situation for Khoobaa Dubbii")

# Load Data
@st.cache_data
def load_data():
    with open('Mammaaksa.json', 'r', encoding='utf-8') as f:
        return json.load(f)

data = load_data()

# Build TF-IDF Search Index
@st.cache_data
def build_index(data_entries):
    def tokenize(text):
import streamlit as st
import json
import re
import math
import os
from collections import Counter
from google import genai

# Page Configuration
st.set_page_config(
    page_title="OroWise AI - Afaan Oromoo Proverbs",
    page_icon="🌿",
    layout="centered"
)

st.title("🌿 OroWise Hybrid AI Engine")
st.caption("Search 3,351+ Afaan Oromoo Proverbs by Keyword or Situation for Khoobaa Dubbii")

# --- Load Data ---
@st.cache_data
def load_data():
    with open('Mammaaksa.json', 'r', encoding='utf-8') as f:
        return json.load(f)

try:
    data = load_data()
except FileNotFoundError:
    st.error("Error: Mammaaksa.json file not found in directory.")
    st.stop()

# --- Build TF-IDF Search Engine ---
@st.cache_data
def build_index(data_entries):
    def tokenize(text):
        return re.findall(r'\b\w+\b', str(text).lower()) if text else []

    documents = []
    for entry in data_entries:
        corpus = f"{entry.get('Mammaaksa_AO', '')} {entry.get('Translation_Literal_EN', '')} {entry.get('Meaning_EN', '')} {entry.get('Category_EN', '')} {entry.get('Keywords_EN', '')}"
        documents.append(tokenize(corpus))

    num_docs = len(documents)
    df_counts = Counter()
    for doc in documents:
        for word in set(doc):
            df_counts[word] += 1

    idf = {word: math.log((num_docs + 1) / (freq + 1)) + 1 for word, freq in df_counts.items()}

    doc_vectors = []
    doc_norms = []
    for doc in documents:
        tf = Counter(doc)
        doc_len = len(doc) if doc else 1
        vec = {w: (c / doc_len) * idf.get(w, 0) for w, c in tf.items()}
        norm = math.sqrt(sum(v**2 for v in vec.values())) or 1.0
        doc_vectors.append(vec)
        doc_norms.append(norm)

    return idf, doc_vectors, doc_norms, tokenize

idf, doc_vectors, doc_norms, tokenize = build_index(data)

def semantic_search(query, category_filter=None, top_n=5):
    q_tokens = tokenize(query)
    q_tf = Counter(q_tokens)
    q_len = len(q_tokens) or 1
    q_vec = {w: (c / q_len) * idf.get(w, 0) for w, c in q_tf.items()}
    q_norm = math.sqrt(sum(v**2 for v in q_vec.values())) or 1.0

    scores = []
    for i, d_vec in enumerate(doc_vectors):
        entry = data[i]
        if category_filter and category_filter != "All":
            if category_filter.lower() not in str(entry.get('Category_EN', '')).lower():
                continue
        dot = sum(d_vec.get(w, 0) * q_vec.get(w, 0) for w in q_vec)
        sim = dot / (doc_norms[i] * q_norm)
        scores.append((sim, entry))

    scores.sort(key=lambda x: x[0], reverse=True)
    return [e for s, e in scores[:top_n] if s > 0]

# --- Gemini Client Initialization ---
api_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=api_key) if api_key else None

def gemini_situation_match(situation_text, candidate_proverbs):
    candidates_formatted = ""
    for idx, p in enumerate(candidate_proverbs, 1):
        candidates_formatted += f"{idx}. [{p.get('ID')}] {p.get('Mammaaksa_AO')} - Meaning: {p.get('Meaning_EN')}\n"

    prompt = f"""
    You are an expert scholar in Oromo culture and Afaan Oromoo oral tradition for the 'Khoobaa Dubbii' platform.
    A user described the following real-life situation:
    "{situation_text}"

    Here are candidate Oromo proverbs:
    {candidates_formatted}

    Analyze the situation and explain which proverb fits best and why.
    Provide a warm, culturally resonant response with advice rooted in Oromo philosophy (Safuu).
    """
    
    response = client.models.generate_content(
        model='gemini-flash-latest',
        contents=prompt,
    )
    return response.text

# --- APP NAVIGATION TABS ---
tab1, tab2 = st.tabs(["🔍 Search by Keyword / Topic", "📖 Search by Life Situation"])

# --- TAB 1: KEYWORD SEARCH ---
with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        user_query = st.text_input("Search word or concept:", placeholder="e.g. jaalala, patience, dhugaa", key="kw_query")
    with col2:
        categories = ["All"] + sorted(list(set(str(e.get('Category_EN', '')) for e in data if e.get('Category_EN'))))
        selected_cat = st.selectbox("Category", categories, key="kw_cat")

    if user_query:
        results = semantic_search(user_query, category_filter=selected_cat, top_n=5)
        if not results:
            st.warning("No proverbs found matching your query.")
        else:
            st.subheader(f"Results for '{user_query}':")
            for idx, res in enumerate(results, 1):
                with st.container():
                    st.markdown(f"### {idx}. [{res.get('ID')}] {res.get('Mammaaksa_AO')}")
                    st.markdown(f"**Literal:** {res.get('Translation_Literal_EN')}")
                    st.markdown(f"**Meaning:** {res.get('Meaning_EN')}")
                    st.caption(f"Category: {res.get('Category_EN')}")

                    if client and st.button(f"🤖 Generate AI Insights for #{res.get('ID')}", key=f"btn_{res.get('ID')}"):
                        prompt = f"""
                        You are an expert scholar in Afaan Oromoo literature for 'Khoobaa Dubbii'.
                        Analyze this Oromo proverb:
                        Proverb: {res.get('Mammaaksa_AO')}
                        Translation: {res.get('Translation_Literal_EN')}
                        Meaning: {res.get('Meaning_EN')}
                        Category: {res.get('Category_EN')}
                        
                        Provide:
                        1. Deep Cultural Context & Philosophy (2-3 sentences)
                        2. Modern Life Application / Moral Lesson
                        3. Ready-to-Publish Social Media Caption (with relevant hashtags)
                        """
                        with st.spinner("Generating AI Analysis..."):
                            try:
                                resp = client.models.generate_content(model='gemini-flash-latest', contents=prompt)
                                st.success("Cultural Analysis Generated!")
                                st.markdown(resp.text)
                            except Exception as e:
                                st.error(f"Error: {e}")
                    st.divider()

# --- TAB 2: SITUATION / SCENARIO SEARCH ---
with tab2:
    st.subheader("Describe what is happening in your life or story:")
    situation = st.text_area(
        "Situation Description",
        placeholder="Example: Someone was offered help, but they were too arrogant to accept it and later regretted it when they failed alone.",
        height=100
    )

    if st.button("💡 Find Proverb for this Situation", type="primary"):
        if not situation.strip():
            st.warning("Please describe a situation first.")
        else:
            with st.spinner("Finding matching proverbs..."):
                candidates = semantic_search(situation, top_n=8)
                
                if not candidates:
                    st.warning("No proverb match found for this situation.")
                else:
                    st.markdown("### Top Matching Proverbs:")
                    for idx, res in enumerate(candidates[:3], 1):
                        st.markdown(f"**{idx}. [{res.get('ID')}] {res.get('Mammaaksa_AO')}**")
                        st.caption(f"Meaning: {res.get('Meaning_EN')}")
                    
                    st.divider()

                    if client:
                        with st.spinner("🤖 Gemini AI is analyzing cultural wisdom for your situation..."):
                            try:
                                match_explanation = gemini_situation_match(situation, candidates)
                                st.subheader("🤖 Khoobaa Dubbii | Situation Guidance")
                                st.markdown(match_explanation)
                            except Exception as e:
                                st.error(f"AI error: {e}")

