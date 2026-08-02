import os
import json
import tomllib
import urllib.request
import urllib.error
from datetime import datetime, timezone

# --- CONFIGURATION ---
STATE_FILE = "state.json"
CONFIG_FILE = "tracker.toml"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
TARGET_REPO = os.environ.get("GITHUB_REPOSITORY")

def github_api(method, endpoint, data=None):
    """Minimal wrapper for GitHub API requests."""
    url = f"https://api.github.com{endpoint}"
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    
    if data:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(data).encode("utf-8")
        
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"API Error ({url}): {e.code} - {e.read().decode('utf-8')}")
        return None

def get_target_release(releases, track):
    """Filters releases based on the requested track."""
    for r in releases:
        if r.get("draft"):
            continue
        if track == "stable" and r.get("prerelease"):
            continue
        if track == "prerelease" and not r.get("prerelease"):
            continue
        # "latest" accepts the first non-draft (stable or prerelease)
        return r
    return None

def main():
    if not GITHUB_TOKEN or not TARGET_REPO:
        print("Error: GITHUB_TOKEN and GITHUB_REPOSITORY environment variables are required.")
        return

    # Load Config and State
    with open(CONFIG_FILE, "rb") as f:
        config = tomllib.load(f)
    
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

    groups = {g["id"]: g["title"] for g in config.get("group", [])}
    updates_by_group = {}

    # Check for updates
    for project in config.get("project", []):
        repo = project["repo"]
        track = project["track"]
        group_id = project["group"]
        
        print(f"Checking {repo} ({track})...")
        releases = github_api("GET", f"/repos/{repo}/releases")
        
        if not releases:
            continue
            
        latest = get_target_release(releases, track)
        if not latest:
            continue
            
        tag = latest["tag_name"]
        
        # If it's a new release we haven't seen yet
        if state.get(repo) != tag:
            if group_id not in updates_by_group:
                updates_by_group[group_id] = []
                
            updates_by_group[group_id].append({
                "project_name": project["name"],
                "repo": repo,
                "tag": tag,
                "url": latest["html_url"],
                "body": latest.get("body", "*No release notes provided.*")
            })

    # Publish Consolidated Releases
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    
    for group_id, updates in updates_by_group.items():
        group_title = groups.get(group_id, group_id.title())
        release_tag = f"{group_id}-{timestamp}"
        release_name = f"{group_title} Updates - {timestamp}"
        
        # Build Release Markdown
        body = f"Consolidated release for **{group_title}** projects.\n\n"
        for u in updates:
            body += f"## {u['project_name']} (`{u['tag']}`)\n"
            body += f"[View original release on GitHub]({u['url']})\n\n"
            body += f"{u['body']}\n\n---\n"

        print(f"Publishing consolidated release: {release_name}")
        
        # Create the release in the current tracker repository
        response = github_api("POST", f"/repos/{TARGET_REPO}/releases", data={
            "tag_name": release_tag,
            "name": release_name,
            "body": body,
            "draft": False,
            "prerelease": False
        })
        
        # If release creation was successful, update the state
        if response and "id" in response:
            for u in updates:
                state[u["repo"]] = u["tag"]

    # Save updated state
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

if __name__ == "__main__":
    main()

