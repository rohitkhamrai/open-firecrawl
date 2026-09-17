import asyncio
from engine.fetcher import fetch_page
from engine.markdown import clean_html_to_markdown

async def debug():
    url = "https://smartpuja.com/"
    html, meta = await fetch_page(url)
    
    with open("debug_html.txt", "w", encoding="utf-8") as f:
        f.write(html)
        
    markdown = clean_html_to_markdown(html)
    with open("debug_md.txt", "w", encoding="utf-8") as f:
        f.write(markdown)
        
    print(f"HTML len: {len(html)}")
    print(f"Markdown len: {len(markdown)}")

if __name__ == "__main__":
    asyncio.run(debug())
