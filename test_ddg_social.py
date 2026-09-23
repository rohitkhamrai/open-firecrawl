from ddgs import DDGS
keyword = 'Sri Sathyanarayana Swamy Pooja'
with DDGS() as ddgs:
    for res in ddgs.text(f'"{keyword}" site:instagram.com "likes"', max_results=5):
        print(res.get('href'))
        print(res.get('body'))
        print('---')
