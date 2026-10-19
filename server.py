from flask import Flask, request, render_template_string
from search import semantic_search, ask_gemini_cultural_analysis, client

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>OroWise AI - Afaan Oromoo Proverb Engine</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; max-width: 700px; margin: auto; padding: 20px; background: #f9f9f9; }
        h1 { color: #1e5631; }
        input, button { padding: 10px; font-size: 16px; margin: 5px 0; width: 100%; box-sizing: border-box; }
        button { background: #1e5631; color: white; border: none; border-radius: 5px; cursor: pointer; }
        .card { background: white; padding: 15px; border-radius: 8px; margin-top: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .tag { color: #888; font-size: 0.9em; }
    </style>
</head>
<body>
    <h1>🌿 OroWise AI Engine</h1>
    <p>Search 3,351+ Afaan Oromoo Proverbs & Cultural Insights for Khoobaa Dubbii</p>

    <form method="GET" action="/">
        <input type="text" name="q" placeholder="Enter search (e.g. jaalala, patience)" value="{{ query }}">
        <button type="submit">🔍 Search Proverbs</button>
    </form>

    {% if results %}
        <h2>Search Results:</h2>
        {% for r in results %}
            <div class="card">
                <h3>[{{ r.ID }}] {{ r.Mammaaksa_AO }}</h3>
                <p><b>Translation:</b> {{ r.Translation_Literal_EN }}</p>
                <p><b>Meaning:</b> {{ r.Meaning_EN }}</p>
                <span class="tag">Category: {{ r.Category_EN }} | Score: {{ r._score }}</span>
                <form method="POST" action="/ai">
                    <input type="hidden" name="id" value="{{ r.ID }}">
                    <button type="submit" style="background:#4a7c59; margin-top:10px;">🤖 Generate Gemini AI Cultural Brief</button>
                </form>
            </div>
        {% endfor %}
    {% endif %}

    {% if ai_result %}
        <div class="card" style="border-left: 5px solid #1e5631;">
            <h2>🤖 Khoobaa Dubbii Cultural Analysis</h2>
            <pre style="white-space: pre-wrap; font-family: inherit;">{{ ai_result }}</pre>
        </div>
    {% endif %}
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    query = request.args.get('q', '')
    results = []
    if query:
        results = semantic_search(query, top_n=3)
    return render_template_string(HTML_TEMPLATE, query=query, results=results)

@app.route('/ai', methods=['POST'])
def ai_analysis():
    proverb_id = request.form.get('id')
    # Find entry by ID
    from search import data
    entry = next((item for item in data if str(item.get('ID')) == str(proverb_id)), None)
    
    ai_text = ""
    if entry and client:
        prompt = f"""
        You are an expert scholar in Afaan Oromoo literature for the 'Khoobaa Dubbii' platform.
        Analyze this Oromo proverb:
        Proverb: {entry.get('Mammaaksa_AO')}
        Translation: {entry.get('Translation_Literal_EN')}
        Meaning: {entry.get('Meaning_EN')}
        
        Provide:
        1. Deep Cultural Context & Philosophy
        2. Modern Life Application
        3. Ready-to-Publish Social Media Caption
        """
        try:
            response = client.models.generate_content(
                model='gemini-flash-latest',
                contents=prompt,
            )
            ai_text = response.text
        except Exception as e:
            ai_text = f"❌ Gemini Error: {e}"
    else:
        ai_text = "Gemini client not initialized or entry not found."

    return render_template_string(HTML_TEMPLATE, query="", results=[], ai_result=ai_text)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

