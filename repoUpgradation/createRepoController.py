from fastapi import HTTPException
from git import Repo, GitCommandError
import os
import shutil
import stat
from createUpdatePomFile import upgrade_dependencies
from flask_cors import CORS

from flask import Flask, request

app = Flask(__name__)
CORS(app)

import os
import shutil
from git import Repo, GitCommandError
from fastapi import HTTPException

def handle_remove_readonly(func, path, exc):
    try:
        os.chmod(path, 0o755)
        func(path)
    except Exception:
        pass

def update_pom_and_push(repo_url, branch_name, new_pom_content, file_name="pom.xml"):
    repo_dir = "./temp_repo"
    file_path = os.path.join(repo_dir, file_name)

    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir, onerror=handle_remove_readonly)

    try:
        repo = Repo.clone_from(repo_url, repo_dir)
        git = repo.git

        # Check if branch exists remotely
        remote_branches = [ref.name.split('/')[-1] for ref in repo.remotes.origin.refs]
        if branch_name in remote_branches:
            git.checkout(branch_name)
        else:
            git.checkout('-b', branch_name)

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Overwrite the pom.xml with new content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_pom_content)

        relative_path = os.path.relpath(file_path, repo_dir)
        repo.index.add([relative_path])
        repo.index.commit(f"Update {file_name} with latest dependency versions")

        origin = repo.remote(name='origin')
        origin.push(branch_name)

        return f"✅ Branch '{branch_name}' updated and '{file_name}' modified."

    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=f"Git error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        try:
            if os.getcwd().startswith(os.path.abspath(repo_dir)):
                os.chdir(os.path.dirname(os.path.abspath(repo_dir)))
        except Exception:
            pass

        try:
            repo.close()
        except Exception:
            pass

        if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir, onerror=handle_remove_readonly)

@app.route('/update-repo', methods=['POST'])
def update_repo():
    req = request.get_json()
    repo_url = req["repoUrl"]
    branch_name = 'smartporter-upgrade'
    try:
        new_line = upgrade_dependencies(req)  # returns string now
        result = update_pom_and_push(repo_url, branch_name, new_line)
        return {"message": result}
    except Exception as e:
        return {"error": str(e)}, 500
    


if __name__ == "__main__":
    app.run(port=8000)