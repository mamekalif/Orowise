import streamlit as st
import json
import re
import math
import os
import random
from datetime import date
from collections import Counter
from google import genai

# Page Configuration
st.set_page_config(
    page_title="OroWise AI - Khoobaa Dubbii",
    page_icon="🌿",
    layout="wide"
)

st.title("🌿 OroWise | Khoobaa Dubbii")
st.caption("Interactive Gateway to 3,351+ Afaan Oromoo Proverbs & Cultural Wisdom")

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

# --- Tokenizer Helper Function ---
def tokenize(text):
    return re.findall(r'\b\w+\b', str(text).lower()) if text else []

# --- Build TF-IDF Search Engine ---
@st.cache_data
def build_index(data_entries):
    documents = [
        tokenize(
            f"{entry.get('Mammaaksa_AO', '')} "
            f"{entry.get('Translation_Literal_EN', '')} "
            f"{entry.get('Meaning_EN', '')} "
            f"{entry.get('Category_EN', '')} "
            f"{entry.get('Keywords_EN', '')}"
        )
        for entry in data_entries
    ]

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

    return idf, doc_vectors, doc_norms

idf, doc_vectors, doc_norms = build_index(data)

def semantic_search(query, category_filter=None, top_n=10):
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

def render_proverb_card(res, idx=None):
    title_prefix = f"{idx}. " if idx else ""
    st.markdown(f"### {title_prefix}[#{res.get('ID', 'N/A')}] {res.get('Mammaaksa_AO', '')}")
    st.markdown(f"**Literal Translation:** {res.get('Translation_Literal_EN', 'N/A')}")
    st.markdown(f"**Meaning:** {res.get('Meaning_EN', 'N/A')}")
    st.caption(f"📁 Category: {res.get('Category_EN', 'General')} | 🏷️ Keywords: {res.get('Keywords_EN', 'N/A')}")
    
    # Khoobaa Dubbii Social Share Formatting
    share_text = f"\"{res.get('Mammaaksa_AO')}\"\n\nMeaning: {res.get('Meaning_EN')}\n\n#KhoobaaDubbii #OroWise #OromoProverbs"
    st.code(share_text, language="text")

    if client and st.button(f"🤖 Generate AI Insights for #{res.get('ID')}", key=f"btn_ai_{res.get('ID')}_{random.randint(0,10000)}"):
        prompt = f"""
        You are an expert scholar in Afaan Oromoo literature for 'Khoobaa Dubbii'.
        Analyze this Oromo proverb:
        Proverb: {res.get('Mammaaksa_AO')}
        Translation: {res.get('Translation_Literal_EN')}
        Meaning: {res.get('Meaning_EN')}
        Category: {res.get('Category_EN')}
        
        Provide:
        1. Deep Cultural Context & Philosophy (Safuu / Oromo Values)
        2. Modern Life Application / Moral Lesson
        3. Ready-to-Publish Social Media Caption (with relevant hashtags)
        """
        with st.spinner("Generating AI Analysis..."):
            try:
                resp = client.models.generate_content(model='gemini-flash-latest', contents=prompt)
                st.success("Cultural Analysis Generated!")
                st.markdown(resp.text)
            except Exception as e:
                st.error(f"AI Error: {e}")
    st.divider()

# --- APP NAVIGATION ---
tab_names = [
    "🌟 Featured & Daily", 
    "🔍 Keyword Search", 
    "📖 Life Situation (AI)", 
    "📂 By Category & Theme", 
    "🎭 By Mood", 
    "🔤 Alphabetical (A-Z)", 
    "🎲 Random Discover"
]
t1, t2, t3, t4, t5, t6, t7 = st.tabs(tab_names)

# --- TAB 1: FEATURED & PROVERB OF THE DAY ---
with t1:
    st.subheader("📅 Proverb of the Day")
    # Use day of year as seed for a stable daily proverb
    day_seed = date.today().timetuple().tm_yday
    daily_entry = data[day_seed % len(data)]
    render_proverb_card(daily_entry)

    st.subheader("✨ Featured Proverbs")
    featured_indices = [10, 42, 108, 250, 500, 1000]
    for fid in featured_indices:
        if fid < len(data):
            render_proverb_card(data[fid])

# --- TAB 2: KEYWORD SEARCH ---
with t2:
    col1, col2 = st.columns([3, 1])
    with col1:
        user_query = st.text_input("Search term or concept:", placeholder="e.g. jaalala, patience, dhugaa", key="kw_query")
    with col2:
        cats = ["All"] + sorted(list(set(str(e.get('Category_EN', '')) for e in data if e.get('Category_EN'))))
        selected_cat = st.selectbox("Category Filter", cats, key="kw_cat")

    if user_query:
        results = semantic_search(user_query, category_filter=selected_cat, top_n=10)
        if not results:
            st.warning("No matching proverbs found.")
        else:
            st.subheader(f"Search Results for '{user_query}':")
            for idx, res in enumerate(results, 1):
                render_proverb_card(res, idx)

# --- TAB 3: LIFE SITUATION (AI) ---
with t3:
    st.subheader("Describe a scenario or life situation:")
    situation = st.text_area(
        "Situation Context",
        placeholder="Example: Someone refused advice from elders, thinking they knew better, but encountered failure.",
        height=100
    )

    if st.button("💡 Find Proverb & AI Guidance", type="primary"):
        if not situation.strip():
            st.warning("Please describe a situation first.")
        else:
            candidates = semantic_search(situation, top_n=5)
            if candidates:
                st.markdown("### Top Recommended Proverbs:")
                for idx, res in enumerate(candidates[:3], 1):
                    st.markdown(f"**{idx}. [{res.get('ID')}] {res.get('Mammaaksa_AO')}**")
                    st.caption(f"Meaning: {res.get('Meaning_EN')}")
                st.divider()

                if client:
                    with st.spinner("🤖 Gemini AI is evaluating cultural guidance..."):
                        candidates_formatted = "\n".join([f"{p.get('ID')}: {p.get('Mammaaksa_AO')} - {p.get('Meaning_EN')}" for p in candidates])
                        prompt = f"""
                        You are an expert scholar in Oromo philosophy and Safuu for 'Khoobaa Dubbii'.
                        Situation: "{situation}"
                        Candidate Proverbs:
                        {candidates_formatted}
                        
                        Explain which proverb best addresses this situation and provide constructive advice rooted in Oromo tradition.
                        """
                        try:
                            resp = client.models.generate_content(model='gemini-flash-latest', contents=prompt)
                            st.subheader("🤖 Khoobaa Dubbii | Situation Guidance")
                            st.markdown(resp.text)
                        except Exception as e:
                            st.error(f"AI Error: {e}")

# --- TAB 4: CATEGORY & THEME ---
with t4:
    st.subheader("Explore by Category or Theme")
    categories = sorted(list(set(str(e.get('Category_EN', 'General')) for e in data if e.get('Category_EN'))))
    chosen_cat = st.selectbox("Select Category / Theme", categories)
    
    cat_matches = [e for e in data if str(e.get('Category_EN', '')).lower() == chosen_cat.lower()]
    st.info(f"Found {len(cat_matches)} proverbs in **{chosen_cat}**")
    
    for idx, res in enumerate(cat_matches[:15], 1):
        render_proverb_card(res, idx)

# --- TAB 5: BY MOOD ---
with t5:
    st.subheader("How are you feeling or what energy are you seeking?")
    mood_keywords = {
        "💪 Encouragement & Strength": "strength courage hope perseverance",
        "⚖️ Wisdom & Caution": "wisdom warning caution secret truth",
        "🤝 Unity & Friendship": "community unity friend help together",
        "🌾 Patience & Growth": "patience work time harvest growth",
        "⚖️ Justice & Integrity": "justice truth honor honesty safuu"
    }
    chosen_mood = st.radio("Choose Mood/Tone", list(mood_keywords.keys()), horizontal=True)
    
    if chosen_mood:
        keyword = mood_keywords[chosen_mood]
        results = semantic_search(keyword, top_n=8)
        for idx, res in enumerate(results, 1):
            render_proverb_card(res, idx)

# --- TAB 6: ALPHABETICAL (A-Z) ---
with t6:
    st.subheader("Browse Alphabetically (Afaan Oromoo)")
    letters = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "Y", "Z"]
    selected_letter = st.selectbox("Select Starting Letter", letters)
    
    alpha_matches = [e for e in data if str(e.get('Mammaaksa_AO', '')).strip().upper().startswith(selected_letter)]
    st.info(f"Found {len(alpha_matches)} proverbs starting with **'{selected_letter}'**")
    
    for idx, res in enumerate(alpha_matches[:20], 1):
        render_proverb_card(res, idx)

# --- TAB 7: RANDOM DISCOVER ---
with t7:
    st.subheader("🎲 Random Wisdom Generator")
    if st.button("🔀 Show New Random Proverbs", type="primary"):
        st.session_state["random_samples"] = random.sample(data, min(5, len(data)))
    
    if "random_samples" not in st.session_state:
        st.session_state["random_samples"] = random.sample(data, min(5, len(data)))
        
    for idx, res in enumerate(st.session_state["random_samples"], 1):
        render_proverb_card(res, idx)
                        
