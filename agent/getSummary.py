from flask import Flask, request, jsonify
import os
import shutil
import tempfile
from git import Repo
import json
from google.generativeai import GenerativeModel
from summarizer import summarize_with_gemini
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/analyze-compatibility", methods=["POST"])
def analyze_compatibility():
    data = request.get_json()
    repo_url = data.get("repoUrl")
    dependencies = data.get("dependencies", [])
    return summarize_with_gemini(dependencies)


    
    
if __name__ == "__main__":
    app.run(port=5000)
