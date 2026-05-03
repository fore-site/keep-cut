import requests
import sys
import os

# Add parent directory to path if running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

anime_list = requests.get("http://localhost:8000/items?edition=anime&limit=8").json()
anime_urls = [item["image_url"] for item in anime_list]

print(anime_urls)

url1 = "https://image.tmdb.org/t/p/w342/in1R2dDc421JxsoRWaIIAqVI2KE.jpg"
url2 = "https://image.tmdb.org/t/p/w342/4tblBrslcKSifMVZ3TmtT2ukMor.jpg"
url3 = "https://image.tmdb.org/t/p/w342/3PFsEuAiyLkWsP4GG6dIV37Q6gu.jpg"
url4 = "https://image.tmdb.org/t/p/w342/uOOtwVbSr4QDjAGIifLDwpb2Pdl.jpg"
url5 = "https://image.tmdb.org/t/p/w342/vUUqzWa2LnHIVqkaKVlVGkVcZIW.jpg"
url6 = "https://image.tmdb.org/t/p/w342/ztkUQFLlC19CCMYHW9o1zWhJRNq.jpg"
url7 = "https://image.tmdb.org/t/p/w342/2koX1xLkpTQM4IZebYvKysFW1Nh.jpg"
url8 = "https://image.tmdb.org/t/p/w342/yZevl2vHQgmosfwUdVNzviIfaWS.jpg"

url9 = anime_urls[0]
url10 = anime_urls[1]
url11 = anime_urls[2]
url12 = anime_urls[3]
url13 = anime_urls[4]
url14 = anime_urls[5]
url15 = anime_urls[6]
url16 = anime_urls[7]

payload = {
  "edition": "tv_shows",
  "mode": "blind",
  "keep_images": [url9, url10, url11, url12],
  "cut_images":  [url13, url14, url15, url16],
  "width": 1200
}

r = requests.post("http://localhost:8000/images/results-card", json=payload)
r.raise_for_status()
open("results.png", "wb").write(r.content)
