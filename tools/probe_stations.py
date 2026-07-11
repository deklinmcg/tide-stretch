#!/usr/bin/env python3
"""Build the global list of LIVE tide gauges for Tide Stretch.

Sources:
  - IOC sea level monitoring (global) — probe each station for fresh data
  - Marine Institute ERDDAP (Ireland)
  - Environment Agency (UK)
  - Queensland Government storm tide (Australia)

Output: live_stations.json  [{src, id, name, country, lat, lon}]
IOC stations in GRB/EIR are skipped (national feeds are denser there).
IOC stations within ~8 km of a QLD gauge are skipped.
"""
import json, math, sys, time
import urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

UA = {'User-Agent': 'TideStretch/1.0 (ambient sound art; deklin@gmail.com)'}

def get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def get_json(url, timeout=25):
    return json.loads(get(url, timeout))

# IOC country code -> ISO2 + display name (IOC uses odd codes)
IOC_CC = {
 'USA':('US','United States'),'CHL':('CL','Chile'),'FRA':('FR','France'),'IDN':('ID','Indonesia'),
 'GRB':('GB','United Kingdom'),'ITA':('IT','Italy'),'SVE':('SE','Sweden'),'ESP':('ES','Spain'),
 'PER':('PE','Peru'),'MEX':('MX','Mexico'),'TWN':('TW','Taiwan'),'NWZ':('NZ','New Zealand'),
 'HEL':('GR','Greece'),'BRA':('BR','Brazil'),'COL':('CO','Colombia'),'AUS':('AU','Australia'),
 'FIL':('PH','Philippines'),'NOR':('NO','Norway'),'ECU':('EC','Ecuador'),'CRC':('CR','Costa Rica'),
 'EIR':('IE','Ireland'),'JPN':('JP','Japan'),'IND':('IN','India'),'CAN':('CA','Canada'),
 'POR':('PT','Portugal'),'GER':('DE','Germany'),'DMK':('DK','Denmark'),'FIN':('FI','Finland'),
 'NET':('NL','Netherlands'),'BEL':('BE','Belgium'),'POL':('PL','Poland'),'RUS':('RU','Russia'),
 'EST':('EE','Estonia'),'LAT':('LV','Latvia'),'LIT':('LT','Lithuania'),'ICE':('IS','Iceland'),
 'TUR':('TR','Turkey'),'CYP':('CY','Cyprus'),'MLT':('MT','Malta'),'CRO':('HR','Croatia'),
 'SLO':('SI','Slovenia'),'MNE':('ME','Montenegro'),'ALB':('AL','Albania'),'UKR':('UA','Ukraine'),
 'BUL':('BG','Bulgaria'),'ROM':('RO','Romania'),'GEO':('GE','Georgia'),'ISR':('IL','Israel'),
 'EGY':('EG','Egypt'),'MOR':('MA','Morocco'),'ALG':('DZ','Algeria'),'TUN':('TN','Tunisia'),
 'LBA':('LY','Libya'),'SEN':('SN','Senegal'),'GHA':('GH','Ghana'),'NGR':('NG','Nigeria'),
 'CMR':('CM','Cameroon'),'GAB':('GA','Gabon'),'ANG':('AO','Angola'),'NAM':('NA','Namibia'),
 'SAF':('ZA','South Africa'),'MOZ':('MZ','Mozambique'),'TAN':('TZ','Tanzania'),'KEN':('KE','Kenya'),
 'SOM':('SO','Somalia'),'DJI':('DJ','Djibouti'),'SUD':('SD','Sudan'),'SAU':('SA','Saudi Arabia'),
 'YEM':('YE','Yemen'),'OMA':('OM','Oman'),'UAE':('AE','United Arab Emirates'),'QAT':('QA','Qatar'),
 'BHR':('BH','Bahrain'),'KUW':('KW','Kuwait'),'IRQ':('IQ','Iraq'),'IRN':('IR','Iran'),
 'PAK':('PK','Pakistan'),'SRL':('LK','Sri Lanka'),'BGD':('BD','Bangladesh'),'MYA':('MM','Myanmar'),
 'THA':('TH','Thailand'),'MAL':('MY','Malaysia'),'SIN':('SG','Singapore'),'VTN':('VN','Vietnam'),
 'CAM':('KH','Cambodia'),'CHN':('CN','China'),'KOR':('KR','South Korea'),'PRK':('KP','North Korea'),
 'HKG':('HK','Hong Kong'),'MAC':('MO','Macau'),'BRU':('BN','Brunei'),'PNG':('PG','Papua New Guinea'),
 'SOL':('SB','Solomon Islands'),'VAN':('VU','Vanuatu'),'FIJ':('FJ','Fiji'),'TON':('TO','Tonga'),
 'SAM':('WS','Samoa'),'KIR':('KI','Kiribati'),'TUV':('TV','Tuvalu'),'NAU':('NR','Nauru'),
 'MSH':('MH','Marshall Islands'),'FSM':('FM','Micronesia'),'PAL':('PW','Palau'),'COO':('CK','Cook Islands'),
 'NIU':('NU','Niue'),'ARG':('AR','Argentina'),'URU':('UY','Uruguay'),'VEN':('VE','Venezuela'),
 'GUY':('GY','Guyana'),'SUR':('SR','Suriname'),'PAN':('PA','Panama'),'NIC':('NI','Nicaragua'),
 'HON':('HN','Honduras'),'GUA':('GT','Guatemala'),'BLZ':('BZ','Belize'),'SLV':('SV','El Salvador'),
 'CUB':('CU','Cuba'),'JAM':('JM','Jamaica'),'HAI':('HT','Haiti'),'DOM':('DO','Dominican Republic'),
 'PUR':('PR','Puerto Rico'),'TRI':('TT','Trinidad and Tobago'),'BAR':('BB','Barbados'),
 'BAH':('BS','Bahamas'),'MAU':('MU','Mauritius'),'SEY':('SC','Seychelles'),'MDV':('MV','Maldives'),
 'MAD':('MG','Madagascar'),'COM':('KM','Comoros'),'CPV':('CV','Cape Verde'),
}

def haversine(a, b, c, d):
    R = 6371
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = math.radians(c - a), math.radians(d - b)
    x = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(x))

out = []

# ---------- Ireland: Marine Institute ----------
print('Ireland (Marine Institute)…', flush=True)
since = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
url = ('https://erddap.marine.ie/erddap/tabledap/IrishNationalTideGaugeNetwork.json'
       '?station_id,latitude,longitude,time&time%3E=' + since)
try:
    d = get_json(url)
    seen = {}
    for sid, lat, lon, t in d['table']['rows']:
        seen[sid] = (float(lat), float(lon))
    for sid, (lat, lon) in sorted(seen.items()):
        out.append(dict(src='ie', id=sid, name=sid, country='IE', lat=lat, lon=lon))
    print(f'  {len(seen)} live')
except Exception as e:
    print('  FAILED:', e); sys.exit(1)

# ---------- UK: Environment Agency ----------
print('UK (Environment Agency)…', flush=True)
d = get_json('https://environment.data.gov.uk/flood-monitoring/id/stations?parameter=level&qualifier=Tidal+Level&_limit=500')
uk = []
for s in d.get('items', []):
    if not s.get('notation') or not s.get('label'): continue
    lat, lon = s.get('lat'), s.get('long')
    if lat is None or lon is None: continue
    label = s['label'] if isinstance(s['label'], str) else s['label'][0]
    uk.append(dict(src='uk', id=s['notation'], name=label, country='GB', lat=float(lat), lon=float(lon)))
# dedupe EA duplicates by id
uk = list({s['id']: s for s in uk}.values())
print(f'  {len(uk)} stations (freshness probed at runtime not needed — EA list is active gauges)')
out += uk

# ---------- Australia: Queensland ----------
print('Queensland…', flush=True)
QLD = 'https://www.data.qld.gov.au/api/3/action'
QLD_RES = '7afe7233-fae0-4024-bc98-3a72f05675bd'
sql = f'SELECT DISTINCT "Site", "Latitude", "Longitude" FROM "{QLD_RES}"'
try:
    d = get_json(QLD + '/datastore_search_sql?sql=' + urllib.parse.quote(sql))
    recs = d['result']['records']
except Exception as e:
    print('  no lat/lon via SQL:', e); recs = []
qld = []
for r in recs:
    try:
        lat, lon = float(r['Latitude']), float(r['Longitude'])
    except (TypeError, ValueError, KeyError):
        continue
    name = r['Site'][0].upper() + r['Site'][1:]
    qld.append(dict(src='au', id=r['Site'], name=name, country='AU', lat=lat, lon=lon))
print(f'  {len(qld)} sites')
out += qld

# ---------- Global: IOC ----------
print('IOC station list…', flush=True)
d = get_json('https://www.ioc-sealevelmonitoring.org/service.php?query=stationlist&showall=a')
stations = {}
for s in d:
    if s.get('status') != 1: continue
    if s['country'] in ('GRB', 'EIR'):  # covered by denser national feeds
        continue
    code = s['Code']
    if code not in stations:
        stations[code] = s
print(f'  {len(stations)} unique candidates; probing for fresh data…', flush=True)

def probe(code):
    try:
        d = get_json(f'https://www.ioc-sealevelmonitoring.org/service.php?query=data&code={code}&period=0.25', timeout=20)
        if not d: return None
        last = max(r['stime'] for r in d if isinstance(r.get('slevel'), (int, float)))
        age = datetime.now(timezone.utc) - datetime.strptime(last, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        if age > timedelta(hours=2): return None
        vals = [r['slevel'] for r in d if isinstance(r.get('slevel'), (int, float))]
        if len(vals) < 5: return None
        return code
    except Exception:
        return None

live = []
done = 0
with ThreadPoolExecutor(max_workers=24) as ex:
    futs = {ex.submit(probe, c): c for c in stations}
    for f in as_completed(futs):
        done += 1
        if done % 100 == 0: print(f'  …{done}/{len(stations)}', flush=True)
        r = f.result()
        if r: live.append(r)
print(f'  {len(live)} IOC stations live')

for code in sorted(live):
    s = stations[code]
    iso, cname = IOC_CC.get(s['country'], (s['country'], s['country']))
    lat, lon = float(s['Lat']), float(s['Lon'])
    # skip if a QLD gauge is within 8 km
    if any(haversine(lat, lon, q['lat'], q['lon']) < 8 for q in qld):
        continue
    out.append(dict(src='ioc', id=code, name=s['Location'], country=iso, lat=lat, lon=lon))

with open('live_stations.json', 'w') as f:
    json.dump(out, f, indent=1)
from collections import Counter
cc = Counter(s['country'] for s in out)
print(f'TOTAL {len(out)} stations in {len(cc)} countries')
print(cc.most_common(15))
