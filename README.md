# Tidal Wave

**The world's local radio, slowed down by the world's sea.**

A browser sound piece. A retro pixel map of the world glows wherever a live tide gauge is reporting — about 1,300 of them in ~90 countries. Tap a dot and its nearest *local* radio station starts playing, time-stretched in real time with the [paulstretch](https://github.com/paulnasca/paulstretch_python) algorithm, the amount of stretch driven by that gauge's actual water level.

Tide out → the radio smears into an ambient drone (up to 30× slower).
Tide comes in → the voices slowly gather themselves back towards normal speed.

The stretched audio always lags behind real time (that's what stretching a live stream means) — you're listening to the recent past, slowed by the sea. A LIVE ticker along the bottom shows what's playing: station, gauge, water level, stretch.

The original piece — Highland Radio (Letterkenny) on the Donegal tide — is still the heart of it: every Donegal gauge plays Highland Radio.

**[▶ Listen](https://deklinmcg.github.io/tide-stretch/)**

## Use it

1. Tap anywhere glowing on the map to zoom into that coastline
2. Tap a tide-gauge dot — the local station tunes in (~10 s of buffering) and drifts on that tide
3. Leave it running — the change happens on tidal time
4. **● REC** (in the ticker) samples up to 60 s of whatever you're hearing and downloads it as a WAV — drop it straight into a sampler
5. **☰** (top right) opens the sidebar: filter the world's gauges by genre, continent, country, or where the tide is right now; play the effects (an XY pad with assignable axes — lowpass, highpass, reverb, delay, drive); and use the lab — stretch any audio file by hand or on a simulated tide

## How it works

One HTML file + two JSON data files, no server, no build, no tracking:

- **Paulstretch in an AudioWorklet** — windows of sound are FFT'd, their phases randomised, inverse-FFT'd and overlap-added. Stretch ratio is a live parameter that glides on a ~15 s time constant. The worklet keeps a 5-minute rolling buffer of the incoming stream.
- **Radio streams** — three transports, all decoded in the browser: HLS playlists of AAC segments, icecast MP3, and icecast ADTS-AAC (the icecast streams are chunk-decoded on frame boundaries, with the previous chunk's tail prepended as decoder warm-up so the seams vanish inside the smear).
- **Tide data** — global: [IOC Sea Level Monitoring](https://www.ioc-sealevelmonitoring.org); UK: [Environment Agency](https://environment.data.gov.uk/flood-monitoring/doc/reference); Ireland: [Marine Institute ERDDAP](https://erddap.marine.ie); Australia: [Queensland Government](https://www.data.qld.gov.au/dataset/coastal-data-system-near-real-time-storm-tide-data). Each gauge's last 25 hours self-calibrate its high/low range (2nd–98th percentile); it re-polls every 5 minutes.
- **Genres** — each station's Radio Browser tags are normalised into ~15 buckets (news & talk, dance & electronic, oldies & gold…) by `tools/fetch_genres.py` and baked into `stations.json`. The tide filter reads gauges live: a few at a time, nearest to your view, cached 20 minutes.
- **Radio pairing** (`stations.json`) — built offline by `tools/pair_radio.py`: for every live gauge it queries the [Radio Browser](https://www.radio-browser.info) community directory by distance, filters out national networks, tests each candidate stream for HTTPS + CORS + a decodable codec, and keeps the nearest *real* station (most-voted within ~40 km of the nearest working one, so a proper local FM station beats a hobby web stream tagged at a nearby village). Gauges with no reachable stream fall back to synthesised wave noise.
- **The map** — Natural Earth 110 m coastlines scanline-rasterised onto a ~320-px-wide logical grid, drawn with a fixed 17-colour washed palette and 4×4 Bayer ordered dithering over a procedurally animated ocean. The sea's wave size follows the tide; its animation speed follows the current stretch.

## Rebuilding the station list

```
cd tools
python3 probe_stations.py     # finds every gauge that reported in the last 2 h
python3 pair_radio.py         # pairs each with a working local stream (~20 min, cached)
python3 make_stations.py stations.json ../stations.json
```

## Credits

- Paulstretch algorithm by Nasca Octavian Paul
- Tide data © IOC/UNESCO (VLIZ), Environment Agency, Marine Institute, Queensland Government — open data
- Station directory: Radio Browser community database
- Coastlines: Natural Earth (public domain)
- Radio audio plays directly from each station's public stream in your own browser; nothing is recorded or rebroadcast
