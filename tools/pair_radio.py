#!/usr/bin/env python3
"""Pair every live tide gauge with its nearest browser-usable LOCAL radio stream.

Usable = https + CORS (ACAO * or origin echo) + codec we can decode in the
browser (icecast MP3, icecast ADTS-AAC, or HLS) + actually sends bytes.

Output: stations.json — gauges with radio {name, url, kind, dist_km, home}.
Stream test results are cached in stream_cache.json across runs.
"""
import json, math, os, re, ssl, sys, threading, time
import urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

ORIGIN = 'https://deklinmcg.github.io'
UA = 'Mozilla/5.0 (TideStretch/1.0 ambient sound art; deklin@gmail.com)'
RB = 'https://de1.api.radio-browser.info/json/stations/search'

# --- national / non-local brands to skip (name regex, case-insensitive) ---
NATIONAL = re.compile(r'''
  ^(bbc\ radio\ \d|bbc\ 6\ ?music|bbc\ world|bbc\ asian)
 |^(rt[eé]|today\ fm|newstalk|off\ the\ ball)\b
 |^(classic\ fm|talksport|absolute\ radio|lbc\b|virgin\ radio|times\ radio|gb\ news)
 |^(npr\b|c-?span)
 |^(france\ (inter|info|culture|musique)|rtl\b|europe\ ?1)\b
 |^(rai\ radio|radio\ nacional|rne\b|cadena\ ser$|cope$|onda\ cero$)
 |^(deutschlandfunk|zdf|ard\b)
 |^(nrk\b|sveriges\ radio|sr\ p\d|yle\b|dr\ p\d|radio\ norge)\b
 |^(air\b|all\ india\ radio)
 |^(abc\ (radio\ national|news|classic|triple\ j)|triple\ j)\b
 |^(rnz|radio\ new\ zealand)\b
 |^(cbc\ radio)\b
 |\bnational\b
''', re.I | re.X)

# hand overrides: gauge test -> forced radio
def override_for(g):
    # Donegal: Highland Radio, Letterkenny — the original piece
    if g['country'] == 'IE' and g['lat'] > 54.4 and g['lon'] < -7.0:
        return dict(name='Highland Radio', kind='hls', dist_km=0,
                    url='https://playerservices.streamtheworld.com/api/livestream-redirect/HIGHLAND_RADIOAAC.m3u8',
                    home='https://www.highlandradio.com')
    return None

def get(url, timeout=20, origin=False):
    h = {'User-Agent': UA}
    if origin: h['Origin'] = ORIGIN
    req = urllib.request.Request(url, headers=h)
    return urllib.request.urlopen(req, timeout=timeout)

def haversine(a, b, c, d):
    R = 6371
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = math.radians(c - a), math.radians(d - b)
    x = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(x))

# --- stream testing with cache ---
cache_lock = threading.Lock()
CACHE_FILE = 'stream_cache.json'
cache = json.load(open(CACHE_FILE)) if os.path.exists(CACHE_FILE) else {}

def test_stream(url):
    """Return kind ('mp3'|'aac'|'hls') if usable, else None. Cached."""
    with cache_lock:
        if url in cache: return cache[url]
    kind = _test_stream(url)
    with cache_lock:
        cache[url] = kind
    return kind

def _test_stream(url):
    if not url.startswith('https://'): return None
    try:
        r = get(url, timeout=12, origin=True)
        acao = r.headers.get('Access-Control-Allow-Origin', '')
        ct = (r.headers.get('Content-Type') or '').lower()
        if acao not in ('*', ORIGIN): r.close(); return None
        if 'mpegurl' in ct or r.url.split('?')[0].endswith('.m3u8'):
            body = r.read(20000).decode('utf-8', 'replace'); r.close()
            base = r.url[:r.url.rfind('/') + 1]
            lines = [l.strip() for l in body.split('\n') if l.strip() and not l.startswith('#')]
            if not lines: return None
            child = lines[0] if re.match(r'^https?:', lines[0]) else base + lines[0]
            # if master playlist, resolve one level down
            if child.split('?')[0].endswith('.m3u8'):
                r2 = get(child, timeout=12, origin=True)
                if r2.headers.get('Access-Control-Allow-Origin', '') not in ('*', ORIGIN): r2.close(); return None
                body2 = r2.read(20000).decode('utf-8', 'replace'); r2.close()
                base2 = r2.url[:r2.url.rfind('/') + 1]
                segs = [l.strip() for l in body2.split('\n') if l.strip() and not l.startswith('#')]
                if not segs: return None
                seg = segs[-1] if re.match(r'^https?:', segs[-1]) else base2 + segs[-1]
            else:
                seg = child
            if re.search(r'\.(ts|mp4|m4s)(\?|$)', seg): return None   # only raw AAC/MP3 segments supported
            r3 = get(seg, timeout=12, origin=True)
            ok = r3.headers.get('Access-Control-Allow-Origin', '') in ('*', ORIGIN) and len(r3.read(4096)) > 0
            r3.close()
            return 'hls' if ok else None
        data = r.read(8192); r.close()
        if not data: return None
        if 'audio/mpeg' in ct or 'audio/mp3' in ct: return 'mp3'
        if 'aac' in ct: return 'aac'
        return None
    except Exception:
        return None

# --- radio browser candidates around a point ---
rb_lock = threading.Lock()
def rb_query(params):
    url = RB + '?' + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            with rb_lock:                      # be polite: one RB request at a time
                r = get(url, timeout=25)
                d = json.loads(r.read()); r.close()
                time.sleep(0.15)
            return d
        except Exception:
            time.sleep(2 * (attempt + 1))
    return []

def candidates(lat, lon):
    seen, out = set(), []
    for dist in (150_000, 600_000, 2_500_000):
        d = rb_query(dict(geo_lat=lat, geo_long=lon, geo_distance=dist,
                          order='distance', hidebroken='true',
                          has_geo_info='true', limit=120))
        for s in d:
            u = (s.get('url_resolved') or s.get('url') or '').strip()
            name = (s.get('name') or '').strip()
            if not u or not name: continue
            key = u
            if key in seen: continue
            seen.add(key)
            if not u.startswith('https://'): continue
            if NATIONAL.search(name): continue
            try:
                slat, slon = float(s['geo_lat']), float(s['geo_long'])
            except (TypeError, ValueError):
                continue
            out.append(dict(name=name, url=u, home=(s.get('homepage') or '')[:200],
                            votes=int(s.get('votes') or 0),
                            dist=haversine(lat, lon, slat, slon)))
        if len(out) >= 25: break
    out.sort(key=lambda s: s['dist'])
    return out

def pair(g):
    ov = override_for(g)
    if ov:
        g['radio'] = ov
        return g
    # Test in distance order; once one works, keep testing everything within
    # +40 km of it, then pick the most-voted-for of the usable set — a real
    # local FM station beats a hobby web stream tagged at a nearby village.
    usable = []
    for c in candidates(g['lat'], g['lon'])[:40]:
        if usable and c['dist'] > usable[0]['dist'] + 40: break
        kind = test_stream(c['url'])
        if kind:
            c['kind'] = kind
            usable.append(c)
    if usable:
        best = max(usable, key=lambda c: (c['votes'], -c['dist']))
        g['radio'] = dict(name=best['name'], url=best['url'], kind=best['kind'],
                          dist_km=round(best['dist']), home=best['home'])
    else:
        g['radio'] = None
    return g

def main():
    gauges = json.load(open('live_stations.json'))
    # fix Japan code from probe run
    for g in gauges:
        if g['country'] == 'JAP': g['country'] = 'JP'
    out, done = [], 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(pair, g): g for g in gauges}
        for f in as_completed(futs):
            out.append(f.result())
            done += 1
            if done % 25 == 0:
                paired = sum(1 for g in out if g.get('radio'))
                print(f'{done}/{len(gauges)}  paired={paired}  cache={len(cache)}  {time.time()-t0:.0f}s', flush=True)
                with cache_lock:
                    json.dump(cache, open(CACHE_FILE, 'w'))
    with cache_lock:
        json.dump(cache, open(CACHE_FILE, 'w'))
    # stable order: country then name
    out.sort(key=lambda g: (g['country'], g['name']))
    json.dump(out, open('stations.json', 'w'), separators=(',', ':'))
    paired = sum(1 for g in out if g.get('radio'))
    print(f'DONE: {paired}/{len(out)} gauges paired with a working local stream')

if __name__ == '__main__':
    main()
