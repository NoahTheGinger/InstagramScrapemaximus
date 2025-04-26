#!/usr/bin/env python
# Instagram Scraping Toolkit - Combined script that scrapes followers and creates a gallery
import csv
import asyncio
import httpx
import json
import random
import pathlib
import hashlib
import sys

# For the cookie part, use JSON escape website to escape the entire block and paste between quotation marks
# Open Instagram and find a request in Dev Tools that starts with "GraphQL" and copy the cookies
HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "x-ig-app-id": "936619743392459",
    "cookie": "<PLACE-COOKIE-DATA-HERE>"
}

# Try to load cookie from file if exists
cookie_file = pathlib.Path("ig_cookie.txt")
if cookie_file.exists():
    HEADERS["cookie"] = cookie_file.read_text().strip()

QUERY_HASH = "c76146de99bb02f6415203be841dd25a"  # followers hash
IMG_DIR = pathlib.Path("imgs")  # images/avatars land here
CONCURRENCY = 8  # parallel image fetches
TIMEOUT = 20

IMG_DIR.mkdir(exist_ok=True)

async def get_user_id(session, username):
    r = await session.get(
        f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}",
        headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()["data"]["user"]["id"]

async def fetch_followers(session, user_id):
    after, followers = None, []
    while True:
        vars_ = {
            "id": user_id, "first": 50,
            "include_reel": True, "fetch_mutual": False,
            **({"after": after} if after else {})
        }
        url = ("https://www.instagram.com/graphql/query/"
               f"?query_hash={QUERY_HASH}&variables={json.dumps(vars_, separators=(',', ':'))}")
        r = await session.get(url, headers=HEADERS, timeout=20)
        if r.status_code in (429, 401):
            await asyncio.sleep(random.uniform(30, 60))
            continue
        payload = r.json().get("data")
        if not payload:  # private / checkpoint / rate-limit edge-case
            print("⚠️  Skipping – unexpected payload:", r.text[:120])
            break
        edge_block = payload["user"]["edge_followed_by"]
        for edge in edge_block["edges"]:
            node = edge["node"]
            followers.append({
                "username": node["username"],
                "full_name": node["full_name"],
                "is_private": node["is_private"],
                "is_verified": node["is_verified"],
                "profile_pic_url": node["profile_pic_url"],
            })
        if not edge_block["page_info"]["has_next_page"]:
            break
        after = edge_block["page_info"]["end_cursor"]
        await asyncio.sleep(random.uniform(1.0, 1.6))
    return followers

def url_to_filename(url: str) -> str:
    """Stable, extension-preserving filename from any IG URL."""
    ext = pathlib.Path(url.split("?")[0]).suffix or ".jpg"
    digest = hashlib.md5(url.encode()).hexdigest()[:10]
    return f"{digest}{ext}"

async def fetch_one_image(session, row):
    url = row["profile_pic_url"]
    fname = IMG_DIR / url_to_filename(url)
    if fname.exists():  # skip duplicates
        return row | {"local_img": fname.name}
    try:
        r = await session.get(url, timeout=TIMEOUT, follow_redirects=True)
        r.raise_for_status()
        fname.write_bytes(r.content)
        return row | {"local_img": fname.name}
    except Exception as e:
        print(f"✗  {row['username']}  —  {e}")
        return row | {"local_img": ""}

async def download_all_images(rows):
    async with httpx.AsyncClient(follow_redirects=True) as session:
        sem = asyncio.Semaphore(CONCURRENCY)
        async def bound(row):
            async with sem:
                return await fetch_one_image(session, row)
        return await asyncio.gather(*(bound(r) for r in rows))

def build_html(rows, username):
    html_out = pathlib.Path(f"{username}_followers_gallery.html")
    html = """<!DOCTYPE html><meta charset="utf-8">
<title>Followers gallery</title>
<style>
body {font-family: Arial, system-ui; margin: 0; padding: 1rem;}
figure{display:inline-block;margin:10px;text-align:center;width:210px}
figure img{border-radius:50%;width:200px;height:200px;object-fit:cover;box-shadow:0 2px 6px #0002}
figcaption a{color:#0366d6;text-decoration:none;font-size:15px}
figcaption a:hover{text-decoration:underline}
</style>
"""
    for r in rows:
        if not r["local_img"]:
            continue
        username = r["username"]
        link = f"https://www.instagram.com/{username}/"
        html += (
            f'<figure>'
            f'<img src="{IMG_DIR}/{r["local_img"]}" alt="{username}">'
            f'<figcaption><a href="{link}" target="_blank" rel="noopener">{username}</a></figcaption>'
            f'</figure>\n'
        )
    html_out.write_text(html, encoding="utf-8")
    print(f"✓  Wrote {html_out}")

def build_md(rows, username):
    md_out = pathlib.Path(f"{username}_followers_gallery.md")
    md_lines = [f"# {username}'s Followers Gallery\n"]
    for r in rows:
        if not r["local_img"]:
            continue
        md_lines.append(f'![{r["username"]}]({IMG_DIR}/{r["local_img"]}) `{r["username"]}`\n')
    md_out.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"✓  Wrote {md_out}")

async def scrape_and_create_gallery(username):
    # Step 1: Scrape followers
    print(f"🔍 Scraping followers for {username}...")
    async with httpx.AsyncClient() as session:
        user_id = await get_user_id(session, username)
        followers = await fetch_followers(session, user_id)
        
        if not followers:
            print(f"{username}: no data captured")
            return
            
        # Save to CSV as intermediate step
        csv_path = pathlib.Path(f"{username}_followers.csv")
        with csv_path.open("w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=followers[0].keys())
            writer.writeheader()
            writer.writerows(followers)
        print(f"✓ {username}: saved {len(followers)} followers → {csv_path.name}")
    
    # Step 2: Create gallery
    print(f"🖼️ Creating gallery from {len(followers)} followers...")
    followers_with_images = await download_all_images(followers)
    build_html(followers_with_images, username)
    build_md(followers_with_images, username)
    print(f"✅ Complete! Gallery created for {username}'s {len(followers)} followers")

def main():
    if len(sys.argv) < 2:
        print("Usage: python InstagramScrapemaximus.py <username1> [username2] [username3] ...")
        print("Example: python InstagramScrapemaximus.py instagram")
        return
    
    usernames = sys.argv[1:]
    for username in usernames:
        asyncio.run(scrape_and_create_gallery(username))

if __name__ == "__main__":
    main() 