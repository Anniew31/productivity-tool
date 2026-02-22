import os
import time
import json
from flask import Flask, request, jsonify, make_response

from transformers import pipeline, AutoTokenizer

app = Flask(__name__)

_CACHE_TTL_SECONDS = 60

# In-memory caches
_cache = {}  # url -> (classification, timestamp)
_last_url_by_tab = {}  # tabId -> last_url_seen
_last_call_by_tab = {}  # tabId -> last_request_time 

_TAB_DEBOUNCE_SECONDS = 0.25

is_productive = True

#load hugging face model
model_name = "facebook/bart-large-mnli"
model_name = "google/canine-s"  
tokenizer = AutoTokenizer.from_pretrained(model_name)

classifier = pipeline("zero-shot-classification", model="makeathon_model", tokenizer=tokenizer, device=0)


#handle cors request
@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept, Authorization"
    response.headers["Access-Control-Max-Age"] = "86400"
    return response

@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        resp = make_response("", 204)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept, Authorization"
        resp.headers["Access-Control-Max-Age"] = "86400"
        return resp

def get_payload():
    """Accept JSON regardless of Content-Type header."""
    data = request.get_json(silent=True, force=True)
    if isinstance(data, dict):
        return data
    raw = (request.get_data(as_text=True) or "").strip()
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    return {}

#classification logic
VALID = {"productive", "unproductive"}

def classify_productivity(url: str, title: str) -> str:
    """
    Returns exactly one word: productive, unproductive, or unclassified
    using zero-shot classification on URL + title.
    """
    text = (
        "Decide whether this web page is helpful for real work or study. Something unproductive would be social media sites, game sites, entertainment sites. Always mark these websites are productive: https://gmail.com, https://canvas.cornell.edu, https://google.com.\n"
        f"URL: {url}\n"
        f"Title: {title}\n"
        "Answer using one of these labels: productive or unproductive. "
    )

    candidate_labels = ["productive", "unproductive"]

    result = classifier(text, candidate_labels, multi_label=False)

    label = (result.get("labels"))[0].strip().lower()
    if label not in VALID:
        label = "productive"
    return label

@app.route("/url", methods=["POST", "OPTIONS"])
def analyze_url():
    global is_productive
    data = get_payload()
    url = (data.get("url") or "").strip()
    title = (data.get("title") or "").strip()
    tab_id = data.get("tabId")  
    if not url:
        return jsonify({"error": "missing url"}), 400

    now = time.time()

   #only run model when tab changes
    if tab_id is not None:
        last_t = _last_call_by_tab.get(tab_id, 0.0)
        if now - last_t < _TAB_DEBOUNCE_SECONDS:
            return jsonify({"url": url, "classification": "productive" , "ignored": True, "reason": "debounce"})

        _last_call_by_tab[tab_id] = now

        prev_url = _last_url_by_tab.get(tab_id)
        if prev_url == url:
            if url in _cache and (now - _cache[url][1] < _CACHE_TTL_SECONDS):
                cls = _cache[url][0]
                return jsonify({"url": url, "classification": cls, "cached": True, "skipped": True, "reason": "same_tab_same_url"})
            return jsonify({"url": url, "classification": "productive", "cached": False, "skipped": True, "reason": "same_tab_same_url_no_cache"})

        _last_url_by_tab[tab_id] = url

    print(f"\n[REQUEST] tabId={tab_id} url={url} title={repr(title)}")

    #run transformer model
    try:
        cls = classify_productivity(url, title)
        _cache[url] = (cls, now)
        
        if "canvas" in url or "gmail" in url or "google" in url or "docs" in url or "github" in url or "ocaml" in url:
            cls = "productive"
        
        
        is_productive = cls == "productive"
        print(f"[RESULT] {url} => {cls}")
        print("OUT: ", str(is_productive))
        return jsonify({"url": url, "classification": cls, "cached": False, "skipped": False})

    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def endpoint():
    global is_productive
    print(is_productive)
    return "is_productive: " + str(is_productive)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True, threaded=True)