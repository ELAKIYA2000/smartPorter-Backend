from flask import Flask, request, send_file, jsonify
import xml.etree.ElementTree as ET
import tempfile, os, shutil, subprocess, json

# app = Flask(__name__)

def clone_repo(repo_url, dest_dir):
    subprocess.run(["git", "clone", "--depth", "1", repo_url, dest_dir], check=True)

def update_pom_versions(pom_path, dependencies):
    ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
    ET.register_namespace('', ns['m'])
    tree = ET.parse(pom_path)
    root = tree.getroot()

    # Build lookup map
    lookup = {
        (d['groupId'], d['artifactId']): d['latestVersion']
        for d in dependencies
    }

    for dep in root.findall(".//m:dependency", ns):
        gid = dep.find("m:groupId", ns)
        aid = dep.find("m:artifactId", ns)
        ver = dep.find("m:version", ns)
        key = (gid.text if gid is not None else None,
               aid.text if aid is not None else None)

        if key in lookup:
            new_ver = lookup[key]
            if ver is not None:
                ver.text = new_ver
            else:
                new_elem = ET.SubElement(dep, "version")
                new_elem.text = new_ver

    tree.write(pom_path, encoding="utf-8", xml_declaration=True)
    return pom_path

# @app.route("/upgrade-dependencies", methods=["POST"])
def upgrade_dependencies(payload):
    temp_dir = tempfile.mkdtemp()
    try:
        repo_url = payload.get("repoUrl")
        deps = payload.get("dependencies")

        if not repo_url or not deps:
            raise ValueError("repo_url and dependencies are required")

        clone_repo(repo_url, temp_dir)

        pom_path = os.path.join(temp_dir, "pom.xml")
        if not os.path.exists(pom_path):
            raise FileNotFoundError("pom.xml not found in repo root")

        update_pom_versions(pom_path, deps)

        # ✅ Return the updated pom.xml content as a string
        with open(pom_path, 'r', encoding='utf-8') as f:
            return f.read()

    except subprocess.CalledProcessError as e:
        raise Exception(f"Git clone failed: {str(e)}")
    except Exception as e:
        raise Exception(str(e))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

# if __name__ == "__main__":
#     app.run(debug=True)
