"""Illustrative only: invented crude exporters for the Hormuz example."""
from __future__ import annotations

import copy
import csv
from pathlib import Path

import networkx as nx

from .build_graph import _add_edge, _approach
from .geo import path_km
from .load import NetworkData
from .model import Commodity, Mode, Provenance, UnitType, node_id


def with_illustrative_upstream(G: nx.MultiDiGraph, data: NetworkData, csv_path: Path, routes: dict,
                               port_access: dict[str, list[str]]) -> nx.MultiDiGraph:
    H = copy.deepcopy(G)
    H.remove_node("ext:seaborne|crude")
    with csv_path.open() as fh:
        exporters = list(csv.DictReader(fh))
    importers = [f for f in data.facilities.values() if f.is_port
                 and any(u.unit_type == UnitType.PORT_IMPORT for u in f.units)]
    for e in exporters:
        n = f"{e['id']}|crude"
        H.add_node(n, kind="oil_field", role="oil_field", commodity=Commodity.CRUDE.value,
                   name=f"{e['name']} (INVENTED)", lon=float(e["lon"]), lat=float(e["lat"]),
                   supply_t=float(e["crude_supply_t_per_year"]), source=e["source"])
        waypoints = [tuple(map(float, p.split())) for p in e["route_waypoints"].split(";") if p.strip()]
        chokepoints = [c for c in e["chokepoints"].split(";") if c]
        for port in importers:
            approach = _approach(routes, port.id) or [(port.lon, port.lat)]
            path = [(float(e["lon"]), float(e["lat"]))] + waypoints + approach
            imp = next(u for u in port.units if u.unit_type == UnitType.PORT_IMPORT)
            _add_edge(H, n, node_id(port.id, Commodity.CRUDE), mode=Mode.SEA, commodity=Commodity.CRUDE,
                      provenance=Provenance.ASSUMED, distance_km=path_km(path), unit_ids=[imp.id],
                      import_unit=imp.id, capacity_t=imp.capacity_t_per_year,
                      chokepoints=sorted(set(chokepoints + port_access.get(port.id, []))),
                      geometry=[path], note="illustrative route from an invented exporter")
    return H
