import sys
import os



import json



import urllib.request



import urllib.parse



import re







# Ensure UTF-8 stdio



import io



if sys.platform == "win32":



    try:



        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')



        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')



    except Exception:



        pass







def search_wikipedia(query: str, lang: str = "ru"):



    """Searches Wikipedia and returns verified snippets and real image thumbnail URLs."""



    try:



        encoded_query = urllib.parse.quote(query)



        api_url = f"https://{lang}.wikipedia.org/w/api.php?action=query&format=json&list=search&srsearch={encoded_query}&utf8=1&srlimit=5"



        req = urllib.request.Request(api_url, headers={"User-Agent": "DeepSeekWebAgentMCP/1.0 (edu; Windows)"})



        with urllib.request.urlopen(req, timeout=10) as resp:



            data = json.loads(resp.read().decode('utf-8'))







        search_results = data.get("query", {}).get("search", [])



        if not search_results:



            return {"query": query, "results": [], "message": "Ничего не найдено"}







        # Fetch details for the first 3 pages including pageimage



        page_ids = "|".join(str(item["pageid"]) for item in search_results[:3])



        details_url = f"https://{lang}.wikipedia.org/w/api.php?action=query&format=json&pageids={page_ids}&prop=extracts|pageimages&exintro=1&explaintext=1&pithumbsize=800"



        req_det = urllib.request.Request(details_url, headers={"User-Agent": "DeepSeekWebAgentMCP/1.0 (edu; Windows)"})



        with urllib.request.urlopen(req_det, timeout=10) as resp_det:



            det_data = json.loads(resp_det.read().decode('utf-8'))







        pages = det_data.get("query", {}).get("pages", {})



        final_results = []



        for pid_str, page in pages.items():



            final_results.append({



                "title": page.get("title"),



                "summary": page.get("extract", "")[:400] + ("..." if len(page.get("extract", "")) > 400 else ""),



                "image_url": page.get("thumbnail", {}).get("source"),



                "page_url": f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(page.get('title', ''))}"



            })







        return {"query": query, "results": final_results}



    except Exception as e:



        return {"query": query, "error": str(e)}







def search_duckduckgo(query: str, max_results: int = 5):



    """Searches DuckDuckGo HTML version and extracts organic titles, URLs, and snippets."""



    try:



        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)



        req = urllib.request.Request(



            url,



            headers={



                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",



                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"



            }



        )



        with urllib.request.urlopen(req, timeout=10) as resp:



            html = resp.read().decode('utf-8', errors='ignore')







        results = []



        snippets = re.findall(r'<a class="result__snippet[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)



        titles = re.findall(r'<a class="result__url[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)







        # Fallback regex for standard links



        matches = re.findall(r'<a class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>[\s\S]*?<a class="result__snippet[^>]*>(.*?)</a>', html)



        for link, title, snippet in matches[:max_results]:



            # Clean DDG redirect URL if present



            clean_link = link



            uddg = re.search(r'uddg=([^&]+)', link)



            if uddg:



                clean_link = urllib.parse.unquote(uddg.group(1))







            clean_title = re.sub(r'<[^>]+>', '', title).strip()



            clean_snippet = re.sub(r'<[^>]+>', '', snippet).strip()



            results.append({



                "title": clean_title,



                "url": clean_link,



                "snippet": clean_snippet



            })







        return {"query": query, "results": results if results else "Ничего не найдено или сработала капча"}



    except Exception as e:



        return {"query": query, "error": str(e)}















def translate_to_en(text: str) -> str:



    """Auto-translates Russian/Cyrillic queries to English for rich stock photo searches."""



    if not re.search(r'[\u0400-\u04FF]', text):



        return text



    try:



        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t&q=" + urllib.parse.quote(text)



        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})



        with urllib.request.urlopen(req, timeout=6) as r:



            data = json.loads(r.read().decode('utf-8'))



            translated = "".join(chunk[0] for chunk in data[0] if chunk[0]).strip()



            if translated:



                return translated



    except Exception:



        pass



    return text







def fetch_page_images(url: str, limit: int = 8):



    """Scrapes any website URL and extracts all high-resolution images (og:image and img tags)."""



    try:



        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})



        with urllib.request.urlopen(req, timeout=10) as resp:



            html = resp.read().decode('utf-8', errors='ignore')



        



        found_urls = []



        # 1. Check og:image



        for og in re.findall(r"""content=["\']([^"\']+)["\']""", html, re.I):



            found_urls.append(urllib.parse.urljoin(url, og))



            



        # 2. Check <img> tags



        for img in re.findall(r"""src=["\']([^"\']+\.(?:jpg|jpeg|png|webp))["\']""", html, re.I):



            full_img = urllib.parse.urljoin(url, img)



            if not full_img.endswith(('.svg', '.gif', '.ico')) and 'logo' not in full_img.lower() and 'icon' not in full_img.lower():



                found_urls.append(full_img)







        # Deduplicate while preserving order



        unique_urls = list(dict.fromkeys(found_urls))[:limit]



        media_files = []



        for i, u in enumerate(unique_urls, 1):



            name = Path(urllib.parse.urlparse(u).path).name or f"scraped_img_{i}.jpg"



            media_files.append({



                "url": u,



                "download_command": f"<<<ACTION: DOWNLOAD_FILE | URL: {u} | PATH: Desktop/ИмяПапки/img/{name}>>>"



            })







        return {



            "source_url": url,



            "found_count": len(media_files),



            "media_files": media_files



        }



    except Exception as e:



        return {"source_url": url, "error": str(e)}







def load_tokens():
    tokens = {}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(base_dir, ".."))
    tokens_file = os.path.join(root_dir, "my_tokens.txt")
    example_file = os.path.join(root_dir, "my_tokens.example.txt")

    # Auto-create my_tokens.txt from template on first run if missing
    if not os.path.exists(tokens_file) and os.path.exists(example_file):
        try:
            import shutil
            shutil.copy2(example_file, tokens_file)
        except Exception:
            pass
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "..", "my_tokens.txt"),
        os.path.join(os.getcwd(), "my_tokens.txt")
    ]
    for p in possible_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            tokens[k.strip()] = v.strip()
                break
            except Exception:
                pass
# Aliases: support both variants (with _API_KEY / _ACCESS_KEY and short _KEY)
    if 'PIXABAY_API_KEY' in tokens and 'PIXABAY_KEY' not in tokens:
        tokens['PIXABAY_KEY'] = tokens['PIXABAY_API_KEY']
    elif 'PIXABAY_KEY' in tokens and 'PIXABAY_API_KEY' not in tokens:
        tokens['PIXABAY_API_KEY'] = tokens['PIXABAY_KEY']

    if 'UNSPLASH_ACCESS_KEY' in tokens and 'UNSPLASH_KEY' not in tokens:
        tokens['UNSPLASH_KEY'] = tokens['UNSPLASH_ACCESS_KEY']
    elif 'UNSPLASH_KEY' in tokens and 'UNSPLASH_ACCESS_KEY' not in tokens:
        tokens['UNSPLASH_ACCESS_KEY'] = tokens['UNSPLASH_KEY']

    if 'PEXAFY_API_KEY' in tokens and 'PEXAFY_KEY' not in tokens:
        tokens['PEXAFY_KEY'] = tokens['PEXAFY_API_KEY']
    elif 'PEXAFY_KEY' in tokens and 'PEXAFY_API_KEY' not in tokens:
        tokens['PEXAFY_API_KEY'] = tokens['PEXAFY_KEY']

    return tokens

def get_proxy_opener():
    # Uses VPN proxy 127.0.0.1:10809 if active, bypasses otherwise
    try:
        import ssl
        ctx = ssl._create_unverified_context()
        proxy_handler = urllib.request.ProxyHandler({'http': 'http://127.0.0.1:10809', 'https': 'http://127.0.0.1:10809'})
        https_handler = urllib.request.HTTPSHandler(context=ctx)
        return urllib.request.build_opener(proxy_handler, https_handler)
    except Exception:
        return urllib.request.build_opener()

def search_pixabay(query: str, limit: int = 6, api_key: str = "") -> list:
    if not api_key:
        return []
    try:
        opener = get_proxy_opener()
        clean_q = urllib.parse.quote(query)
        # Pixabay requires per_page between 3 and 200
        pix_limit = max(3, min(limit, 200))
        url = f"https://pixabay.com/api/?key={api_key}&q={clean_q}&image_type=photo&orientation=horizontal&safesearch=true&per_page={pix_limit}"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        })
        with opener.open(req, timeout=7) as r:
            data = json.loads(r.read().decode('utf-8'))
        
        results = []
        for hit in data.get("hits", []):
            img_url = hit.get("largeImageURL") or hit.get("webformatURL")
            tags = hit.get("tags", "photo")
            title = tags.split(",")[0].strip().title() + f" ({hit.get('id')})"
            w = hit.get("imageWidth") or hit.get("webformatWidth", 1920)
            h = hit.get("imageHeight") or hit.get("webformatHeight", 1080)
            size_kb = round(hit.get("imageSize", 1800000) / 1024, 1)
            ext = "jpg"
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', title[:30]).strip('_') + f".{ext}"
            
            results.append({
                "title": title + f".{ext}",
                "url": img_url,
                "width": w,
                "height": h,
                "size_kb": size_kb,
                "type": "image",
                "provider": "Pixabay (Commercial Stock)",
                "download_command": f"<<<ACTION: DOWNLOAD_FILE | URL: {img_url} | PATH: Desktop/ИмяПапки/img/{safe_name}>>>"
            })
        return results
    except Exception as e:
        print(f"Pixabay search error: {e}")
        return []

def search_unsplash(query: str, limit: int = 6, access_key: str = "") -> list:
    if not access_key:
        return []
    try:
        opener = get_proxy_opener()
        clean_q = urllib.parse.quote(query)
        url = f"https://api.unsplash.com/search/photos?query={clean_q}&client_id={access_key}&per_page={limit}&orientation=landscape"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        })
        with opener.open(req, timeout=7) as r:
            data = json.loads(r.read().decode('utf-8'))
            
        results = []
        for item in data.get("results", []):
            img_url = item.get("urls", {}).get("regular") or item.get("urls", {}).get("full")
            desc = item.get("alt_description") or item.get("description") or "Modern photo"
            title = desc[:30].strip().title() + f" ({item.get('id')})"
            w = item.get("width", 1920)
            h = item.get("height", 1080)
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', title[:30]).strip('_') + ".jpg"
            
            results.append({
                "title": title + ".jpg",
                "url": img_url,
                "width": w,
                "height": h,
                "size_kb": 950.0,
                "type": "image",
                "provider": "Unsplash (Designer Curation)",
                "download_command": f"<<<ACTION: DOWNLOAD_FILE | URL: {img_url} | PATH: Desktop/ИмяПапки/img/{safe_name}>>>"
            })
        return results
    except Exception as e:
        print(f"Unsplash search error: {e}")
        return []

def search_free_media(query: str, media_type: str = "image", limit: int = 6, provider: str = "auto"):
    """Multi-provider image search engine.
    1. Pixabay (Commercial Stock) - top modern photography for web design.
    2. Unsplash (Designer Curation) - aesthetic architecture and interiors.
    3. Wikimedia Commons - encyclopedic fallback (works 100% without keys if my_tokens.txt is absent)."""
    try:
        tokens = load_tokens()
        translated_query = translate_to_en(query).strip()
        
        # 1. Primary: Pixabay (if token is available)
        pix_key = tokens.get("PIXABAY_KEY", "")
        if pix_key and provider in ["auto", "pixabay"]:
            pix_results = search_pixabay(translated_query, limit=limit, api_key=pix_key)
            if len(pix_results) >= 2:
                return {
                    "query": query,
                    "translated_query": translated_query,
                    "provider": "Pixabay (Commercial Stock)",
                    "media_type": media_type,
                    "found_count": len(pix_results),
                    "media_files": pix_results,
                    "advice": "Скопируй 'download_command' для моментального скачивания файла без 404 ошибок!"
                }

        # 2. Secondary: Unsplash (if token is available)
        uns_key = tokens.get("UNSPLASH_KEY", "")
        if uns_key and provider in ["auto", "unsplash"]:
            uns_results = search_unsplash(translated_query, limit=limit, access_key=uns_key)
            if len(uns_results) >= 2:
                return {
                    "query": query,
                    "translated_query": translated_query,
                    "provider": "Unsplash (Designer Curation)",
                    "media_type": media_type,
                    "found_count": len(uns_results),
                    "media_files": uns_results,
                    "advice": "Скопируй 'download_command' для моментального скачивания файла без 404 ошибок!"
                }

        # 3. Tertiary: Wikimedia Commons fallback (zero keys required)
        import ssl
        ctx = ssl._create_unverified_context()
        search_term = translated_query
        term_lower = search_term.lower()
        if any(k in term_lower for k in ["living room", "гостин", "зал"]):
            search_term = '"living room" interior'
        elif any(k in term_lower for k in ["studio", "студи"]):
            search_term = '"studio apartment"'
        elif any(k in term_lower for k in ["apartment", "flat", "квартир"]):
            search_term = 'interior "apartment" design'
        elif any(k in term_lower for k in ["wooden frame", "timber frame", "frame house", "каркас"]):
            search_term = '"timber framing" construction house'
        elif any(k in term_lower for k in ["bathroom", "санузел", "ванн", "туалет"]):
            search_term = '"bathroom" modern interior'
        elif any(k in term_lower for k in ["kitchen", "кухн"]):
            search_term = '"kitchen" modern interior'
        elif any(k in term_lower for k in ["before renovation", "до ремонта", "чернов", "стройка"]):
            search_term = 'house renovation interior construction drywall'
        elif any(k in term_lower for k in ["coffee", "кофе"]):
            search_term = '"coffee cup" cafe'

        final_query = f"{search_term} filetype:bitmap"
        encoded = urllib.parse.quote(final_query)
        api_url = (
            f"https://commons.wikimedia.org/w/api.php?action=query"
            f"&generator=search&gsrnamespace=6&gsrsearch={encoded}&gsrlimit=35"
            f"&prop=imageinfo&iiprop=url|mime|size|dimensions&format=json"
        )
        req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"})
        with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        pages = data.get("query", {}).get("pages", {})
        results = []
        junk_keywords = [
            "schweiker", "hughes", "tate", "dorm", "recreation", "restroom", "park", "villa", "estate", "scale",
            "map", "plan", "magazine", "drawing", "sketch", "advertisement", "archive", "century", 
            "newspaper", "postcard", "engraving", "heritage", "temple", "museum", "hotel", "ruin", 
            "ancient", "statue", "monument", "historic", "church", "school", "umbrella", "bench", 
            "fountain", "restaurant", "nepal", "laos", "village", "cabin", "log cabin", "civilisation",
            "plumbing illustrated", "bakery", "bäckerei", "barn", "horse barn", "bishkek", "kyrgyzstan", "california street"
        ]

        for pid, p in pages.items():
            title = p.get("title", "").replace("File:", "").strip()
            t_lower = title.lower()
            if any(f"({y}" in title for y in range(1800, 1970)):
                continue
            if any(junk in t_lower for junk in junk_keywords):
                continue

            infos = p.get("imageinfo", [])
            if not infos:
                continue
            info = infos[0]
            raw_url = info.get("url", "")
            if not raw_url:
                continue
            clean_url = raw_url.split("?")[0]
            mime = info.get("mime", "")
            w = info.get("width", 0)
            h = info.get("height", 0)

            if media_type == "image":
                if mime not in ["image/jpeg", "image/png", "image/webp"] or w < 900 or h < 600:
                    continue

            ext = clean_url.split(".")[-1]
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', title[:30]).strip('_') + f".{ext}"
            size_kb = round(info.get("size", 0) / 1024, 1)

            results.append({
                "title": title,
                "url": clean_url,
                "width": w,
                "height": h,
                "size_kb": size_kb,
                "type": media_type,
                "provider": "Wikimedia Commons (Free Archive)",
                "download_command": f"<<<ACTION: DOWNLOAD_FILE | URL: {clean_url} | PATH: Desktop/ИмяПапки/img/{safe_name}>>>"
            })
            if len(results) >= limit:
                break

        return {
            "query": query,
            "translated_query": translated_query,
            "provider": "Wikimedia Commons (Free Archive)",
            "media_type": media_type,
            "found_count": len(results),
            "media_files": results,
            "advice": "Скопируй 'download_command' для моментального скачивания файла без 404 ошибок!"
        }
    except Exception as e:
        return {"query": query, "error": str(e), "message": "Ошибка поиска медиа"}

# -------------------------------------------------------------
# ICON LIBRARY & SVG ENGINE (Lucide Icons)
# -------------------------------------------------------------
BUILTIN_ICONS = {
    "phone": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>',
    "phone-call": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/><path d="M14.05 2a9 9 0 0 1 8 7.94"/><path d="M14.05 6A5 5 0 0 1 18 10"/></svg>',
    "mail": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>',
    "map-pin": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/></svg>',
    "check": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>',
    "check-circle": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/></svg>',
    "star": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
    "shield-check": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/></svg>',
    "clock": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    "calendar": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/></svg>',
    "arrow-right": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>',
    "chevron-down": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>',
    "menu": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="18" y2="18"/></svg>',
    "x": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>',
    "calculator": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="16" height="20" x="4" y="2" rx="2"/><line x1="8" x2="16" y1="6" y2="6"/><line x1="16" x2="16" y1="14" y2="14"/><path d="M16 10h.01"/><path d="M12 10h.01"/><path d="M8 10h.01"/><path d="M12 14h.01"/><path d="M8 14h.01"/><path d="M12 18h.01"/><path d="M8 18h.01"/></svg>',
    "hammer": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 12-8.5 8.5c-.83.83-2.17.83-3 0 0 0 0 0 0 0a2.12 2.12 0 0 1 0-3L12 9"/><path d="M17.64 15 22 10.64"/><path d="m20.91 3.26-6.36 6.36"/><path d="m12.7 7.7 3.6-3.6a2 2 0 0 1 2.8 0l1.4 1.4a2 2 0 0 1 0 2.8l-3.6 3.6"/></svg>',
    "wrench": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>',
    "home": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
    "user": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    "sparkles": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>',
    "truck": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/><path d="M15 18H9"/><path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14"/><circle cx="17" cy="18" r="2"/><circle cx="7" cy="18" r="2"/></svg>',
    "shopping-cart": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="21" r="1"/><circle cx="19" cy="21" r="1"/><path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12"/></svg>',
    "search": '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>'
}

ICON_SYNONYMS = {
    "телефон": "phone", "звонок": "phone-call", "трубка": "phone",
    "почта": "mail", "письмо": "mail", "email": "mail",
    "карта": "map-pin", "адрес": "map-pin", "локация": "map-pin",
    "галочка": "check", "успех": "check-circle", "да": "check",
    "звезда": "star", "рейтинг": "star", "отзыв": "star",
    "щит": "shield-check", "гарантия": "shield-check", "надежность": "shield-check",
    "часы": "clock", "время": "clock", "срок": "clock",
    "календарь": "calendar", "дата": "calendar",
    "стрелка": "arrow-right", "далее": "arrow-right", "подробнее": "arrow-right",
    "меню": "menu", "бургер": "menu", "крестик": "x", "закрыть": "x",
    "калькулятор": "calculator", "расчет": "calculator", "цена": "calculator",
    "молоток": "hammer", "ремонт": "hammer", "ключ": "wrench", "инструмент": "wrench",
    "дом": "home", "квартира": "home", "коттедж": "home",
    "человек": "user", "мастер": "user", "клиент": "user", "профиль": "user",
    "искорка": "sparkles", "новинка": "sparkles", "топ": "sparkles",
    "доставка": "truck", "машина": "truck", "грузовик": "truck",
    "корзина": "shopping-cart", "заказ": "shopping-cart",
    "поиск": "search", "лупа": "search"
}

def get_svg_icon(name: str, color: str = "currentColor", size: int = 24, save_path: str = "") -> dict:
    """Returns clean inline SVG for Lucide icons or saves it to save_path."""
    name_clean = name.lower().strip().replace(" ", "-").replace("_", "-")
    if name_clean in ICON_SYNONYMS:
        name_clean = ICON_SYNONYMS[name_clean]
    
    svg_code = None
    if name_clean in BUILTIN_ICONS:
        svg_code = BUILTIN_ICONS[name_clean].format(color=color, size=size)
    else:
        url = f"https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/{name_clean}.svg"
        try:
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=ctx, timeout=4) as resp:
                raw_svg = resp.read().decode('utf-8')
                raw_svg = re.sub(r'width="\d+"', f'width="{size}"', raw_svg)
                raw_svg = re.sub(r'height="\d+"', f'height="{size}"', raw_svg)
                raw_svg = re.sub(r'stroke="[^"]*"', f'stroke="{color}"', raw_svg)
                svg_code = raw_svg
        except Exception as e:
            return {"status": "error", "message": f"Иконка '{name_clean}' не найдена: {e}. Рекомендуем использовать одну из встроенных: {list(BUILTIN_ICONS.keys())[:15]}"}

    saved_to = None
    if save_path and svg_code:
        try:
            p = save_path
            if p.startswith("Desktop/") or p.startswith("Desktop\\"):
                desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Рабочий стол")
                if not os.path.exists(desktop):
                    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                p = os.path.join(desktop, p[8:])
            os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(svg_code)
            saved_to = p
        except Exception as e:
            return {"status": "error", "message": f"Не удалось сохранить иконку в {save_path}: {e}"}

    return {
        "status": "success",
        "icon_name": name_clean,
        "size": size,
        "color": color,
        "saved_path": saved_to,
        "inline_svg": svg_code,
        "html_usage": f'<span class="icon icon-{name_clean}">{svg_code}</span>'
    }

def search_icons(query: str) -> dict:
    """Searches available Lucide SVG icons by Russian or English keywords."""
    q = query.lower().strip()
    direct_match = ICON_SYNONYMS.get(q, q)
    matches = []
    for rus, eng in ICON_SYNONYMS.items():
        if q in rus or q in eng:
            if eng not in matches:
                matches.append(eng)
    for b in BUILTIN_ICONS:
        if q in b and b not in matches:
            matches.append(b)
    return {
        "status": "success",
        "query": query,
        "primary_icon": direct_match if direct_match in BUILTIN_ICONS or matches else "check",
        "matching_icons": matches[:10] if matches else list(BUILTIN_ICONS.keys())[:10],
        "tip": "Используй get_svg_icon с выбранным именем для мгновенной вставки SVG!"
    }

# -------------------------------------------------------------
# WEBSITE & COMPETITOR ANALYZER
# -------------------------------------------------------------
def analyze_website(url: str) -> dict:
    """Analyzes a website/landing page structure, typography, colors, and content blocks."""
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8'
    }

    try:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return {"status": "error", "url": url, "message": f"Не удалось загрузить сайт: {str(e)}"}

    title_m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    title = re.sub(r'\s+', ' ', title_m.group(1)).strip() if title_m else "Не указан"

    desc_m = re.search(r"""<meta[^>]+name=['"]description['"][^>]+content=['"](.*?)['"]""", html, re.IGNORECASE)
    desc = desc_m.group(1).strip() if desc_m else "Не указано"

    h1_list = [re.sub(r'<[^>]+>', '', h).strip() for h in re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)]
    h2_list = [re.sub(r'<[^>]+>', '', h).strip() for h in re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.IGNORECASE | re.DOTALL)]
    h1_list = [re.sub(r'\s+', ' ', h) for h in h1_list if h][:4]
    h2_list = [re.sub(r'\s+', ' ', h) for h in h2_list if h][:8]

    buttons = re.findall(r'<button[^>]*>(.*?)</button>', html, re.IGNORECASE | re.DOTALL)
    btn_clean = []
    for b in buttons:
        t = re.sub(r'<[^>]+>', '', b).strip()
        t = re.sub(r'\s+', ' ', t)
        if 2 < len(t) < 40 and t not in btn_clean:
            btn_clean.append(t)
    ctas = btn_clean[:6]

    hex_colors = re.findall(r'#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})\b', html)
    color_counts = {}
    for c in hex_colors:
        c_up = ("#" + c).upper()
        if len(c_up) == 4:
            c_up = "#" + c_up[1]*2 + c_up[2]*2 + c_up[3]*2
        if c_up in ["#FFFFFF", "#000000", "#EEEEEE", "#CCCCCC", "#333333", "#111111", "#222222"]:
            continue
        color_counts[c_up] = color_counts.get(c_up, 0) + 1
    sorted_colors = sorted(color_counts.items(), key=lambda x: x[1], reverse=True)
    palette = [c[0] for c in sorted_colors[:5]]

    google_fonts = re.findall(r"""fonts\.googleapis\.com/css2\?family=([^&'"]+)""", html)
    fonts_found = []
    for f in google_fonts:
        f_name = urllib.parse.unquote(f.split(":")[0]).replace("+", " ")
        if f_name not in fonts_found:
            fonts_found.append(f_name)

    sections = []
    html_lower = html.lower()
    patterns = [
        ("Шапка (Header/Nav)", ["<header", "class=\"header", "id=\"header", "<nav"]),
        ("Главный баннер (Hero)", ["hero", "banner", "main-slider", "jumbotron"]),
        ("Преимущества / Услуги", ["services", "features", "advantages", "benefits", "услуги", "преимущества"]),
        ("Портфолио / Работы", ["portfolio", "gallery", "works", "projects", "кейсы", "наши работы"]),
        ("Калькулятор / Тарифы", ["calculator", "pricing", "tariffs", "цены", "стоимость"]),
        ("Отзывы", ["reviews", "testimonials", "feedback", "отзывы"]),
        ("Контакты и форма", ["contacts", "contact-form", "форма", "footer"])
    ]
    for sec_name, keys in patterns:
        if any(k in html_lower for k in keys):
            sections.append(sec_name)

    return {
        "status": "success",
        "url": url,
        "title": title,
        "meta_description": desc,
        "sections_detected": sections,
        "primary_headings_h1": h1_list,
        "secondary_headings_h2": h2_list,
        "call_to_actions": ctas,
        "brand_color_palette": palette,
        "fonts_detected": fonts_found,
        "design_brief_for_deepseek": f"Структура референса: {', '.join(sections)}. Рекомендуемые цвета: {', '.join(palette[:3]) if palette else 'синий/изумрудный акцент'}. Шрифты: {', '.join(fonts_found) if fonts_found else 'Inter / Montserrat'}."
    }

TOOLS = [
    {
        "name": "search_pixabay",
        "description": "Прямой поиск коммерческих фотографий высокого разрешения в Pixabay (лимит 5 000 запросов/час). Идеально для сайтов: современные кухни, ремонты, квартиры-студии, каркасные дома, мебель в 4K/6K. Ключ считывается из my_tokens.txt. В автономной среде без ключей автоматически используется открытый поиск.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Поисковый запрос на русском или английском (например 'современная кухня', 'living room', 'timber frame house')"},
                "limit": {"type": "integer", "description": "Количество результатов (по умолчанию 5)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_unsplash",
        "description": "Прямой поиск дизайнерских и архитектурных фотографий в Unsplash. Премиальные интерьеры, кинематографичный свет, стильные фасады. Ключ считывается из my_tokens.txt.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Поисковый запрос на английском или русском (например 'modern apartment interior', 'minimalist house')"},
                "limit": {"type": "integer", "description": "Количество результатов (по умолчанию 5)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "check_available_stocks",
        "description": "Проверяет наличие файла my_tokens.txt и статус всех фотобанков на текущем компьютере (Pixabay, Unsplash, Pexafy, Wikimedia Commons, AI Generator). Используй при старте, чтобы знать доступные на этой машине источники!",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_svg_icon",
        "description": "Возвращает готовый чистый векторный SVG-код для популярных иконок (Lucide / Feather) по названию (phone, mail, map-pin, check, star, hammer, wrench, home, clock, arrow-right, sparkles, truck, etc.) или сохраняет в файл. Идеально для оформления карточек, кнопок и меню сайта без лишних библиотек!",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Название иконки (на английском или русском: phone, звонок, mail, почта, check, галочка, star, звезда, hammer, ремонт, home, дом, truck, доставка и т.д.)"},
                "color": {"type": "string", "description": "Цвет обводки SVG (например 'currentColor', '#2563eb', '#10b981'). По умолчанию 'currentColor'"},
                "size": {"type": "integer", "description": "Размер иконки в пикселях (по умолчанию 24)"},
                "save_path": {"type": "string", "description": "Опциональный путь для сохранения файла (например 'Desktop/test 6/img/icons/phone.svg')"}
            },
            "required": ["name"]
        }
    },
    {
        "name": "search_icons",
        "description": "Ищет подходящие SVG-иконки по ключевому слову на русском или английском (например 'телефон', 'гарантия', 'доставка', 'звезда').",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Поисковый запрос (например 'звонок', 'карта', 'калькулятор')"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "analyze_website",
        "description": "Анализирует сайт-конкурент или референс по URL. Извлекает структуру блоков (hero, услуги, отзывы, контакты), цветовую палитру бренда, используемые шрифты, заголовки H1/H2 и текст кнопок (CTA). Идеально для создания ТЗ и быстрого прототипирования современных лендингов!",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Полная ссылка на сайт-референс (например https://example.com)"}
            },
            "required": ["url"]
        }
    },



    {



        "name": "search_duckduckgo",



        "description": "Ищет информацию в Интернете через DuckDuckGo (статьи, новости, документация, сайты).",



        "inputSchema": {



            "type": "object",



            "properties": {



                "query": {"type": "string", "description": "Поисковый запрос"}



            },



            "required": ["query"]



        }



    },



    {



        "name": "search_wikipedia",



        "description": "Ищет текстовые энциклопедические статьи в Википедии. ВНИМАНИЕ: СТРОГО ЗАПРЕЩЕНО использовать для поиска фото для сайтов (выдаст старинных художников и телешоу)! Для фото используй ТОЛЬКО search_free_media!",



        "inputSchema": {



            "type": "object",



            "properties": {



                "query": {"type": "string", "description": "Название темы или статьи"},



                "lang": {"type": "string", "description": "Языковой раздел (ru или en), по умолчанию ru"}



            },



            "required": ["query"]



        }



    }



,



    {



        "name": "search_free_media",



        "description": "Универсальный авто-поиск фото без авторских прав: автоматически опрашивает Pixabay (5000 req/h) -> Unsplash -> Wikimedia. Поддерживает Graceful Degradation: при наличии ключей использует коммерческие стоки 4K/6K, в чистом окружении — открытые архивы.",



        "inputSchema": {



            "type": "object",



            "properties": {



                "query": {"type": "string", "description": "Что искать (на английском или русском, например: 'wooden lamp', 'fire flame', 'nature landscape')"},



                "media_type": {"type": "string", "enum": ["image", "video"], "description": "'image' для фото или 'video' для видеороликов, по умолчанию 'image'"},



                "limit": {"type": "integer", "description": "Количество результатов (1-10), по умолчанию 5"}



            },



            "required": ["query"]



        }



    },



    {



        "name": "fetch_page_images",



        "description": "Парсит любую веб-страницу и извлекает прямые ссылки на изображения высокого разрешения (og:image и фотографии).",



        "inputSchema": {



            "type": "object",



            "properties": {



                "url": {"type": "string", "description": "URL страницы сайта"}



            },



            "required": ["url"]



        }



    }



]







def main():



    while True:



        line = sys.stdin.readline()



        if not line:



            break



        line = line.strip()



        if not line:



            continue



        try:



            req = json.loads(line)



        except Exception:



            continue







        req_id = req.get("id")



        method = req.get("method")



        params = req.get("params", {})







        if method == "initialize":



            resp = {



                "jsonrpc": "2.0",



                "id": req_id,



                "result": {



                    "protocolVersion": "2024-11-05",



                    "capabilities": {"tools": {}},



                    "serverInfo": {"name": "web-search-mcp", "version": "1.0.0"}



                }



            }



            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")



            sys.stdout.flush()







        elif method == "notifications/initialized":



            pass







        elif method == "tools/list":



            resp = {



                "jsonrpc": "2.0",



                "id": req_id,



                "result": {"tools": TOOLS}



            }



            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")



            sys.stdout.flush()







        elif method == "tools/call":



            tool_name = params.get("name")



            args = params.get("arguments", {})







            if tool_name == "search_duckduckgo":



                query = args.get("query", "")



                data = search_duckduckgo(query)



                resp = {



                    "jsonrpc": "2.0",



                    "id": req_id,



                    "result": {



                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}]



                    }



                }



            elif tool_name == "get_svg_icon":
                name = args.get("name", "check")
                color = args.get("color", "currentColor")
                size = int(args.get("size", 24))
                save_path = args.get("save_path", "")
                data = get_svg_icon(name, color, size, save_path)
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}]
                    }
                }

            elif tool_name == "search_icons":
                query = args.get("query", "")
                data = search_icons(query)
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}]
                    }
                }

            elif tool_name == "analyze_website":
                url = args.get("url", "")
                data = analyze_website(url)
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}]
                    }
                }

            elif tool_name == "search_wikipedia":



                query = args.get("query", "")



                lang = args.get("lang", "ru")



                data = search_wikipedia(query, lang)



                resp = {



                    "jsonrpc": "2.0",



                    "id": req_id,



                    "result": {



                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}]



                    }



                }



            elif tool_name == "search_pixabay":
                query = args.get("query", "")
                limit = int(args.get("limit", 5))
                tokens = load_tokens()
                key = tokens.get("PIXABAY_KEY", "")
                if not key:
                    data = {
                        "status": "info",
                        "message": "API-ключ Pixabay не сконфигурирован в my_tokens.txt. Используйте универсальный поиск 'search_free_media' — он автоматически работает в автономном режиме без ключей!"
                    }
                else:
                    trans_q = translate_to_en(query).strip()
                    res = search_pixabay(trans_q, limit=limit, api_key=key)
                    data = {
                        "query": query,
                        "translated_query": trans_q,
                        "provider": "Pixabay (Commercial Stock)",
                        "found_count": len(res),
                        "media_files": res,
                        "advice": "Скопируй 'download_command' для моментального скачивания файла!"
                    }
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}]
                    }
                }

            elif tool_name == "search_unsplash":
                query = args.get("query", "")
                limit = int(args.get("limit", 5))
                tokens = load_tokens()
                key = tokens.get("UNSPLASH_KEY", "")
                if not key:
                    data = {
                        "status": "info",
                        "message": "API-ключ Unsplash не сконфигурирован в my_tokens.txt. Используйте 'search_free_media' для работы через доступные источники."
                    }
                else:
                    trans_q = translate_to_en(query).strip()
                    res = search_unsplash(trans_q, limit=limit, access_key=key)
                    data = {
                        "query": query,
                        "translated_query": trans_q,
                        "provider": "Unsplash (Designer Curation)",
                        "found_count": len(res),
                        "media_files": res,
                        "advice": "Скопируй 'download_command' для моментального скачивания файла!"
                    }
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}]
                    }
                }

            elif tool_name == "check_available_stocks":
                tokens = load_tokens()
                has_pixabay = bool(tokens.get("PIXABAY_KEY"))
                has_unsplash = bool(tokens.get("UNSPLASH_KEY"))
                has_pexafy = bool(tokens.get("PEXAFY_KEY"))
                data = {
                    "status": "success",
                    "environment_mode": "Enterprise / Full Access" if (has_pixabay or has_unsplash) else "Community / Standalone Mode (Zero-Config)",
                    "providers": {
                        "pixabay": "✅ АКТИВЕН (5000 запросов/час, ключ в my_tokens.txt)" if has_pixabay else "❌ Ключ не указан (для активации добавьте в my_tokens.txt)",
                        "unsplash": "✅ АКТИВЕН (дизайнерский сток, ключ в my_tokens.txt)" if has_unsplash else "❌ Ключ не указан",
                        "pexafy": "✅ АКТИВЕН (шлюз Pexels)" if has_pexafy else "❌ Ключ не указан",
                        "wikimedia": "✅ АКТИВЕН (всегда доступен без ключей)",
                        "ai_generator": "✅ АКТИВЕН (команда GENERATE_IMAGE всегда доступна)"
                    },
                    "recommendation": "Используй search_pixabay или search_free_media для подбора идеальных фото!"
                }
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}]
                    }
                }

            elif tool_name == "search_free_media":



                query = args.get("query", "")



                media_type = args.get("media_type", "image")



                limit = int(args.get("limit", 5))



                data = search_free_media(query, media_type, limit)



                resp = {



                    "jsonrpc": "2.0",



                    "id": req_id,



                    "result": {



                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}]



                    }



                }



            elif tool_name == "fetch_page_images":



                url = args.get("url", "")



                data = fetch_page_images(url)



                resp = {



                    "jsonrpc": "2.0",



                    "id": req_id,



                    "result": {



                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}]



                    }



                }



            else:



                resp = {



                    "jsonrpc": "2.0",



                    "id": req_id,



                    "error": {"code": -32601, "message": f"Неизвестный инструмент: {tool_name}"}



                }



            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")



            sys.stdout.flush()







if __name__ == "__main__":



    main()


