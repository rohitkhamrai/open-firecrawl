import html2text
from bs4 import BeautifulSoup
import re

def clean_html_to_markdown(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    
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
    
    # Remove multiple blank lines
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    return markdown.strip()
