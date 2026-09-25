import asyncio
from auto_browser_client import AutoBrowserClient

async def test():
    url = "https://www.instagram.com/reel/DdLYGtzR1zZ/"
    print(f"Testing auto-browser on: {url}")
    
    base_url = "http://192.168.0.134:35095"
    async with AutoBrowserClient(base_url, token="super-secret-token-for-auto-browser-123") as client:
        session = await client.async_create_session(
            start_url=url, 
            auth_profile="insta"
        )
        session_id = session["id"]
        
        try:
            await asyncio.sleep(5)
            obs = await client.async_observe(session_id, preset="text")
            
            text_content = ""
            if 'text' in obs:
                text_content = obs['text']
            elif 'elements' in obs:
                text_content = " ".join([el.get('text', '') for el in obs['elements'] if 'text' in el])
            
            with open("debug_output.txt", "w", encoding="utf-8") as f:
                f.write(text_content)
                
            print("Successfully wrote output to debug_output.txt")
            
            await client.async_close_session(session_id)
        except Exception as e:
            await client.async_close_session(session_id)
            print(e)

if __name__ == "__main__":
    asyncio.run(test())
