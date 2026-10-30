# Graph-build diagnostics (generated)

## Pipeline ends matched to sites (11)

| pipeline | commodity | fragment | end | facility | distance_km | runner_up |
|---|---|---|---|---|---|---|
| 62ca72fe | crude | 0 | 0 | Shell Pernis Refinery | 2.74 |  |
| 62ca72fe | crude | 0 | 1 | Rotterdam [NL] | 3.49 |  |
| 62ca72fe | crude | 1 | 1 | ExxonMobil Botlek Rotterdam Refinery | 1.09 |  |
| 62ca72fe | crude | 3 | 0 | ExxonMobil Botlek Rotterdam Refinery | 3.5 |  |
| ff619ee1 | naphtha | 1 | 0 | BP Rotterdam Refinery | 1.33 |  |
| ff619ee1 | naphtha | 2 | 0 | Moerdijk Chemicals (Shell) | 1.97 | Moerdijk [NL] (3.97 km) |
| ff619ee1 | naphtha | 2 | 1 | Moerdijk [NL] | 1.57 | Moerdijk Chemicals (Shell) (2.59 km) |
| ff619ee1 | naphtha | 3 | 0 | Shell Pernis Refinery | 1.09 |  |
| ff619ee1 | naphtha | 3 | 1 | Moerdijk Chemicals (Shell) | 1.98 |  |
| 6ed918fb | ethylene | 0 | 1 | Total Olefins Antwerp | 3.88 |  |
| 6ed918fb | ethylene | 1 | 1 | Chemelot-Geleen Chemical Complex | 3.09 |  |

## Loose ends (no site, inside the slice) (14)

| pipeline | commodity | fragment | end | nearest | nearest_km |
|---|---|---|---|---|---|
| 62ca72fe | crude | 1 | 0 | ExxonMobil Botlek Rotterdam Refinery | 5.4 |
| 62ca72fe | crude | 2 | 0 | ExxonMobil Botlek Rotterdam Refinery | 4.3 |
| 62ca72fe | crude | 2 | 1 | ExxonMobil Botlek Rotterdam Refinery | 6.5 |
| 62ca72fe | crude | 4 | 0 | Moerdijk [NL] | 15.9 |
| 62ca72fe | crude | 4 | 1 | Moerdijk [NL] | 8.6 |
| 62ca72fe | crude | 5 | 0 | Moerdijk [NL] | 23.6 |
| 62ca72fe | crude | 5 | 1 | Moerdijk [NL] | 15.9 |
| 62ca72fe | crude | 6 | 0 | Moerdijk [NL] | 28.0 |
| 62ca72fe | crude | 6 | 1 | Antwerp [BE] | 19.3 |
| 62ca72fe | crude | 7 | 0 | Antwerp [BE] | 16.5 |
| 62ca72fe | crude | 7 | 1 | Antwerp [BE] | 25.0 |
| ff619ee1 | naphtha | 0 | 0 | Rotterdam [NL] | 4.2 |
| ff619ee1 | naphtha | 0 | 1 | Rotterdam [NL] | 4.3 |
| 6ed918fb | ethylene | 1 | 0 | Total Olefins Antwerp | 6.2 |

## Pass-bys: site near a line's middle, deliberately not connected (6)

| pipeline | fragment | facility | distance_km |
|---|---|---|---|
| 62ca72fe | 0 | ExxonMobil Botlek Rotterdam Refinery | 3.54 |
| 62ca72fe | 3 | Moerdijk [NL] | 3.11 |
| 62ca72fe | 4 | Moerdijk [NL] | 2.26 |
| ff619ee1 | 0 | Rotterdam [NL] | 3.89 |
| ff619ee1 | 1 | Moerdijk [NL] | 3.14 |
| ff619ee1 | 1 | ExxonMobil Botlek Rotterdam Refinery | 3.36 |

## Assumed fallback links (4)

| site | commodity | direction | port | distance_km | likely_mode |
|---|---|---|---|---|---|
| Total Lukoil Zeeland Refinery | crude | in | Terneuzen [NL] | 15.3 | jetty or short local line |
| Total Lukoil Zeeland Refinery | crude | in | Ghent [BE] | 35.4 | barge |
| Total Lukoil Zeeland Refinery | naphtha | out | Terneuzen [NL] | 15.3 | jetty or short local line |
| Total Lukoil Zeeland Refinery | naphtha | out | Ghent [BE] | 35.4 | barge |
