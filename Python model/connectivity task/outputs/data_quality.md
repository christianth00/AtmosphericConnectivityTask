# Data quality report (generated)

| Severity | Entity | Issue |
| --- | --- | --- |
| high | 62ca72fe | crude pipeline: 8 disjoint fragments and no endpoint facility ids; connectivity must be inferred |
| high | ff619ee1 | naphtha pipeline: 4 disjoint fragments and no endpoint facility ids; connectivity must be inferred |
| high | 6ed918fb | ethylene pipeline: 2 disjoint fragments and no endpoint facility ids; connectivity must be inferred |
| medium | units | identical capacity 549,754 t/yr: Total Olefins Antwerp / Naphtha Cracker 2, Chemelot-Geleen Chemical Complex / Naphthacracker — NAK 4 |
| medium | 3cc39dad,b9cc8511 | ExxonMobil Antwerp Refinery (refinery) and Total Antwerp Refinery (refinery) are 1.78 km apart: one integrated site, or neighbours? |
| medium | 3cc39dad,74b0c40d | ExxonMobil Antwerp Refinery (refinery) and Total Olefins Antwerp (cracker) are 0.74 km apart: one integrated site, or neighbours? |
| medium | b9cc8511,74b0c40d | Total Antwerp Refinery (refinery) and Total Olefins Antwerp (cracker) are 1.32 km apart: one integrated site, or neighbours? |
| medium | 62ca72fe | one crude feature stitches several named systems ['CEPS', 'RAPL', 'RMR']; the label may not hold for every segment |
| medium | ff619ee1 | geometry length 206 km vs baseline_distance_km 179 km; meaning of the field is unclear |
| medium | ff619ee1 | one naphtha feature stitches several named systems ['Gasunie', 'RRP']; the label may not hold for every segment |
| medium | 6ed918fb | geometry length 178 km vs baseline_distance_km 123 km; meaning of the field is unclear |
| medium | 6ed918fb | fragment 1 (Antwerpen_to_Geleen) is a straight two-point line with rounded coordinates despite derivation=MAPPED: drawn, not surveyed |
| medium | 6ed918fb | ethylene is a cracker product: not used for naphtha tracing |
