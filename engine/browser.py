import asyncio
from auto_browser_client import AutoBrowserClient
import config
from typing import Dict, Any

async def get_social_metrics(url: str) -> Dict[str, str]:
    """
    Connects to the remote auto-browser instance, navigates to the URL,
    and extracts the text from the page to find Likes and Views.
    """
    # Assuming auto-browser runs on the same host as Postgres (192.168.0.134:35095)
    base_url = "http://192.168.0.134:35095"
    
    try:
        async with AutoBrowserClient(base_url, token="super-secret-token-for-auto-browser-123") as client:
            # Create a session utilizing an auth profile if available
            session = await client.async_create_session(
                start_url=url, 
                auth_profile="insta" # The user saved the profile as "insta"
            )
            session_id = session["id"]
            
            try:
                # Give the page a moment to load dynamic content
                await asyncio.sleep(3)
                
                # Get text excerpt since auto-browser doesn't support 'html' preset natively
                obs = await client.async_observe(session_id, preset="text")
                
                html_content = ""
                if 'text_excerpt' in obs:
                    html_content = obs['text_excerpt']
                    
                # Close the session
                await client.async_close_session(session_id)
                
                return {"raw_text": html_content}
                
            except Exception as e:
                # Make sure to close session on error
                await client.async_close_session(session_id)
                print(f"Error observing page: {e}")
                return {"raw_text": ""}
                
    except Exception as e:
        print(f"Failed to connect to auto-browser at {base_url}: {e}")
        return {"raw_text": ""}
