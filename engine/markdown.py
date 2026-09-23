import html2text
from bs4 import BeautifulSoup
import re
import json

def clean_html_to_markdown(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    
    system_meta = []
    
    # 1. Extract OpenGraph and Twitter meta tags
    og_tags = []
    for meta in soup.find_all("meta"):
        prop = meta.get("property", "") or meta.get("name", "")
        if "og:description" in prop or "twitter:description" in prop or "og:title" in prop:
            content = meta.get("content", "").strip()
            if content:
                og_tags.append(f"{prop}: {content}")
                
    if og_tags:
        system_meta.append("Social Media Meta Data: " + " | ".join(og_tags))

    # 2. Extract JSON-LD script tags
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            data_str = json.dumps(data)
            if "interactionStatistic" in data_str or "userInteractionCount" in data_str:
                system_meta.append(f"Structured Data Metrics: {data_str[:1000]}")
        except Exception:
            pass

    # 3. DOM Fallback for generic rendered metrics (Likes, Views, Comments)
    dom_metrics = set()
    for el in soup.find_all(['span', 'div']):
        text = el.get_text(strip=True)
        if text and len(text) < 30:
            if re.match(r'^[\d.,]+[KMBkmb]?\s+(Likes?|Views?|Comments?|Shares?)$', text, re.IGNORECASE):
                dom_metrics.add(text)
    
    if dom_metrics:
        system_meta.append("Rendered DOM Metrics: " + ", ".join(dom_metrics))

    # Strip noisy elements
    for element in soup(["script", "style", "nav", "footer", "noscript", "header", "aside"]):
        element.decompose()
        
    cleaned_html = str(soup)
    
    # Configure html2text
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_tables = False
    h.ignore_emphasis = False
    h.body_width = 0 # No wrapping
    
    markdown = h.handle(cleaned_html)
    
    # Prepend SYSTEM META if found
    if system_meta:
        meta_block = "\n".join(system_meta)
        markdown = f"[SYSTEM META: Post Engagement Metrics]\n{meta_block}\n[END SYSTEM META]\n\n{markdown}"
    
    # Remove multiple blank lines
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    return markdown.strip()
