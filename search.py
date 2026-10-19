import json
import re
import math
import os
from collections import Counter
from dotenv import load_dotenv

# Automatically load environment variables from .env file
load_dotenv()

# Gemini API Client Integration
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

DATA_FILE = 'Mammaaksa.json'

try:
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"✅ Loaded {len(data)} proverbs into OroWise AI Engine!")
except FileNotFoundError:
    print(f"❌ Error: Could not find {DATA_FILE} in current directory.")
    exit(1)

# Initialize Gemini Client if key exists in .env
client = None
api_key = os.environ.get("GEMINI_API_KEY")
if GEMINI_AVAILABLE and api_key:
    client = genai.Client(api_key=api_key)
    print("🤖 Gemini AI Assistant connected from .env!")
else:
    print("ℹ️ Gemini API key not found in .env. (Search runs offline; set GEMINI_API_KEY in .env for AI insights).")

def tokenize(text):
    if not text:
        return []
    return re.findall(r'\b\w+\b', str(text).lower())

# Build Sparse Vector Index (TF-IDF weighted)
documents = []
for entry in data:
    corpus_text = (
        f"{entry.get('Mammaaksa_AO', '')} "
        f"{entry.get('Translation_Literal_EN', '')} "
        f"{entry.get('Meaning_EN', '')} "
        f"{entry.get('Category_EN', '')} "
        f"{entry.get('Keywords_EN', '')}"
    )
    documents.append(tokenize(corpus_text))

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
    vec = {}
    norm_sq = 0
    for word, count in tf.items():
        score = (count / doc_len) * idf.get(word, 0)
        vec[word] = score
        norm_sq += score ** 2
    doc_vectors.append(vec)
    doc_norms.append(math.sqrt(norm_sq) if norm_sq > 0 else 1.0)

def semantic_search(query, category_filter=None, top_n=3):
    q_tokens = tokenize(query)
    q_tf = Counter(q_tokens)
    q_len = len(q_tokens) if q_tokens else 1
    
    q_vec = {}
    q_norm_sq = 0
    for word, count in q_tf.items():
        score = (count / q_len) * idf.get(word, 0)
        q_vec[word] = score
        q_norm_sq += score ** 2
    q_norm = math.sqrt(q_norm_sq) if q_norm_sq > 0 else 1.0

    scores = []
    for i, d_vec in enumerate(doc_vectors):
        entry = data[i]
        if category_filter:
            cat_text = str(entry.get('Category_EN', '')).lower()
            if category_filter.lower() not in cat_text:
                continue

        dot_product = sum(d_vec.get(w, 0) * q_vec.get(w, 0) for w in q_vec)
        similarity = dot_product / (doc_norms[i] * q_norm)
        scores.append((similarity, i))

    scores.sort(key=lambda x: x[0], reverse=True)
    return [dict(data[idx], _score=round(score, 3)) for score, idx in scores[:top_n]]

# --- Gemini AI Cultural & Media Generator (Using permanent alias) ---
def ask_gemini_cultural_analysis(proverb_entry):
    if not client:
        print("⚠️ Gemini Client not active. Check GEMINI_API_KEY inside .env.")
        return

    prompt = f"""
    You are an expert scholar in Afaan Oromoo literature and oral traditions for the "Khoobaa Dubbii" media platform.
    Analyze the following Oromo proverb:
    
    Proverb (AO): {proverb_entry.get('Mammaaksa_AO')}
    Literal English: {proverb_entry.get('Translation_Literal_EN')}
    Meaning: {proverb_entry.get('Meaning_EN')}
    Category: {proverb_entry.get('Category_EN')}
    
    Provide:
    1. Deep Cultural Context & Philosophy (2-3 sentences)
    2. Modern Life Application / Moral Lesson
    3. Ready-to-Publish Social Media Caption (with relevant hashtags)
    """

    print("\n⏳ Generating AI Cultural Insights with Gemini...")
    try:
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt,
        )
        print("\n" + "="*50)
        print("🤖 KHOOBAA DUBBII | AI CULTURAL INSIGHT")
        print("="*50)
        print(response.text)
        print("="*50 + "\n")

        save = input("Save AI insight to 'orowise_ai_cards.txt'? (y/n): ").strip().lower()
        if save == 'y':
            with open('orowise_ai_cards.txt', 'a', encoding='utf-8') as f:
                f.write(f"ID: {proverb_entry.get('ID')}\nPROVERB: {proverb_entry.get('Mammaaksa_AO')}\n")
                f.write(response.text)
                f.write("\n" + "-"*50 + "\n\n")
            print("💾 AI Card saved to 'orowise_ai_cards.txt'!")
    except Exception as e:
        print(f"❌ Gemini Error: {e}")

# --- CLI Terminal Loop ---
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🔥 OroWise Hybrid AI Search Terminal 🔥")
    print("Commands:")
    print("  • Enter search text (e.g., 'patience | marriage')")
    print("  • Type 'ai 1', 'ai1', 'ai 2', or 'ai2' to analyze search results")
    print("  • Type 'exit' or 'q' to quit.")
    print("="*50 + "\n")

    last_results = []

    while True:
        raw_input_str = input("\nOroWise > ").strip()
        if raw_input_str.lower() in ['exit', 'q', 'quit']:
            print("Nagaatti!")
            break
        if not raw_input_str:
            continue

        # Flexible AI command parser
        ai_match = re.match(r'^ai\s*(\d+)$', raw_input_str.lower())
        if ai_match:
            try:
                idx = int(ai_match.group(1)) - 1
                if 0 <= idx < len(last_results):
                    ask_gemini_cultural_analysis(last_results[idx])
                else:
                    print(f"⚠️ Invalid index. Choose 1 to {len(last_results)}.")
            except Exception as e:
                print(f"⚠️ Error parsing AI command: {e}")
            continue

        # Category filter split using '|'
        if "|" in raw_input_str:
            parts = raw_input_str.split("|", 1)
            user_query, cat_filter = parts[0].strip(), parts[1].strip()
        else:
            user_query, cat_filter = raw_input_str, None

        last_results = semantic_search(user_query, category_filter=cat_filter, top_n=3)

        if not last_results:
            print(f"⚠️ No matches found.")
            continue

        print(f"\n📊 Top Matches for '{user_query}':\n")
        for rank, res in enumerate(last_results, 1):
            print(f"  {rank}. [{res.get('ID')}] {res.get('Mammaaksa_AO')} (Score: {res.get('_score')})")
            print(f"     Translation: {res.get('Translation_Literal_EN')}")
            print(f"     Meaning: {res.get('Meaning_EN')}\n")

        print("💡 Tip: Type 'ai 1', 'ai1', or 'ai2' to generate AI cultural analysis & media captions!")

