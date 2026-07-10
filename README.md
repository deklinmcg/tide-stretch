# Tide Stretch

**Live radio, slowed down by the actual sea.**

A browser sound piece: [Highland Radio](https://www.highlandradio.com/) (Letterkenny, Co. Donegal) is time-stretched in real time using the [paulstretch](https://github.com/paulnasca/paulstretch_python) algorithm, and the amount of stretch is driven by a real tide gauge — by default Killybegs Port, but you can pick any of ~270 stations around Ireland and the UK.

Tide out → the radio smears into an ambient drone (up to 30× slower).
Tide comes in → the voices slowly gather themselves back towards normal speed.

The stretched audio always lags behind real time (that's what stretching a live stream means) — you're listening to the recent past, slowed by the sea.

**[▶ Listen](https://deklinmcg.github.io/tide-stretch/)**

## Use it

1. Click **📻 Highland Radio live** (or drop in any audio file)
2. Press **▶ Play**
3. Switch **Live tide: on** and pick a station
4. Leave it running — the drift happens on tidal time

## How it works

One HTML file, no server, no build, no tracking:

- **Paulstretch in an AudioWorklet** — windows of sound are FFT'd, their phases randomised, inverse-FFT'd and overlap-added. Stretch ratio is a live parameter that glides.
- **Radio** — an `<audio>` element streams the station and its output is routed into the worklet, which keeps a 5-minute rolling buffer.
- **Tide data** — UK: [Environment Agency flood-monitoring API](https://environment.data.gov.uk/flood-monitoring/doc/reference); Ireland: [Marine Institute ERDDAP](https://erddap.marine.ie) (Irish National Tide Gauge Network). The station's last 25 hours self-calibrate its high/low range; it re-polls every 5 minutes.

## Credits

- Paulstretch algorithm by Nasca Octavian Paul
- Tide data © Environment Agency / Marine Institute, used under their open data terms
- Radio audio plays directly from Highland Radio's public stream in your own browser; nothing is recorded or rebroadcast
