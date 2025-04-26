# Instagram Scraping Toolkit: Scrapemaximus

> **A single-file helper for hobby-scale Instagram research**  
> *No browser automation, no proxies, minimal dependencies.*

This toolkit provides a streamlined way to:
1. Fetch **all followers** of any public (or your own private) Instagram profile, plus basic metadata
2. Download each follower's profile picture
3. Generate a lightweight **HTML + Markdown gallery** of avatars

---

## Quick start

```bash
# clone / cd / then:
python -m venv .venv && source .venv/bin/activate   # Windows ⇒ .venv\Scripts\Activate
pip install httpx                                    # only runtime dependency

# Run the script with one or more Instagram usernames
python InstagramScrapemaximus.py username1 username2
```

---

## How the toolkit works

### Authentication
* Requires a **logged-in cookie** (`sessionid=` etc.) pasted into `HEADERS["cookie"]` in the script
* Alternatively, store the cookie in `ig_cookie.txt` (already referenced in code)
* Keep that cookie out of version control!

### Scraping process
* Hits Instagram's **public GraphQL endpoint** (`query_hash c76146de99bb02f6415203be841dd25a`) to page through followers 50 at a time  
* Saves for each follower:
  * `username`
  * `full_name`
  * `is_private`
  * `is_verified`
  * `profile_pic_url`
* Writes follower data to a CSV file (`{username}_followers.csv`)

### Gallery generation
* Downloads every `profile_pic_url` (parallel, 8 at once) into `imgs/` directory  
* Produces two human-friendly views:
  * **`{username}_followers_gallery.html`** – 200 px circular avatars, username links open the profile in a new tab  
  * **`{username}_followers_gallery.md`** – same content, markdown-native

**Speed & safety:**  
Default 1–1.5 s delay ⇒ ~3 k rows/hour, well below IG's soft limits. Adjust `await asyncio.sleep()` if needed.

---

## Tips & extensions

* Add the **following** list: change `QUERY_HASH` to `d04b0a864b4b54837c0d870b0e77e076` and call a `get_following()` helper (implement similar to fetch_followers)
* Enrich each row with the follower's **bio** or **location** by querying `/api/v1/users/web_profile_info/` per username  
* Process multiple usernames in a single run by passing them as space-separated arguments: `python InstagramScrapemaximus.py user1 user2 user3`

---

## License

MIT – have fun, no warranty. Remember Instagram's Terms of Service: use responsibly and only on data you're authorized to fetch.
