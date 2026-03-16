"""
One-shot Vercel deployment for the MacroPulse marketing site.
Usage: python scripts/_deploy_vercel.py
"""
import json
import os
import sys
from pathlib import Path

import httpx

TOKEN = os.environ["VERCEL_TOKEN"]
TEAM_OR_USER = os.environ.get("VERCEL_USER_ID", "")
PROJECT_NAME = "macropulse"
SITE_DIR = Path(__file__).parent.parent / "site"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}


def read_files():
    files = []
    for path in sorted(SITE_DIR.rglob("*")):
        if path.is_file():
            rel = path.relative_to(SITE_DIR).as_posix()
            content = path.read_text(encoding="utf-8")
            files.append({"file": rel, "data": content, "encoding": "utf-8"})
    return files


def deploy(files):
    payload = {
        "name": PROJECT_NAME,
        "files": files,
        "target": "production",
        "projectSettings": {
            "framework": None,
            "buildCommand": None,
            "outputDirectory": None,
            "installCommand": None,
            "devCommand": None,
        },
    }
    print(f"Deploying {len(files)} files to project '{PROJECT_NAME}'...")
    resp = httpx.post(
        "https://api.vercel.com/v13/deployments",
        headers=HEADERS,
        json=payload,
        timeout=60,
    )
    return resp.status_code, resp.json()


def add_domain(project_id):
    for domain in ["macropulse.live", "www.macropulse.live"]:
        resp = httpx.post(
            f"https://api.vercel.com/v10/projects/{project_id}/domains",
            headers=HEADERS,
            json={"name": domain},
            timeout=30,
        )
        data = resp.json()
        status = "OK" if resp.status_code in (200, 201) else f"FAIL ({data.get('error', {}).get('message', resp.status_code)})"
        print(f"  Domain {domain}: {status}")


def main():
    files = read_files()
    total_kb = sum(len(f["data"]) for f in files) / 1024
    print(f"Files: {[f['file'] for f in files]}")
    print(f"Total: {total_kb:.1f} KB")

    status, data = deploy(files)

    if status not in (200, 201):
        print(f"\nDeploy failed ({status}):")
        print(json.dumps(data, indent=2))
        sys.exit(1)

    deploy_url = data.get("url", "")
    project_id = data.get("projectId", "")
    deploy_id = data.get("id", "")

    print(f"\nDeployed successfully!")
    print(f"  Deploy URL:  https://{deploy_url}")
    print(f"  Project ID:  {project_id}")
    print(f"  Deploy ID:   {deploy_id}")

    if project_id:
        print("\nAdding custom domains...")
        add_domain(project_id)

    print("\nDone. Set DNS records:")
    print("  macropulse.live     A    76.76.21.21")
    print("  www.macropulse.live CNAME cname.vercel-dns.com")


if __name__ == "__main__":
    main()
