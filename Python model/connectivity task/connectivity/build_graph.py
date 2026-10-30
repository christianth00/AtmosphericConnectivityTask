from __future__ import annotations

import csv
import itertools
import json
from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx
from shapely.geometry import Point

from .geo import km, metric_line, metric_point, path_km
from .load import NetworkData
from .model import (CONFIDENCE, PORT_COMMODITIES, Commodity, Facility, GraphConfig, Mode, Provenance,
                    UnitType, node_id)

SEA_MARKET_LONLAT = (3.0, 52.0)
SEA_DETOUR = 1.2


@dataclass
class Diagnostics:
    snaps: list[dict] = field(default_factory=list)
    loose_ends: list[dict] = field(default_factory=list)
    pass_bys: list[dict] = field(default_factory=list)
    unmapped: list[dict] = field(default_factory=list)


def sea_market_node(c: Commodity) -> str:
    return f"ext:seaborne|{c.value}"


# Kept apart from supply, so the outside world can't relay cargo between our own ports.
def sea_export_node(c: Commodity) -> str:
    return f"ext:seaborne_export|{c.value}"


def load_port_access(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    with path.open() as fh:
        return {r["facility_id"]: [r["sea_access"]] for r in csv.DictReader(fh)}


def load_routes(path: Path | None) -> dict:
    return json.loads(path.read_text()) if path and path.exists() else {}


def _approach(routes: dict, port_id: str) -> list | None:
    r = routes.get("sea_approach", {}).get(port_id)
    return [tuple(p) for p in r["path"]] if r else None


def _sea_lane_path(routes: dict, a_id: str, b_id: str) -> list | None:
    pa, pb = _approach(routes, a_id), _approach(routes, b_id)
    if not (pa and pb):
        return None
    k = 0
    while k < min(len(pa), len(pb)) and pa[k] == pb[k]:
        k += 1
    return list(reversed(pa[k - 1:])) + pb[k:]


def _barge_path(routes: dict, a_id: str, b_id: str) -> list | None:
    br = routes.get("barge_route", {})
    if f"{a_id}>{b_id}" in br:
        return [tuple(p) for p in br[f"{a_id}>{b_id}"]]
    if f"{b_id}>{a_id}" in br:
        return [tuple(p) for p in reversed(br[f"{b_id}>{a_id}"])]
    return None


def _add_edge(G, u, v, *, mode: Mode, commodity: Commodity, provenance: Provenance,
              distance_km: float = 0.0, **attrs):
    confidence = CONFIDENCE[provenance] * attrs.pop("confidence_factor", 1.0)
    G.add_edge(u, v, mode=mode.value, commodity=commodity.value, provenance=provenance.value,
               confidence=round(confidence, 2), distance_km=round(distance_km, 2),
               asset_id=attrs.pop("asset_id", None), unit_ids=attrs.pop("unit_ids", []),
               capacity_t=attrs.pop("capacity_t", None), chokepoints=attrs.pop("chokepoints", []),
               geometry=attrs.pop("geometry", None), **attrs)


def _add_facility_nodes(G, data: NetworkData):
    for f in data.facilities.values():
        for c in sorted(f.handles()):
            G.add_node(node_id(f.id, c), kind="facility", facility_id=f.id, name=f.name, role=f.role,
                       commodity=c.value, lon=f.lon, lat=f.lat, status=f.status)


def _add_process_edges(G, data: NetworkData):
    for f in data.facilities.values():
        for u in f.units:
            for cin, cout in itertools.product(sorted(u.inputs), sorted(u.outputs)):
                _add_edge(G, node_id(f.id, cin), node_id(f.id, cout), mode=Mode.PROCESS,
                          commodity=cout, provenance=Provenance.DERIVED, unit_ids=[u.id],
                          capacity_t=u.capacity_t_per_year, unit_type=u.unit_type.value)


def _add_pipeline_edges(G, data: NetworkData, cfg: GraphConfig, diag: Diagnostics):
    facs = list(data.facilities.values())
    pts = {f.id: metric_point(f.lon, f.lat) for f in facs}
    lons, lats = [f.lon for f in facs], [f.lat for f in facs]
    bbox = metric_line([(min(lons), min(lats)), (max(lons), max(lats))]).envelope

    for p in data.pipelines:
        c = p.commodity
        eligible = [f for f in facs if f.can_supply(c) or f.can_receive(c)]
        H = nx.Graph()
        ends: dict[tuple, Point] = {}
        for i, part in enumerate(p.parts):
            line = metric_line(part)
            a, b = (i, 0), (i, 1)
            ends[a], ends[b] = metric_point(*part[0]), metric_point(*part[-1])
            H.add_edge(a, b, km=line.length / 1000, gap=False, frag=i)
            # A site near the middle of a line but not an end is reported, not connected.
            for f in eligible:
                d_line = km(line, pts[f.id])
                if d_line < cfg.snap_km and min(km(ends[a], pts[f.id]), km(ends[b], pts[f.id])) >= cfg.snap_km:
                    diag.pass_bys.append({"pipeline": p.id[:8], "fragment": i, "facility": f.name,
                                          "distance_km": round(d_line, 2)})
        for e1, e2 in itertools.combinations(ends, 2):
            if e1[0] != e2[0] and km(ends[e1], ends[e2]) < cfg.join_km:
                H.add_edge(e1, e2, km=km(ends[e1], ends[e2]), gap=True)

        terminal: dict[str, tuple] = {}
        for key, pt in ends.items():
            ranked = sorted(((km(pt, pts[f.id]), f) for f in eligible), key=lambda t: t[0])
            if ranked and ranked[0][0] < cfg.snap_km:
                d, f = ranked[0]
                runner_up = ranked[1] if len(ranked) > 1 and ranked[1][0] < cfg.snap_km else None
                nid = node_id(f.id, c)
                if nid not in terminal:
                    terminal[nid] = key
                diag.snaps.append({"pipeline": p.id[:8], "commodity": c.value, "fragment": key[0],
                                   "end_lonlat": p.parts[key[0]][0 if key[1] == 0 else -1],
                                   "facility_lonlat": (f.lon, f.lat),
                                   "end": key[1], "facility": f.name, "distance_km": round(d, 2),
                                   "runner_up": f"{runner_up[1].name} ({runner_up[0]:.2f} km)" if runner_up else ""})
            elif bbox.distance(pt) / 1000 > cfg.boundary_margin_km:
                lon, lat = p.parts[key[0]][0 if key[1] == 0 else -1]
                seg = p.segment_names[key[0]] if key[0] < len(p.segment_names) else "UNK"
                nid = f"ext:{seg}@{lon:.2f},{lat:.2f}|{c.value}"
                G.add_node(nid, kind="boundary", name=f"Beyond slice ({seg}, {c.value})", role="boundary",
                           commodity=c.value, lon=lon, lat=lat)
                terminal[nid] = key
            else:
                diag.loose_ends.append({"pipeline": p.id[:8], "commodity": c.value, "fragment": key[0],
                                        "end": key[1], "nearest": ranked[0][1].name if ranked else "",
                                        "nearest_km": round(ranked[0][0], 1) if ranked else None})

        def supplies(n):
            return G.nodes[n]["kind"] == "boundary" or data.facilities[G.nodes[n]["facility_id"]].can_supply(c)

        def receives(n):
            return G.nodes[n]["kind"] == "boundary" or data.facilities[G.nodes[n]["facility_id"]].can_receive(c)

        for a, b in itertools.permutations(terminal, 2):
            ea, eb = terminal[a], terminal[b]
            if not (supplies(a) and receives(b)) or not nx.has_path(H, ea, eb):
                continue
            path = nx.shortest_path(H, ea, eb, weight="km")
            hops = list(zip(path, path[1:]))
            gaps = sum(H.edges[h]["gap"] for h in hops)
            frags = sorted({H.edges[h]["frag"] for h in hops if not H.edges[h]["gap"]})
            boundary = "boundary" in (G.nodes[a]["kind"], G.nodes[b]["kind"])
            _add_edge(G, a, b, mode=Mode.PIPELINE, commodity=c,
                      provenance=Provenance.GAP_BRIDGED if gaps else Provenance.SNAPPED,
                      distance_km=sum(H.edges[h]["km"] for h in hops), asset_id=p.id, gaps_bridged=gaps,
                      segments=[p.segment_names[i] for i in frags if i < len(p.segment_names)],
                      geometry=[p.parts[i] for i in frags],
                      confidence_factor=0.5 if boundary else 1.0)  # direction unknown at the boundary


def _add_port_links(G, data: NetworkData, cfg: GraphConfig):
    facs = data.facilities.values()
    for port, f in itertools.product([x for x in facs if x.is_port], [x for x in facs if not x.is_port]):
        d = km(metric_point(port.lon, port.lat), metric_point(f.lon, f.lat))
        if d > cfg.port_link_km:
            continue
        line = [[(port.lon, port.lat), (f.lon, f.lat)]]
        for c in sorted(PORT_COMMODITIES):
            if f.can_receive(c):
                _add_edge(G, node_id(port.id, c), node_id(f.id, c), mode=Mode.PORT_LINK, commodity=c,
                          provenance=Provenance.INFERRED, distance_km=d, geometry=line)
            if f.can_supply(c):
                _add_edge(G, node_id(f.id, c), node_id(port.id, c), mode=Mode.PORT_LINK, commodity=c,
                          provenance=Provenance.INFERRED, distance_km=d, geometry=line)


def _add_colocated(G, data: NetworkData, cfg: GraphConfig):
    facs = [f for f in data.facilities.values() if not f.is_port]
    for a, b in itertools.permutations(facs, 2):
        d = km(metric_point(a.lon, a.lat), metric_point(b.lon, b.lat))
        if d > cfg.colocated_km:
            continue
        for c in Commodity:
            if a.can_supply(c) and b.can_receive(c):
                _add_edge(G, node_id(a.id, c), node_id(b.id, c), mode=Mode.COLOCATED, commodity=c,
                          provenance=Provenance.INFERRED, distance_km=d,
                          geometry=[[(a.lon, a.lat), (b.lon, b.lat)]],
                          note="same integrated site or neighbours? ownership not in data")


def _port_unit(f: Facility, t: UnitType):
    return next((u for u in f.units if u.unit_type == t), None)


def _add_sea_lanes(G, data: NetworkData, access: dict[str, list[str]], routes: dict):
    ports = [f for f in data.facilities.values() if f.is_port]
    mx, my = SEA_MARKET_LONLAT
    for c in sorted(PORT_COMMODITIES):
        G.add_node(sea_market_node(c), kind="boundary", role="seaborne_market", commodity=c.value,
                   name=f"Seaborne {c.value} (outside slice)", lon=mx, lat=my)
        G.add_node(sea_export_node(c), kind="boundary", role="seaborne_export", commodity=c.value,
                   name=f"Export {c.value} (outside slice)", lon=mx, lat=my)
    for a, b in itertools.permutations(ports, 2):
        exp, imp = _port_unit(a, UnitType.PORT_EXPORT), _port_unit(b, UnitType.PORT_IMPORT)
        if not (exp and imp):
            continue
        path = _sea_lane_path(routes, a.id, b.id) or [(a.lon, a.lat), (b.lon, b.lat)]
        d = path_km(path) if len(path) > 2 else km(metric_point(a.lon, a.lat), metric_point(b.lon, b.lat)) * SEA_DETOUR
        for c in sorted(PORT_COMMODITIES):
            _add_edge(G, node_id(a.id, c), node_id(b.id, c), mode=Mode.SEA, commodity=c,
                      provenance=Provenance.INFERRED, distance_km=d, unit_ids=[exp.id, imp.id],
                      export_unit=exp.id, import_unit=imp.id,
                      capacity_t=min(exp.capacity_t_per_year, imp.capacity_t_per_year),
                      chokepoints=sorted(set(access.get(a.id, []) + access.get(b.id, []))),
                      geometry=[path])
    for p in ports:
        path = _approach(routes, p.id) or [(mx, my), (p.lon, p.lat)]
        d = path_km(path) if len(path) > 2 else km(metric_point(mx, my), metric_point(p.lon, p.lat)) * SEA_DETOUR
        imp, exp = _port_unit(p, UnitType.PORT_IMPORT), _port_unit(p, UnitType.PORT_EXPORT)
        for c in sorted(PORT_COMMODITIES):
            if imp:
                _add_edge(G, sea_market_node(c), node_id(p.id, c), mode=Mode.SEA, commodity=c,
                          provenance=Provenance.INFERRED, distance_km=d, unit_ids=[imp.id], import_unit=imp.id,
                          capacity_t=imp.capacity_t_per_year, chokepoints=access.get(p.id, []),
                          geometry=[path])
            if exp:
                _add_edge(G, node_id(p.id, c), sea_export_node(c), mode=Mode.SEA, commodity=c,
                          provenance=Provenance.INFERRED, distance_km=d, unit_ids=[exp.id], export_unit=exp.id,
                          capacity_t=exp.capacity_t_per_year, chokepoints=access.get(p.id, []),
                          geometry=[list(reversed(path))])


BARGE_DETOUR = 1.4


def _add_reference_waterways(G, data: NetworkData, path: Path, routes: dict):
    if not path.exists():
        return
    with path.open() as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        pairs = [(r["from_id"], r["to_id"])]
        if r["bidirectional"].strip().lower() == "true":
            pairs.append((r["to_id"], r["from_id"]))
        for a_id, b_id in pairs:
            a, b = data.facilities.get(a_id), data.facilities.get(b_id)
            if not (a and b):
                continue
            route = _barge_path(routes, a_id, b_id)
            d = path_km(route) if route else km(metric_point(a.lon, a.lat), metric_point(b.lon, b.lat)) * BARGE_DETOUR
            for c in sorted(PORT_COMMODITIES):
                if a.can_supply(c) and b.can_receive(c):
                    _add_edge(G, node_id(a.id, c), node_id(b.id, c), mode=Mode.BARGE, commodity=c,
                              provenance=Provenance.ASSUMED, confidence_factor=1.5, distance_km=d,
                              waterway=r["waterway"], chokepoints=[r["chokepoint"]] if r["chokepoint"] else [],
                              geometry=[route or [(a.lon, a.lat), (b.lon, b.lat)]])


def _add_unmapped_fallback(G, data: NetworkData, cfg: GraphConfig, diag: Diagnostics):
    ports = [f for f in data.facilities.values() if f.is_port]
    for f in (x for x in data.facilities.values() if not x.is_port):
        needs = [(c, "in") for c in sorted(f.consumes() & PORT_COMMODITIES)]
        needs += [(c, "out") for c in sorted(f.produces() & PORT_COMMODITIES)]
        for c, direction in needs:
            n = node_id(f.id, c)
            edges = G.in_edges(n, data=True) if direction == "in" else G.out_edges(n, data=True)
            if any(d["mode"] != Mode.PROCESS.value for *_, d in edges):
                continue
            ranked = sorted(((km(metric_point(p.lon, p.lat), metric_point(f.lon, f.lat)), p) for p in ports),
                            key=lambda t: t[0])
            for d, p in ranked[: cfg.unmapped_nearest_ports]:
                likely = "barge" if d > 30 else "jetty or short local line"
                a, b = (node_id(p.id, c), n) if direction == "in" else (n, node_id(p.id, c))
                _add_edge(G, a, b, mode=Mode.UNMAPPED, commodity=c, provenance=Provenance.ASSUMED,
                          distance_km=d, likely_mode=likely,
                          geometry=[[(p.lon, p.lat), (f.lon, f.lat)]])
                diag.unmapped.append({"site": f.name, "commodity": c.value, "direction": direction,
                                      "port": p.name, "distance_km": round(d, 1), "likely_mode": likely})


def build_graph(data: NetworkData, cfg: GraphConfig = GraphConfig(), port_access: dict[str, list[str]] | None = None,
                waterways_csv: Path | None = None, routes: dict | None = None) -> tuple[nx.MultiDiGraph, Diagnostics]:
    G = nx.MultiDiGraph(data_hash=data.data_hash,
                        unit_capacity_t={u.id: u.capacity_t_per_year for u in data.units.values()})
    diag = Diagnostics()
    _add_facility_nodes(G, data)
    _add_process_edges(G, data)
    _add_pipeline_edges(G, data, cfg, diag)
    _add_port_links(G, data, cfg)
    _add_colocated(G, data, cfg)
    _add_sea_lanes(G, data, port_access or {}, routes or {})
    if waterways_csv is not None:
        _add_reference_waterways(G, data, waterways_csv, routes or {})
    _add_unmapped_fallback(G, data, cfg, diag)
    return G, diag
