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
    page_title="OroWise AI",
    page_icon="🌿",
    layout="wide"
)

# Header Branding
st.title("🌿 OroWise AI Engine")

# Language Switcher
lang_choice = st.sidebar.radio("🌐 Afaan Filadhu / Choose Language:", ["Afaan Oromoo", "English"])
is_ao = (lang_choice == "Afaan Oromoo")

if is_ao:
    st.caption("Wiirtuu Mammaaksa Oromoo 3,351+ fi Ogummaa Aadaa Oromoo Interactive AI'n Deeggarame")
else:
    st.caption("Interactive Gateway to 3,351+ Afaan Oromoo Proverbs & Cultural Wisdom")

# Initialize Session State
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

    lbl_meaning = "Hiika:" if is_ao else "Meaning:"
    lbl_literal = "Jechaan:" if is_ao else "Literal:"
    lbl_cat = "Kutaalee:" if is_ao else "Category:"
    lbl_key = "Jechoota Ijoo:" if is_ao else "Keywords:"

    with st.container():
        card_html = (
            "<div style='background-color: #1a1c23; border-left: 5px solid #2e7d32; padding: 15px; border-radius: 8px; margin-bottom: 10px;'>"
            + "<h3 style='color: #4caf50; margin-top: 0;'>" + ("#" + str(idx) + ". " if idx else "") + "[#" + str(p_id) + "] " + mammaaksa + "</h3>"
            + "<p style='color: #e0e0e0; font-size: 1.05em;'><b>" + lbl_meaning + "</b> " + meaning + "</p>"
            + "<p style='color: #b0bec5; font-size: 0.9em;'><b>" + lbl_literal + "</b> " + literal + "</p>"
            + "<p style='color: #81c784; font-size: 0.8em; margin-bottom: 0;'>📁 " + lbl_cat + " " + category + " | 🏷️ " + lbl_key + " " + keywords + "</p>"
            + "</div>"
        )
        st.markdown(card_html, unsafe_allow_html=True)

        safe_speech_text = re.sub(r'["\'\\]', '', mammaaksa)
        btn_listen_lbl = "🔊 Sagalee Dhagahi" if is_ao else "🔊 Listen Audio"
        audio_js_html = (
            "<button onclick='speakText()' style='background-color: #2e7d32; color: white; border: none; padding: 6px 14px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 0.9em;'>"
            + btn_listen_lbl
            + "</button>"
            + "<script>"
            + "function speakText() {"
            + "    if ('speechSynthesis' in window) {"
            + "        window.speechSynthesis.cancel();"
            + "        var msg = new SpeechSynthesisUtterance('" + safe_speech_text + "');"
            + "        msg.rate = 0.85;"
            + "        msg.pitch = 1.0;"
            + "        msg.lang = 'om-ET';"
            + "        window.speechSynthesis.speak(msg);"
            + "    } else {"
            + "        alert('Text-to-speech is not supported on this browser.');"
            + "    }"
            + "}"
            + "</script>"
        )
        st.components.v1.html(audio_js_html, height=45)

        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.5, 2])
        
        is_saved = any(s.get('ID') == p_id for s in st.session_state["saved_proverbs"])
        if is_ao:
            fav_label = "❤️ Olkaawwameera" if is_saved else "🤍 Olkaawwadhu"
        else:
            fav_label = "❤️ Saved" if is_saved else "🤍 Save Proverb"

        if c1.button(fav_label, key=f"fav_{p_id}_{random.randint(0,10000)}"):
            if not is_saved:
                st.session_state["saved_proverbs"].append(res)
                st.toast(f"Saved proverb #{p_id}", icon="❤️")
            else:
                st.session_state["saved_proverbs"] = [s for s in st.session_state["saved_proverbs"] if s.get('ID') != p_id]
                st.toast(f"Removed proverb #{p_id}", icon="🗑️")
            st.rerun()

        wa_text = urllib.parse.quote(f"🌿 *OroWise AI*\n\n\"{mammaaksa}\"\n\nMeaning: {meaning}\n\nExplore more at OroWise!")
        c2.markdown(f"[💬 Share WhatsApp](https://api.whatsapp.com/send?text={wa_text})")

        x_text = urllib.parse.quote(f"\"{mammaaksa}\"\n\nMeaning: {meaning}\n#OroWise #OromoProverbs")
        c3.markdown(f"[🐦 Share X](https://twitter.com/intent/tweet?text={x_text})")

        raw_share = f"\"{mammaaksa}\"\nMeaning: {meaning}\n#OroWise"
        c4.code(raw_share, language="text")

        btn_ai_lbl = f"🤖 Xiinxala AI #{p_id}" if is_ao else f"🤖 Generate AI Insights for #{p_id}"
        if client and st.button(btn_ai_lbl, key=f"btn_ai_{p_id}_{random.randint(0,10000)}"):
            lang_prompt_instruction = "Respond in Afaan Oromoo with rich cultural terminology." if is_ao else "Respond in English with Oromo cultural terms."
            prompt = f"You are an expert scholar in Afaan Oromoo literature for the 'OroWise' platform. Analyze this Oromo proverb:\nProverb: {mammaaksa}\nTranslation: {literal}\nMeaning: {meaning}\nCategory: {category}\n\nProvide:\n1. Deep Cultural Context & Philosophy (Safuu / Oromo Values)\n2. Modern Life Application / Moral Lesson\n3. Ready-to-Publish Social Media Caption (with relevant hashtags)\n\nInstruction: {lang_prompt_instruction}"
            with st.spinner("Analyzing..." if not is_ao else "Xiinxalamaa jira..."):
                try:
                    resp_text = generate_gemini_response(prompt)
                    st.success("Cultural Analysis Generated!" if not is_ao else "Xiinxalli Aadaa Qophaa'eera!")
                    st.markdown(resp_text)
                except Exception as e:
                    st.error(f"{e}")
        st.divider()

# --- APP NAVIGATION TABS ---
if is_ao:
    tab_names = [
        "🏠 Simanna",
        "🌟 Guyyaa & Filatamaa", 
        "🔍 Barbaacha Jechaa", 
        "📖 Haala Jireenyaa (AI)", 
        "📂 Kutaalee & Dhimma", 
        "🎭 Akka Miiraa & Annisaa", 
        "🔤 Quubee (A-Z)", 
        "🎲 Carraan Barbaadi",
        "❤️ Mammaaksa Olka'an",
        "📊 Sakatta'a Dataa",
        "ℹ️ Waa'ee Keenya",
        "📩 Nu Quunnamaa"
    ]
else:
    tab_names = [
        "🏠 Welcome",
        "🌟 Featured & Daily", 
        "🔍 Keyword Search", 
        "📖 Life Situation (AI)", 
        "📂 Category & Theme", 
        "🎭 By Mood & Energy", 
        "🔤 Alphabetical (A-Z)", 
        "🎲 Random Discover",
        "❤️ Saved Proverbs",
        "📊 Dataset Stats",
        "ℹ️ About Us",
        "📩 Contact"
    ]

t0, t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11 = st.tabs(tab_names)

# --- TAB 0: WELCOME LANDING PAGE ---
with t0:
    if is_ao:
        st.subheader("🌿 Baga Gara OroWise AI Dhuftan")
        st.write("Akkam! Baga gara wiirtuu mammaaksa fi ogummaa aadaa Oromoo dhuftan.")
        st.write("OroWise mammaaksa Afaan Oromoo **3,351+** teeknoolojii AI faana walitti fiduun isiif dhiyeessa.")
        st.divider()
        st.markdown("### 🚀 Akkamitti Barbaaduu Dandeessu:")
        st.write("• **🔍 Barbaacha Jechaa:** Jechoota Afaan Oromoo fi Ingiliffaan mammaaksa barbaadaa (*jaalala, dhugaa, dhaabbata*).")
        st.write("• **📖 Haala Jireenyaa (AI):** Haala jireenyaa keessan ibsaatii mammaaksa isaan deeggaru fi gorsa AI Safuu Oromoo irratti hundaa'e argadhaa.")
        st.write("• **🎭 Akka Miiraa:** Filannoowwan miiraa **25+** gubbaa filachuun mammaaksa itti dhihaatu argadhaa.")
        st.write("• **🔊 Sagalee Dhagahi:** Sagalee dubbisa mammaaksa sana dhageeffadhaa.")
        st.write("• **📱 Cuqasa Tokkoon Qooda:** Mammaaksa filattan WhatsApp fi X (Twitter) irratti qooddadhaa.")
        st.write("• **❤️ Mammaaksa Olkaawwadhaa:** Mammaaksa jaallattan boodaaf olkaawwachuu dandeessu.")
        st.caption("Nagaa fi Rahmata! Ogummaa dhalootaa dhalootti dabre kana keessatti bashannanaa.")
    else:
        st.subheader("🌿 Welcome to OroWise AI")
        st.write("Akkaam! Welcome to the digital repository of Oromo cultural philosophy.")
        st.write("OroWise brings over **3,351+ Afaan Oromoo proverbs (mammaaksa)** into an interactive, AI-enhanced platform.")
        st.divider()
        st.markdown("### 🚀 How to Explore:")
        st.write("• **🔍 Keyword Search:** Find proverbs instantly by typing Oromo or English words (*jaalala, patience, dhugaa*).")
        st.write("• **📖 Life Situation (AI):** Describe a real-world story or conflict to get matching proverbs paired with AI guidance rooted in *Safuu*.")
        st.write("• **🎭 By Mood & Energy:** Choose from over **25+ emotional tones** to match your current feeling or topic.")
        st.write("• **🔊 Audio Speech:** Listen to text-to-speech pronunciation of any proverb.")
        st.write("• **📱 One-Click Social Sharing:** Copy formatted text or share directly to WhatsApp and X (Twitter).")
        st.write("• **❤️ Bookmarks:** Save your favorite proverbs for future reference.")
        st.caption("Nagaa fi Rahmata! Explore wisdom preserved across generations.")

# --- TAB 1: FEATURED & PROVERB OF THE DAY ---
with t1:
    st.subheader("📅 Mammaaksa Guyyaa" if is_ao else "📅 Proverb of the Day")
    day_seed = date.today().timetuple().tm_yday
    daily_entry = data[day_seed % len(data)]
    render_proverb_card(daily_entry)

    st.subheader("✨ Mammaaksa Filatamaa" if is_ao else "✨ Featured Proverbs")
    featured_indices = [10, 42, 108, 250, 500, 1000]
    for fid in featured_indices:
        if fid < len(data):
            render_proverb_card(data[fid])

# --- TAB 2: KEYWORD SEARCH ---
with t2:
    col1, col2 = st.columns([3, 1])
    with col1:
        user_query = st.text_input("Jecha barbaaddan barreessaa:" if is_ao else "Search term or concept:", placeholder="e.g. jaalala, patience, dhugaa", key="kw_query")
    with col2:
        cats = ["All"] + sorted(list(set(str(e.get('Category_EN', '')) for e in data if e.get('Category_EN'))))
        selected_cat = st.selectbox("Gosa / Category", cats, key="kw_cat")

    if user_query:
        results = semantic_search(user_query, category_filter=selected_cat, top_n=10)
        if not results:
            st.warning("Mammaaksi barbaaddan hinargamne." if is_ao else "No matching proverbs found.")
        else:
            st.subheader(f"Bu'aa Barbaacha '{user_query}':" if is_ao else f"Search Results for '{user_query}':")
            for idx, res in enumerate(results, 1):
                render_proverb_card(res, idx)

# --- TAB 3: LIFE SITUATION (AI) ---
with t3:
    st.subheader("Haala jireenyaa keessan ibsaa:" if is_ao else "Describe a scenario or life situation:")
    situation = st.text_area(
        "Ibsa Haala Jireenyaa" if is_ao else "Situation Context",
        placeholder="Fakkeenya: Nama jaalala hin beekne kan garaa isaa qofa yaadu kan bu'aa qofaaf nama jaalatu",
        height=100
    )

    btn_find_lbl = "💡 Mammaaksa fi Gorsa AI Barbaadi" if is_ao else "💡 Find Proverb & AI Guidance"
    if st.button(btn_find_lbl, type="primary"):
        if not situation.strip():
            st.warning("Mee dura haala sana gabaabsitee ibsi." if is_ao else "Please describe a situation first.")
        else:
            candidates = semantic_search(situation, top_n=5)
            if candidates:
                st.markdown("### Mammaaksa Isaan Deeggaru:" if is_ao else "### Top Recommended Proverbs:")
                for idx, res in enumerate(candidates[:3], 1):
                    st.markdown(f"**{idx}. [{res.get('ID')}] {res.get('Mammaaksa_AO')}**")
                    st.caption(f"Meaning: {res.get('Meaning_EN')}")
                st.divider()

                if client:
                    with st.spinner("🤖 Gemini AI xiinxalaa jira..." if is_ao else "🤖 Gemini AI is evaluating cultural guidance..."):
                        candidates_formatted = "\n".join([f"{p.get('ID')}: {p.get('Mammaaksa_AO')} - {p.get('Meaning_EN')}" for p in candidates])
                        prompt_lang = "Respond in Afaan Oromoo." if is_ao else "Respond in English."
                        prompt = f"You are an expert scholar in Oromo philosophy and Safuu for the 'OroWise' platform. User Situation: '{situation}'\nCandidate Proverbs:\n{candidates_formatted}\n\nExplain which proverb best addresses this situation and provide constructive advice rooted in Oromo tradition. {prompt_lang}"
                        try:
                            resp_text = generate_gemini_response(prompt)
                            st.subheader("🤖 OroWise | Gorsa AI" if is_ao else "🤖 OroWise | Situation Guidance")
                            st.markdown(resp_text)
                        except Exception as e:
                            st.error(f"{e}")

# --- TAB 4: CATEGORY & THEME ---
with t4:
    st.subheader("Kutaalee fi Dhimmaan Barbaadaa" if is_ao else "Explore by Category or Theme")
    categories = sorted(list(set(str(e.get('Category_EN', 'General')) for e in data if e.get('Category_EN'))))
    chosen_cat = st.selectbox("Kutaa Filadhaa" if is_ao else "Select Category / Theme", categories)
    
    cat_matches = [e for e in data if str(e.get('Category_EN', '')).lower() == chosen_cat.lower()]
    st.info(f"Mammaaksa {len(cat_matches)} kutaa **{chosen_cat}** keessatti argaman:" if is_ao else f"Found {len(cat_matches)} proverbs in **{chosen_cat}**")
    
    for idx, res in enumerate(cat_matches[:15], 1):
        render_proverb_card(res, idx)

# --- TAB 5: BY MOOD & ENERGY ---
with t5:
    st.subheader("Miira akkamii keessa jirtu?" if is_ao else "How are you feeling or what energy are you seeking?")
    mood_keywords = {
        "💪 Jabina fi Onnee / Strength & Hope": "strength courage hope perseverance resilience endure brave power",
        "⚖️ Ogummaa fi Of-eeggannoo / Wisdom & Caution": "wisdom warning caution secret truth careful secret discretion",
        "🤝 Tokkummaa fi Jaalala / Unity & Friendship": "community unity friend help together alliance trust harmony",
        "🌾 Obsa fi Yeroo / Patience & Time": "patience work time harvest growth delay perseverance wait season",
        "⚖️ Dhugaa fi Safuu / Justice & Integrity": "justice truth honor honesty safuu dignity right law moral",
        "🙏 Galateeffannaa fi Nagaa / Peace & Blessing": "blessing thank peace fortune good destiny life grace calm",
        "👑 Hayyummaa fi Hoogganummaa / Leadership & Gadaa": "lead responsibility guide elder head decision power governance chief",
        "🏡 Maatii fi Warra / Family & Kinship": "family mother father child relatives blood home marriage parent lineage",
        "🕊️ Araara fi Nageenya / Reconciliation": "reconciliation peace argument anger calm mercy forgiveness truce",
        "🌾 Hojii fi Cira / Labor & Work": "farming work effort harvest sweat labor energy produce struggle",
        "😏 Qoosaa fi Kolfa / Humor & Satire": "foolish irony trick joke vanity pride lesson sarcasm play",
        "🌅 Haaromsa fi Abdii / Renewal & Hope": "morning new begin future sunrise transformation change opportunity",
        "🤲 Kabaja fi Safuu / Respect & Humility": "humility modest respect honor elders bow gentle quiet safuu"
    }
    
    chosen_mood = st.selectbox("Miira Filadhaa / Choose Mood", list(mood_keywords.keys()))
    
    if chosen_mood:
        keyword = mood_keywords[chosen_mood]
        results = semantic_search(keyword, top_n=10)
        st.info(f"Mammaaksa miira **{chosen_mood}** deeggaran:" if is_ao else f"Displaying proverbs matching the energy of **{chosen_mood}**:")
        for idx, res in enumerate(results, 1):
            render_proverb_card(res, idx)

# --- TAB 6: ALPHABETICAL (A-Z) ---
with t6:
    st.subheader("Akka Quubeetiin Barbaadaa (Afaan Oromoo)" if is_ao else "Browse Alphabetically (Afaan Oromoo)")
    letters = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "Y", "Z"]
    selected_letter = st.selectbox("Qubee Jalqabaa Filadhaa" if is_ao else "Select Starting Letter", letters)
    
    alpha_matches = [e for e in data if str(e.get('Mammaaksa_AO', '')).strip().upper().startswith(selected_letter)]
    st.info(f"Mammaaksa {len(alpha_matches)} qubee **'{selected_letter}'**n jalqaban:" if is_ao else f"Found {len(alpha_matches)} proverbs starting with **'{selected_letter}'**")
    
    for idx, res in enumerate(alpha_matches[:20], 1):
        render_proverb_card(res, idx)

# --- TAB 7: RANDOM DISCOVER ---
with t7:
    st.subheader("🎲 Mammaaksa Carraan Barbaaduu" if is_ao else "🎲 Random Wisdom Generator")
    btn_rand_lbl = "🔀 Mammaaksa Haaraa Agarsiisi" if is_ao else "🔀 Show New Random Proverbs"
    if st.button(btn_rand_lbl, type="primary"):
        st.session_state["random_samples"] = random.sample(data, min(5, len(data)))
    
    if "random_samples" not in st.session_state:
        st.session_state["random_samples"] = rando
