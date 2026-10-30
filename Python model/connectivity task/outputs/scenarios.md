# Scenario results (generated; stand-in solver, illustrative only)

Baseline run `ae8bef352f`, data `a8efcbf355c7`, solver `stub-mincost-0.2`.

## Baseline: naphtha delivered to each cracker by original supplier (kt/yr)

| cracker | BP Rotterdam Refinery | ExxonMobil Antwerp Refinery | ExxonMobil Botlek Rotterdam Refinery | Seaborne naphtha (outside slice) | Shell Pernis Refinery | Total Antwerp Refinery | Total Lukoil Zeeland Refinery |
|---|---|---|---|---|---|---|---|
| Moerdijk Chemicals (Shell) | 295 |  | 142 |  | 2226 |  |  |
| Total Olefins Antwerp |  | 1529 |  |  |  | 29 |  |
| Antwerp Petrochemicals (BASF) | 869 |  | 417 |  |  | 981 |  |
| Terneuzen Petrochemical (Dow) | 230 |  | 111 | 572 |  |  | 772 |
| Chemelot-Geleen Chemical Complex | 597 |  | 287 |  |  | 673 |  |

## pernis_offline: Shell Pernis refinery offline

Shock run `cec371e767`; 2 graph elements removed or changed. Unmet naphtha demand: none.

| cracker | origin | base_t | shock_t | delta_t |
|---|---|---|---|---|
| Antwerp Petrochemicals (BASF) | BP Rotterdam Refinery | 869 | 114 | -755 |
| Antwerp Petrochemicals (BASF) | ExxonMobil Botlek Rotterdam Refinery | 417 | 55 | -362 |
| Antwerp Petrochemicals (BASF) | Seaborne naphtha (outside slice) | 0 | 1117 | 1117 |
| Chemelot-Geleen Chemical Complex | BP Rotterdam Refinery | 597 | 78 | -519 |
| Chemelot-Geleen Chemical Complex | ExxonMobil Botlek Rotterdam Refinery | 287 | 38 | -249 |
| Chemelot-Geleen Chemical Complex | Seaborne naphtha (outside slice) | 0 | 768 | 768 |
| Moerdijk Chemicals (Shell) | BP Rotterdam Refinery | 295 | 1799 | 1504 |
| Moerdijk Chemicals (Shell) | ExxonMobil Botlek Rotterdam Refinery | 142 | 864 | 722 |
| Moerdijk Chemicals (Shell) | Shell Pernis Refinery | 2226 | 0 | -2226 |
| Terneuzen Petrochemical (Dow) | BP Rotterdam Refinery | 230 | 0 | -230 |
| Terneuzen Petrochemical (Dow) | ExxonMobil Botlek Rotterdam Refinery | 111 | 0 | -111 |
| Terneuzen Petrochemical (Dow) | Seaborne naphtha (outside slice) | 572 | 913 | 341 |

(kt/yr)

## pernis_at_40pct: Shell Pernis refinery running at 40% (partial outage)

Shock run `e93c626f3a`; 1 graph elements removed or changed. Unmet naphtha demand: none.

| cracker | origin | base_t | shock_t | delta_t |
|---|---|---|---|---|
| Antwerp Petrochemicals (BASF) | BP Rotterdam Refinery | 869 | 471 | -399 |
| Antwerp Petrochemicals (BASF) | ExxonMobil Botlek Rotterdam Refinery | 417 | 226 | -191 |
| Antwerp Petrochemicals (BASF) | Seaborne naphtha (outside slice) | 0 | 590 | 590 |
| Chemelot-Geleen Chemical Complex | BP Rotterdam Refinery | 597 | 323 | -274 |
| Chemelot-Geleen Chemical Complex | ExxonMobil Botlek Rotterdam Refinery | 287 | 155 | -131 |
| Chemelot-Geleen Chemical Complex | Seaborne naphtha (outside slice) | 0 | 405 | 405 |
| Moerdijk Chemicals (Shell) | BP Rotterdam Refinery | 295 | 1198 | 903 |
| Moerdijk Chemicals (Shell) | ExxonMobil Botlek Rotterdam Refinery | 142 | 575 | 433 |
| Moerdijk Chemicals (Shell) | Shell Pernis Refinery | 2226 | 890 | -1336 |
| Terneuzen Petrochemical (Dow) | BP Rotterdam Refinery | 230 | 0 | -230 |
| Terneuzen Petrochemical (Dow) | ExxonMobil Botlek Rotterdam Refinery | 111 | 0 | -111 |
| Terneuzen Petrochemical (Dow) | Seaborne naphtha (outside slice) | 572 | 913 | 341 |

(kt/yr)

## naphtha_pipeline_offline: The mapped naphtha pipeline (RRP / Pernis-Moerdijk) out of service

Shock run `c2ed6ee43a`; 4 graph elements removed or changed. Unmet naphtha demand: none.

| cracker | origin | base_t | shock_t | delta_t |
|---|---|---|---|---|
| Antwerp Petrochemicals (BASF) | BP Rotterdam Refinery | 869 | 495 | -374 |
| Antwerp Petrochemicals (BASF) | ExxonMobil Botlek Rotterdam Refinery | 417 | 238 | -179 |
| Antwerp Petrochemicals (BASF) | Shell Pernis Refinery | 0 | 553 | 553 |
| Chemelot-Geleen Chemical Complex | BP Rotterdam Refinery | 597 | 340 | -257 |
| Chemelot-Geleen Chemical Complex | ExxonMobil Botlek Rotterdam Refinery | 287 | 163 | -123 |
| Chemelot-Geleen Chemical Complex | Shell Pernis Refinery | 0 | 380 | 380 |
| Moerdijk Chemicals (Shell) | BP Rotterdam Refinery | 295 | 1025 | 730 |
| Moerdijk Chemicals (Shell) | ExxonMobil Botlek Rotterdam Refinery | 142 | 492 | 350 |
| Moerdijk Chemicals (Shell) | Shell Pernis Refinery | 2226 | 1146 | -1080 |
| Terneuzen Petrochemical (Dow) | BP Rotterdam Refinery | 230 | 131 | -99 |
| Terneuzen Petrochemical (Dow) | ExxonMobil Botlek Rotterdam Refinery | 111 | 63 | -48 |
| Terneuzen Petrochemical (Dow) | Shell Pernis Refinery | 0 | 147 | 147 |

(kt/yr)

## westerschelde_blocked: Sea and barge access via the Westerschelde blocked (a local 'Hormuz')

Shock run `b6de63ff2e`; 52 graph elements removed or changed. Unmet naphtha demand: Terneuzen Petrochemical (Dow) 1,684 kt.

| cracker | origin | base_t | shock_t | delta_t |
|---|---|---|---|---|
| Antwerp Petrochemicals (BASF) | BP Rotterdam Refinery | 869 | 388 | -481 |
| Antwerp Petrochemicals (BASF) | ExxonMobil Botlek Rotterdam Refinery | 417 | 225 | -192 |
| Antwerp Petrochemicals (BASF) | Total Antwerp Refinery | 981 | 1654 | 673 |
| Chemelot-Geleen Chemical Complex | BP Rotterdam Refinery | 597 | 987 | 390 |
| Chemelot-Geleen Chemical Complex | ExxonMobil Botlek Rotterdam Refinery | 287 | 571 | 284 |
| Chemelot-Geleen Chemical Complex | Total Antwerp Refinery | 673 | 0 | -673 |
| Moerdijk Chemicals (Shell) | BP Rotterdam Refinery | 295 | 277 | -18 |
| Moerdijk Chemicals (Shell) | ExxonMobil Botlek Rotterdam Refinery | 142 | 160 | 18 |
| Terneuzen Petrochemical (Dow) | BP Rotterdam Refinery | 230 | 0 | -230 |
| Terneuzen Petrochemical (Dow) | ExxonMobil Botlek Rotterdam Refinery | 111 | 0 | -111 |
| Terneuzen Petrochemical (Dow) | Seaborne naphtha (outside slice) | 572 | 0 | -572 |
| Terneuzen Petrochemical (Dow) | Total Lukoil Zeeland Refinery | 772 | 0 | -772 |
| Terneuzen Petrochemical (Dow) | UNMET | 0 | 1684 | 1684 |

(kt/yr)

## antwerp_area_closed: Everything inside a polygon around Antwerp port closed

Shock run `0ee8a18937`; 11 graph elements removed or changed. Unmet naphtha demand: none.

| cracker | origin | base_t | shock_t | delta_t |
|---|---|---|---|---|
| Antwerp Petrochemicals (BASF) | BP Rotterdam Refinery | 869 | 0 | -869 |
| Antwerp Petrochemicals (BASF) | ExxonMobil Botlek Rotterdam Refinery | 417 | 0 | -417 |
| Antwerp Petrochemicals (BASF) | Total Antwerp Refinery | 981 | 0 | -981 |
| Chemelot-Geleen Chemical Complex | BP Rotterdam Refinery | 597 | 1045 | 448 |
| Chemelot-Geleen Chemical Complex | ExxonMobil Botlek Rotterdam Refinery | 287 | 512 | 226 |
| Chemelot-Geleen Chemical Complex | Total Antwerp Refinery | 673 | 0 | -673 |
| Terneuzen Petrochemical (Dow) | BP Rotterdam Refinery | 230 | 613 | 382 |
| Terneuzen Petrochemical (Dow) | ExxonMobil Botlek Rotterdam Refinery | 111 | 300 | 190 |
| Terneuzen Petrochemical (Dow) | Seaborne naphtha (outside slice) | 572 | 0 | -572 |
| Total Olefins Antwerp | ExxonMobil Antwerp Refinery | 1529 | 0 | -1529 |
| Total Olefins Antwerp | Total Antwerp Refinery | 29 | 0 | -29 |

(kt/yr)

## Coverage sensitivity: same shock, with and without the assumed barge layer

| scenario | unmet_kt_with_barge_layer | unmet_kt_package_data_only |
|---|---|---|
| pernis_offline | 0 | 1947 |
| pernis_at_40pct | 0 | 1057 |
| naphtha_pipeline_offline | 0 | 1947 |
| westerschelde_blocked | 1684 | 6789 |
| antwerp_area_closed | 0 | 1279 |

## Assumption sensitivity: naphtha yield on crude (with barge layer)

| naphtha_yield | baseline_import_kt | unmet_kt_pernis_offline | unmet_kt_pernis_at_40pct | unmet_kt_naphtha_pipeline_offline | unmet_kt_westerschelde_blocked | unmet_kt_antwerp_area_closed |
|---|---|---|---|---|---|---|
| 0.07 | 3321 | 0 | 0 | 0 | 1684 | 0 |
| 0.1 | 572 | 0 | 0 | 0 | 1684 | 0 |
| 0.13 | 0 | 0 | 0 | 0 | 1684 | 0 |

## ILLUSTRATIVE: Strait of Hormuz closed (invented upstream)

Two hypothetical exporters (`data/reference/illustrative_upstream.csv`) replace the unlimited seaborne crude market. Their locations are generic and their capacities are made up, so **the numbers below show the mechanism, not a forecast.**

5 sea lanes cut. Crude by exporter (kt/yr):

| exporter | base_kt | shock_kt |
|---|---|---|
| Hypothetical Gulf exporter (INVENTED) | 37839 | 0 |
| Hypothetical North Sea exporter (INVENTED) | 40000 | 40000 |
| UNMET refinery crude | 0 | 37839 |

Refinery run rates (share of target crude intake supplied):

| refinery | base | shock |
|---|---|---|
| BP Rotterdam Refinery | 1.0 | 0.77 |
| ExxonMobil Antwerp Refinery | 1.0 | 0.0 |
| Total Lukoil Zeeland Refinery | 1.0 | 0.0 |
| Total Antwerp Refinery | 1.0 | 0.0 |

Knock-on: seaborne naphtha imports 572 -> 5,024 kt/yr; unmet cracker demand 0 kt/yr.

The stand-in solver cuts whole refineries rather than sharing the shortfall; that is a property of min-cost routing, not a prediction.

Trace with the upstream slotted in (Moerdijk, top 3 routes, tracer unchanged):

| tier1_supplier | origin | min_confidence | path |
|---|---|---|---|
| Shell Pernis Refinery | Hypothetical Gulf exporter (INVENTED) | 0.2 | Hypothetical Gulf exporter (INVENTED) --sea/assumed--> Rotterdam [NL] --pipeline/snapped--> Shell Pernis Refinery [crude_distillation: crude->naphtha] --pipeline/gap_bridged--> Moerdijk Chemicals (Shell) |
| Shell Pernis Refinery | Hypothetical North Sea exporter (INVENTED) | 0.2 | Hypothetical North Sea exporter (INVENTED) --sea/assumed--> Rotterdam [NL] --pipeline/snapped--> Shell Pernis Refinery [crude_distillation: crude->naphtha] --pipeline/gap_bridged--> Moerdijk Chemicals (Shell) |
| Seaborne naphtha (outside slice) | Seaborne naphtha (outside slice) | 0.5 | Seaborne naphtha (outside slice) --sea/inferred--> Moerdijk [NL] --pipeline/snapped--> Moerdijk Chemicals (Shell) |
