import asyncio
import json
from engine.fetcher import fetch_page
from engine.markdown import clean_html_to_markdown
from engine.extractor import extract_schema

async def main():
    # Example temple/pooja booking website
    url = "https://smartpuja.com/" 
    
    print(f"Scraping {url} using StealthyFetcher...")
    html, metadata = await fetch_page(url)
    
    print(f"Raw HTML length: {len(html)}")
    
    print("Converting HTML to lean Markdown...")
    markdown = clean_html_to_markdown(html)
    
    print(f"Markdown length: {len(markdown)} characters")
    print(f"Markdown preview: {markdown[:500]}\n...")
    
    schema = {
      "type": "object",
      "properties": {
        "temple_name": {"type": "string"},
        "poojas": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "name": {"type": "string"},
              "details": {"type": "string"},
              "price": {"type": "string"}
            }
          }
        },
        "rituals": {
          "type": "array",
          "items": {"type": "string"}
        },
        "products_sold": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "name": {"type": "string"},
              "price": {"type": "string"}
            }
          }
        }
      }
    }
    
    print("Extracting requested structured schema using Groq & OpenRouter...")
    json_data = await extract_schema(markdown, schema)
    
    with open("debug_md.txt", "w", encoding="utf-8") as f:
        f.write(markdown)
        
    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)
    
    print("\n================ EXTRACTION RESULT ================")
    print(json.dumps(json_data, indent=2))
    print("===================================================\n")
    print("Data saved to debug_md.txt and output.json")

if __name__ == "__main__":
    asyncio.run(main())
