#!/usr/bin/env python3
"""Add a genre to every paired radio in stations.json.

Bulk-downloads Radio Browser's station list per country, matches our baked
stream URLs (exact, then normalised), falls back to /byurl lookups, and
normalises RB's messy free-text tags into a dozen buckets.
Usage: fetch_genres.py <stations.json in/out>
"""
import json, re, sys, time, urllib.request, urllib.parse
from collections import Counter

RB = 'https://de1.api.radio-browser.info/json'
UA = {'User-Agent': 'TidalWave/1.0 (ambient sound art; deklin@gmail.com)'}

def get_json(url, timeout=40):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def norm_url(u):
    u = (u or '').strip().lower()
    u = re.sub(r'^https?://', '', u)
    u = re.sub(r'[/;?]+$', '', u)
    u = re.sub(r'\?_=\d+$', '', u)
    return u

# ordered: first match wins
BUCKETS = [
 ('news & talk',      r'news|talk|information|current affairs|speech|nachrichten|noticias|actualit'),
 ('sport',            r'\bsport|football|gaa\b|racing'),
 ('classical',        r'classical|klassik|opera|symphony|orchest'),
 ('jazz & blues',     r'jazz|blues|swing'),
 ('dance & electronic', r'dance|electro|house|techno|trance|edm|drum.?n.?bass|dnb|club'),
 ('rock & alternative', r'rock|metal|punk|alternative|indie|grunge'),
 ('hip-hop & rnb',    r'hip.?hop|rap|r.?n.?b|rnb|urban'),
 ('country & folk',   r'country|folk|americana|bluegrass|celtic|trad'),
 ('oldies & gold',    r'oldies|gold|60s|70s|80s|90s|retro|classic hits|nostal'),
 ('religious',        r'christian|gospel|catholic|religio|islam|quran|worship'),
 ('world & culture',  r'world|latin|salsa|reggae|afro|bollywood|arab|ranchera|cumbia|mariachi|schlager|volksmusik|gaeltacht|irish language'),
 ('chill & ambient',  r'chill|lounge|ambient|relax|easy listening|smooth'),
 ('pop & hits',       r'pop|hits|top ?40|hot ?ac|contemporary|charts|adult contemporary'),
 ('community',        r'community|local|college|university|student|hospital|campus'),
]
def bucket(tags, name):
    t = (tags or '').lower() + ' ' + (name or '').lower()
    for g, pat in BUCKETS:
        if re.search(pat, t):
            return g
    return 'local radio'

path = sys.argv[1]
data = json.load(open(path))
stations = data['stations']

# distinct radio URLs per country (match within-country first, then global)
by_cc = {}
for g in stations:
    r = g.get('radio')
    if r: by_cc.setdefault(g['country'], set()).add(r['url'])

url_tags = {}          # norm_url -> (tags, rb_name)
ccs = sorted(by_cc)
for i, cc in enumerate(ccs):
    if len(cc) != 2: continue
    try:
        d = get_json(RB + '/stations/search?countrycode=' + cc + '&hidebroken=true&limit=10000')
    except Exception as e:
        print(cc, 'bulk failed:', e); continue
    for s in d:
        for u in (s.get('url_resolved'), s.get('url')):
            k = norm_url(u)
            if k and k not in url_tags:
                url_tags[k] = (s.get('tags', ''), s.get('name', ''))
    print(f'{i+1}/{len(ccs)} {cc}: rb={len(d)}', flush=True)
    time.sleep(0.15)

matched = fallback = 0
misses = set()
for g in stations:
    r = g.get('radio')
    if not r: continue
    k = norm_url(r['url'])
    hit = url_tags.get(k)
    if hit:
        r['genre'] = bucket(hit[0], r['name']); matched += 1
    else:
        misses.add((k, r['url']))
# fallback: individual byurl lookups for distinct misses
miss_map = {}
for i, (k, u) in enumerate(sorted(misses)):
    try:
        d = get_json(RB + '/stations/byurl?url=' + urllib.parse.quote(u, safe=''))
        if d: miss_map[k] = (d[0].get('tags', ''), d[0].get('name', ''))
    except Exception:
        pass
    time.sleep(0.2)
for g in stations:
    r = g.get('radio')
    if not r or 'genre' in r: continue
    hit = miss_map.get(norm_url(r['url']))
    r['genre'] = bucket(hit[0] if hit else '', r['name'])
    if hit: fallback += 1

json.dump(data, open(path, 'w'), separators=(',', ':'), ensure_ascii=False)
cnt = Counter(g['radio']['genre'] for g in stations if g.get('radio'))
print(f'matched bulk={matched} fallback={fallback} of {sum(1 for g in stations if g.get("radio"))}')
for g_, n in cnt.most_common(): print(f'  {n:5d} {g_}')
