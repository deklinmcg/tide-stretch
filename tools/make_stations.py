#!/usr/bin/env python3
"""Package pair_radio.py output into the final stations.json the site loads."""
import json, sys
from datetime import date

NAMES = {
 'US':'United States','CL':'Chile','FR':'France','ID':'Indonesia','GB':'United Kingdom','IT':'Italy',
 'SE':'Sweden','ES':'Spain','PE':'Peru','MX':'Mexico','TW':'Taiwan','NZ':'New Zealand','GR':'Greece',
 'BR':'Brazil','CO':'Colombia','AU':'Australia','PH':'Philippines','NO':'Norway','EC':'Ecuador',
 'CR':'Costa Rica','IE':'Ireland','JP':'Japan','IN':'India','CA':'Canada','PT':'Portugal','DE':'Germany',
 'DK':'Denmark','FI':'Finland','NL':'Netherlands','BE':'Belgium','PL':'Poland','RU':'Russia','EE':'Estonia',
 'LV':'Latvia','LT':'Lithuania','IS':'Iceland','TR':'Türkiye','CY':'Cyprus','MT':'Malta','HR':'Croatia',
 'SI':'Slovenia','ME':'Montenegro','AL':'Albania','UA':'Ukraine','BG':'Bulgaria','RO':'Romania',
 'GE':'Georgia','IL':'Israel','EG':'Egypt','MA':'Morocco','DZ':'Algeria','TN':'Tunisia','LY':'Libya',
 'SN':'Senegal','GH':'Ghana','NG':'Nigeria','CM':'Cameroon','GA':'Gabon','AO':'Angola','NA':'Namibia',
 'ZA':'South Africa','MZ':'Mozambique','TZ':'Tanzania','KE':'Kenya','SO':'Somalia','DJ':'Djibouti',
 'SD':'Sudan','SA':'Saudi Arabia','YE':'Yemen','OM':'Oman','AE':'United Arab Emirates','QA':'Qatar',
 'BH':'Bahrain','KW':'Kuwait','IQ':'Iraq','IR':'Iran','PK':'Pakistan','LK':'Sri Lanka','BD':'Bangladesh',
 'MM':'Myanmar','TH':'Thailand','MY':'Malaysia','SG':'Singapore','VN':'Vietnam','KH':'Cambodia',
 'CN':'China','KR':'South Korea','KP':'North Korea','HK':'Hong Kong','MO':'Macau','BN':'Brunei',
 'PG':'Papua New Guinea','SB':'Solomon Islands','VU':'Vanuatu','FJ':'Fiji','TO':'Tonga','WS':'Samoa',
 'KI':'Kiribati','TV':'Tuvalu','NR':'Nauru','MH':'Marshall Islands','FM':'Micronesia','PW':'Palau',
 'CK':'Cook Islands','NU':'Niue','AR':'Argentina','UY':'Uruguay','VE':'Venezuela','GY':'Guyana',
 'SR':'Suriname','PA':'Panama','NI':'Nicaragua','HN':'Honduras','GT':'Guatemala','BZ':'Belize',
 'SV':'El Salvador','CU':'Cuba','JM':'Jamaica','HT':'Haiti','DO':'Dominican Republic','PR':'Puerto Rico',
 'TT':'Trinidad and Tobago','BB':'Barbados','BS':'Bahamas','MU':'Mauritius','SC':'Seychelles',
 'MV':'Maldives','MG':'Madagascar','KM':'Comoros','CV':'Cape Verde','MNC':'Monaco','MC':'Monaco',
 'ANT':'Antarctica','ATA':'Antarctica','GL':'Greenland','FO':'Faroe Islands','GI':'Gibraltar',
 'BM':'Bermuda','KY':'Cayman Islands','AW':'Aruba','CW':'Curaçao','GP':'Guadeloupe','MQ':'Martinique',
 'GF':'French Guiana','RE':'Réunion','YT':'Mayotte','NC':'New Caledonia','PF':'French Polynesia',
 'WF':'Wallis and Futuna','TL':'Timor-Leste','MNG':'Mongolia','VUT':'Vanuatu',
}

src = sys.argv[1] if len(sys.argv) > 1 else 'stations.json'
dst = sys.argv[2] if len(sys.argv) > 2 else 'stations_final.json'
gauges = json.load(open(src))

# every gauge gets a radio: unpaired ones borrow the nearest paired gauge's
# station (with the true distance from THIS gauge to that transmitter's gauge
# as a floor — honest enough for the ticker)
import math
def hav(a, b, c, d):
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = math.radians(c - a), math.radians(d - b)
    x = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*6371*math.asin(math.sqrt(x))
paired_g = [g for g in gauges if g.get('radio')]
filled = 0
for g in gauges:
    if g.get('radio'): continue
    best, bd = None, 1e12
    for p in paired_g:
        d = hav(g['lat'], g['lon'], p['lat'], p['lon'])
        if d < bd: bd, best = d, p
    if best:
        r = dict(best['radio'])
        r['dist_km'] = round(bd + best['radio'].get('dist_km', 0))
        g['radio'] = r
        filled += 1
print(f'filled {filled} unpaired gauges from their nearest paired neighbour')
countries = {}
import re
for g in gauges:
    cc = g['country']
    countries[cc] = NAMES.get(cc, cc)
    g['lat'] = round(g['lat'], 3)
    g['lon'] = round(g['lon'], 3)
    # tidy IOC-style names: underscores, trailing country suffixes, stray spaces
    n = g['name'].replace('_', ' ')
    n = re.sub(r'\s+(' + re.escape(cc) + r'|[A-Z]{2})$', '', n) if len(n) > 4 else n
    g['name'] = re.sub(r'\s{2,}', ' ', n).strip()
final = {'generated': str(date.today()), 'countries': countries, 'stations': gauges}
json.dump(final, open(dst, 'w'), separators=(',', ':'), ensure_ascii=False)
paired = sum(1 for g in gauges if g.get('radio'))
import os
print(f'{dst}: {len(gauges)} gauges, {paired} paired, {len(countries)} countries, {os.path.getsize(dst)} bytes')
