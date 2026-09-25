import asyncio
import sys
import io
from engine.browser import get_social_metrics
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def test():
    metrics = await get_social_metrics('https://www.instagram.com/reel/DdLYGtzR1zZ/')
    text = metrics.get('raw_text', '')
    
    likes_match = re.search(r'content="([^"]*?([\d,\.]+[KkMmBb]?)\s*(likes|Likes|Plays|plays)[^"]*?)"', text)
    if likes_match:
        print('LIKES:', likes_match.group(2))
    else:
        fallback = re.search(r'([\d,\.]+[KkMmBb]?)\s*(likes|Likes)', text)
        print('FALLBACK LIKES:', fallback.group(1) if fallback else None)
        
    views_match = re.search(r'content="([^"]*?([\d,\.]+[KkMmBb]?)\s*(views|Views)[^"]*?)"', text)
    if views_match:
        print('VIEWS:', views_match.group(2))
    else:
        fallback_views = re.search(r'([\d,\.]+[KkMmBb]?)\s*(views|Views)', text)
        print('FALLBACK VIEWS:', fallback_views.group(1) if fallback_views else None)

asyncio.run(test())
