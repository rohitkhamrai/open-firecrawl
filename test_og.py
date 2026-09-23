import requests
from bs4 import BeautifulSoup

url = 'https://www.facebook.com/ddnewsjmu/posts/special-arrangements-planned-for-kashmiri-pandit-community-on-maha-shivratrireli/122184045764785126/'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')
for meta in soup.find_all('meta'):
    if meta.get('property') and 'og:' in meta.get('property'):
        print(f"{meta.get('property')}: {meta.get('content')}")
