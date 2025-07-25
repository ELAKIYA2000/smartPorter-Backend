from flask import Flask, request, jsonify
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from flask_cors import CORS
import google.generativeai as genai



app = Flask(__name__)
CORS(app)

@app.route('/check-compatibility', methods=['POST'])
def check_compatibility():
    repo_url = request.args.get("repoUrl")

    if not repo_url:
        return jsonify({"error": "repoUrl is required"}), 400

    try:
        dependencies = fetch_pom_dependencies(repo_url)
    except Exception as e:
        return jsonify({"error": f"Failed to parse pom.xml: {str(e)}"}), 500

    results = []
    for dep in dependencies:
        group_id = dep["groupId"]
        artifact_id = dep["artifactId"]
        current_version = dep["version"]

        try:
            latest_version = fetch_latest_maven_version(group_id, artifact_id)
        except Exception as e:
            latest_version = "unknown"

        compatibility_flag, summary = compare_versions_with_gemini(current_version, latest_version, group_id, artifact_id)

        results.append({
            "groupId": group_id,
            "artifactId": artifact_id,
            "currentVersion": current_version,
            "latestVersion": latest_version,
            "compatibilityFlag": compatibility_flag,
            "compatibilitySummary": summary,
            "status": "update available" if latest_version != current_version else "up to date"
        })
        

    return jsonify(results), 200


def fetch_pom_dependencies(repo_url):
    parsed = urlparse(repo_url)
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        raise Exception("Invalid GitHub repo URL.")

    owner, repo = parts[0], parts[1]
    branches = ["main", "master"]
    pom_url = None
    response = None
    for branch in branches:
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/pom.xml"
        resp = requests.get(url)
        if resp.status_code == 200:
            pom_url = url
            response = resp
            break
    if response is None or response.status_code != 200:
        raise Exception("Unable to fetch pom.xml from 'main' or 'master' branch")

    root = ET.fromstring(response.text)
    ns = {"m": "http://maven.apache.org/POM/4.0.0"}

    dependencies = []
    for dep in root.findall(".//m:dependency", ns):
        group_id = dep.find("m:groupId", ns)
        artifact_id = dep.find("m:artifactId", ns)
        version = dep.find("m:version", ns)

        if group_id is not None and artifact_id is not None and version is not None:
            dependencies.append({
                "groupId": group_id.text.strip(),
                "artifactId": artifact_id.text.strip(),
                "version": version.text.strip()
            })

    return dependencies


def fetch_latest_maven_version(group_id, artifact_id):
    search_url = (
        f"https://search.maven.org/solrsearch/select?q=g:%22{group_id}%22+AND+a:%22{artifact_id}%22"
        "&core=gav&rows=1&wt=json&sort=version+desc"
    )
    response = requests.get(search_url)
    if response.status_code != 200:
        raise Exception("Failed to query Maven Central")

    data = response.json()
    docs = data.get("response", {}).get("docs", [])
    if not docs:
        raise Exception("No versions found on Maven Central")

    return docs[0]["v"]


# Configure API key (use env var or secret manager in production)
genai.configure(api_key="AIzaSyCHe9OkM4VNDhu4uWVFUTru80B4SJNIscM")

# Initialize the model
model = genai.GenerativeModel("gemini-1.5-pro")


def compare_versions_with_gemini(current, latest,group_id, artifact_id):
    if not current or not latest or current == "unknown" or latest == "unknown":
        return False, "Version information incomplete."

    prompt = f"""
    Compare these two Maven dependency versions:
    - Current version: {current}
    - Latest version: {latest}
    for groupId: {group_id}, artifactId: {artifact_id}

    Based on semantic versioning principles, is the current version compatible with the latest one?
    Respond with this JSON format:
    {{
        "compatible": true/false,
        "reason": "..."
    }}
    """

    try:
        response = model.generate_content(prompt)
        result = response.text.strip()

        # Extract boolean and reason from result
        import json
        parsed = json.loads(result)
        return parsed["compatible"], parsed["reason"]

    except Exception as e:
        return False, f"Error contacting Gemini: {str(e)}"


if __name__ == "__main__":
    app.run(port=8080)