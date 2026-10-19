import streamlit as st
import json
import re
import math
import os
import random
import urllib.parse
from datetime import date
from collections import Counter
from google import genai

# Page Configuration
st.set_page_config(
    page_title="OroWise | Khoobaa Dubbii",
    page_icon="🌿",
    layout="wide"
)

st.title("🌿 OroWise | Khoobaa Dubbii")
st.caption("Interactive Gateway to 3,351+ Afaan Oromoo Proverbs & Cultural Wisdom")

# Initialize Session State for Bookmarks/Favorites
if "saved_proverbs" not in st.session_state:
    st.session_state["saved_proverbs"] = []

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

# --- Gemini Client Initialization with Fallback ---
api_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=api_key) if api_key else None

def generate_gemini_response(prompt_text):
    models_to_try = ['gemini-2.5-flash', 'gemini-flash-latest', 'gemini-1.5-flash']
    last_error = None
    
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt_text,
            )
            if response and response.text:
                return response.text
        except Exception as e:
            last_error = e
            continue
            
    raise Exception(f"AI Service Temporarily Busy. Please retry in a moment. Details: {last_error}")

def render_proverb_card(res, idx=None):
    p_id = res.get('ID', 'N/A')
    mammaaksa = res.get('Mammaaksa_AO', '')
    literal = res.get('Translation_Literal_EN', 'N/A')
    meaning = res.get('Meaning_EN', 'N/A')
    category = res.get('Category_EN', 'General')
    keywords = res.get('Keywords_EN', 'N/A')

    # Visual Styled Container (Khoobaa Dubbii Digital Card)
    with st.container():
        st.markdown(
            f"""
            <div style="background-color: #1a1c23; border-left: 5px solid #2e7d32; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                <h3 style="color: #4caf50; margin-top: 0;">{"#" + str(idx) + ". " if idx else ""}[#{p_id}] {mammaaksa}</h3>
                <p style="color: #e0e0e0; font-size: 1.05em;"><b>Meaning:</b> {meaning}</p>
                <p style="color: #b0bec5; font-size: 0.9em;"><b>Literal:</b> {literal}</p>
                <p style="color: #81c784; font-size: 0.8em; margin-bottom: 0;">📁 Category: {category} | 🏷️ Keywords: {keywords}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Audio Pronunciation Button (Text-to-Speech HTML)
        tts_text = urllib.parse.quote(mammaaksa)
        audio_html = f"""
        <audio controls style="height: 30px; width: 250px;">
            <source src="https://translate.google.com/translate_tts?ie=UTF-8&q={tts_text}&tl=om&client=tw-ob" type="audio/mpeg">
            Your browser does not support audio elements.
        </audio>
        """
        st.components.v1.html(audio_html, height=40)

        # Action Buttons Row: Favorite, Social Share Links
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.5, 2])
        
        # Favorite / Bookmark
        is_saved = any(s.get('ID') == p_id for s in st.session_state["saved_proverbs"])
        fav_label = "❤️ Saved" if is_saved else "🤍 Save Proverb"
        if c1.button(fav_label, key=f"fav_{p_id}_{random.randint(0,10000)}"):
            if not is_saved:
                st.session_state["saved_proverbs"].append(res)
                st.toast(f"Saved proverb #{p_id} to your list!", icon="❤️")
            else:
                st.session_state["saved_proverbs"] = [s for s in st.session_state["saved_proverbs"] if s.get('ID') != p_id]
                st.toast(f"Removed proverb #{p_id}", icon="🗑️")
            st.rerun()

        # WhatsApp Share Link
        wa_text = urllib.parse.quote(f"🌿 *Khoobaa Dubbii*\n\n\"{mammaaksa}\"\n\nMeaning: {meaning}\n\nExplore more at OroWise!")
        c2.markdown(f"[💬 Share WhatsApp](https://api.whatsapp.com/send?text={wa_text})")

        # X (Twitter) Share Link
        x_text = urllib.parse.quote(f"\"{mammaaksa}\"\n\nMeaning: {meaning}\n#KhoobaaDubbii #OroWise #OromoProverbs")
        c3.markdown(f"[🐦 Share X](https://twitter.com/intent/tweet?text={x_text})")

        # Copyable Text Codeblock
        raw_share = f"\"{mammaaksa}\"\nMeaning: {meaning}\n#KhoobaaDubbii #OroWise"
        c4.code(raw_share, language="text")

        # AI Insights Button
        if client and st.button(f"🤖 Generate AI Insights for #{p_id}", key=f"btn_ai_{p_id}_{random.randint(0,10000)}"):
            prompt = f"""
            You are an expert scholar in Afaan Oromoo literature for 'Khoobaa Dubbii'.
            Analyze this Oromo proverb:
            Proverb: {mammaaksa}
            Translation: {literal}
            Meaning: {meaning}
            Category: {category}
            
            Provide:
            1. Deep Cultural Context & Philosophy (Safuu / Oromo Values)
            2. Modern Life Application / Moral Lesson
            3. Ready-to-Publish Social Media Caption (with relevant hashtags)
            """
            with st.spinner("Generating AI Analysis..."):
                try:
                    resp_text = generate_gemini_response(prompt)
                    st.success("Cultural Analysis Generated!")
                    st.markdown(resp_text)
                except Exception as e:
                    st.error(f"{e}")
        st.divider()

# --- APP NAVIGATION TABS ---
tab_names = [
    "🌟 Featured & Daily", 
    "🔍 Keyword Search", 
    "📖 Life Situation (AI)", 
    "📂 Category & Theme", 
    "🎭 By Mood", 
    "🔤 Alphabetical (A-Z)", 
    "🎲 Random Discover",
    "❤️ Saved Proverbs",
    "📊 Dataset Stats"
]
t1, t2, t3, t4, t5, t6, t7, t8, t9 = st.tabs(tab_names)

# --- TAB 1: FEATURED & PROVERB OF THE DAY ---
with t1:
    st.subheader("📅 Proverb of the Day")
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
        placeholder="Example: Nama jaalala hin beekne kan garaa isaa qofa yaadu kan bu'aa qofaaf nama jaalatu",
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
                        User Situation: "{situation}"
                        Candidate Proverbs:
                        {candidates_formatted}
                        
                        Explain which proverb best addresses this situation and provide constructive advice rooted in Oromo tradition.
                        """
                        try:
                            resp_text = generate_gemini_response(prompt)
                            st.subheader("🤖 Khoobaa Dubbii | Situation Guidance")
                            st.markdown(resp_text)
                        except Exception as e:
                            st.error(f"{e}")

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

# --- TAB 8: SAVED / FAVORITES ---
with t8:
    st.subheader("❤️ Your Saved Proverbs Collection")
    saved_list = st.session_state["saved_proverbs"]
    if not saved_list:
        st.info("You haven't saved any proverbs yet. Click '🤍 Save Proverb' on any card to add it here!")
    else:
        st.success(f"You have {len(saved_list)} saved proverb(s).")
        if st.button("🗑️ Clear All Saved"):
            st.session_state["saved_proverbs"] = []
            st.rerun()
        for idx, res in enumerate(saved_list, 1):
            render_proverb_card(res, idx)

# --- TAB 9: DATASET STATS ---
with t9:
    st.subheader("📊 OroWise Repository Analytics")
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Proverbs", f"{len(data):,}")
    categories_cnt = len(set(str(e.get('Category_EN', '')) for e in data if e.get('Category_EN')))
    m2.metric("Categories", categories_cnt)
    total_words = sum(len(tokenize(e.get('Mammaaksa_AO', ''))) for e in data)
    m3.metric("Total Words in Corpus", f"{total_words:,}")

    st.markdown("### Top Proverbs by Category")
    cat_counts = Counter(str(e.get('Category_EN', 'General')) for e in data if e.get('Category_EN'))
    for cat, count in cat_counts.most_common(8):
        st.write(f"• **{cat}**: {count} proverbs")
    
