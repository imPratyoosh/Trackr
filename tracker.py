import os
import json
import tomllib
import urllib.request
import urllib.error

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
        if track == "dev" and not r.get("prerelease"):
            continue
        # "latest" accepts the first non-draft (whether stable or dev)
        return r
    return None

def main():
    if not GITHUB_TOKEN or not TARGET_REPO:
        print("Error: GITHUB_TOKEN and GITHUB_REPOSITORY are required.")
        return

    # Load Config and State
    with open(CONFIG_FILE, "rb") as f:
        config = tomllib.load(f)
    
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

    # Organize projects by group for GitHub Actions log tree
    grouped_projects = {}
    for repo_name, details in config.items():
        group_name = details.get("group", "ungrouped")
        if group_name not in grouped_projects:
            grouped_projects[group_name] = []
        details["name"] = repo_name  # Store the TOML heading name
        grouped_projects[group_name].append(details)

    # Check for updates and publish
    for group_name, projects in grouped_projects.items():
        # This tells GitHub Actions to create a collapsible log group
        print(f"::group::{group_name}")
        
        for project in projects:
            repo = project["repo"]
            track = project["track"]
            brand_name = project["name"]
            
            print(f"Checking {brand_name} ({repo} @ {track})...")
            releases = github_api("GET", f"/repos/{repo}/releases")
            
            if not releases:
                continue
                
            latest = get_target_release(releases, track)
            if not latest:
                continue
                
            tag = latest["tag_name"]
            
            # Check if this is a new release
            if state.get(repo) != tag:
                print(f"-> New release found: {tag}")
                
                # Format: "Patches-v1.2.0" for tag (avoids conflicts if 2 repos use v1.2.0)
                release_tag = f"{brand_name}-{tag}"
                # Format: "Patches v1.2.0" for title
                release_title = f"{brand_name} {tag}" 
                original_url = latest["html_url"]
                original_body = latest.get("body", "*No release notes provided.*")
                
                # Combine link with original body
                body = f"[View original release on GitHub]({original_url})\n\n---\n\n{original_body}"
                
                # Publish individual release
                response = github_api("POST", f"/repos/{TARGET_REPO}/releases", data={
                    "tag_name": release_tag,
                    "name": release_title,
                    "body": body,
                    "draft": False,
                    # Mark as prerelease if original was a prerelease (dev track)
                    "prerelease": latest.get("prerelease", False) 
                })
                
                if response and "id" in response:
                    print(f"-> Published: {release_title}")
                    state[repo] = tag

        # Close the GitHub Actions log group
        print("::endgroup::")

    # Save updated state
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

if __name__ == "__main__":
    main()
                
