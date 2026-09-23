import requests
from bs4 import BeautifulSoup

url = 'https://www.instagram.com/p/CwY9-Ruvq-w/'
headers = {'User-Agent': 'WhatsApp/2.21.12.21 A'}
r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')
for meta in soup.find_all('meta'):
    if meta.get('property') and 'og:' in meta.get('property'):
        print(f"{meta.get('property')}: {meta.get('content')}")
