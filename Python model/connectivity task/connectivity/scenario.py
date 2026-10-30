from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from typing import Annotated, Literal, Union

import networkx as nx
from pydantic import BaseModel, ConfigDict, Field, field_validator
from shapely import wkt
from shapely.geometry import MultiLineString, Point, Polygon

from .model import GraphConfig, SolverAssumptions
from .solver_stub import solve


def _name(H, n) -> str:
    return H.nodes[n].get("name", n)


def _remove_edges(H, log: list, match, reason: str):
    for u, v, k, d in list(H.edges(keys=True, data=True)):
        if match(d):
            log.append({"change": "removed edge", "what": f"{_name(H, u)} -> {_name(H, v)} "
                        f"({d['mode']}, {d['commodity']})", "reason": reason})
            H.remove_edge(u, v, k)


def _remove_nodes(H, log: list, match, reason: str):
    for n, d in list(H.nodes(data=True)):
        if match(d):
            log.append({"change": "removed node", "what": f"{_name(H, n)} [{d.get('commodity')}] "
                        f"and its {H.degree(n)} edges", "reason": reason})
            H.remove_node(n)


class _Intervention(BaseModel):
    model_config = ConfigDict(frozen=True)


class FacilityOutage(_Intervention):
    kind: Literal["facility_outage"] = "facility_outage"
    facility_id: str = Field(min_length=1)
    residual: float = Field(0.0, ge=0, lt=1)

    def apply(self, H, log):
        if self.residual == 0:
            _remove_nodes(H, log, lambda d: d.get("facility_id") == self.facility_id, "facility offline")
            return
        for u, v, d in H.edges(data=True):
            if d["mode"] == "process" and H.nodes[u].get("facility_id") == self.facility_id:
                d["capacity_t"] *= self.residual
                log.append({"change": "capacity", "what": f"{_name(H, u)} ({d.get('unit_type')})",
                            "reason": f"{self.residual:.0%} of capacity remains"})


class UnitOutage(_Intervention):
    kind: Literal["unit_outage"] = "unit_outage"
    unit_id: str = Field(min_length=1)

    def apply(self, H, log):
        _remove_edges(H, log, lambda d: self.unit_id in d["unit_ids"], "unit offline")


class AssetOutage(_Intervention):
    kind: Literal["asset_outage"] = "asset_outage"
    asset_id: str = Field(min_length=1)

    def apply(self, H, log):
        _remove_edges(H, log, lambda d: d["asset_id"] == self.asset_id, "asset offline")


class ChokepointBlock(_Intervention):
    kind: Literal["chokepoint_block"] = "chokepoint_block"
    chokepoint: str = Field(min_length=1)

    def apply(self, H, log):
        _remove_edges(H, log, lambda d: self.chokepoint in d["chokepoints"], f"chokepoint blocked: {self.chokepoint}")


class RegionBlock(_Intervention):
    kind: Literal["region_block"] = "region_block"
    polygon_wkt: str

    @field_validator("polygon_wkt")
    @classmethod
    def must_be_a_valid_polygon(cls, v):
        try:
            geom = wkt.loads(v)
        except Exception as e:
            raise ValueError(f"not readable as WKT: {e}") from e
        if not isinstance(geom, Polygon) or not geom.is_valid:
            raise ValueError("must be a single valid polygon (lon/lat)")
        return v

    def apply(self, H, log):
        region = wkt.loads(self.polygon_wkt)
        _remove_nodes(H, log, lambda d: region.contains(Point(d["lon"], d["lat"])), "inside blocked region")
        _remove_edges(H, log, lambda d: bool(d.get("geometry")) and MultiLineString(d["geometry"]).intersects(region),
                      "route crosses blocked region")


Intervention = Annotated[Union[FacilityOutage, UnitOutage, AssetOutage, ChokepointBlock, RegionBlock],
                         Field(discriminator="kind")]


class Scenario(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    description: str = ""
    interventions: tuple[Intervention, ...] = ()

    @property
    def scenario_id(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()[:10]


BASELINE = Scenario(name="baseline", description="no intervention")


def apply_scenario(G: nx.MultiDiGraph, s: Scenario) -> tuple[nx.MultiDiGraph, list[dict]]:
    H = copy.deepcopy(G)  # the baseline graph is never touched
    log: list[dict] = []
    for intervention in s.interventions:
        intervention.apply(H, log)
    return H, log


def origin_mix(G: nx.MultiDiGraph, result: dict) -> dict[str, Counter]:
    F = nx.DiGraph()
    for (u, v, k), t in result["edge_flows_t"].items():
        if G.edges[u, v, k]["commodity"] == "naphtha":
            F.add_edge(u, v, t=F.get_edge_data(u, v, {"t": 0})["t"] + t)
    for n in list(result["source_t"]) + list(result["unmet_t"]) + list(result["demand_t"]):
        F.add_node(n)
    mix: dict[str, Counter] = {}
    for n in nx.topological_sort(F):
        c = Counter()
        if n in result["source_t"]:
            c[G.nodes[n].get("name", n)] += result["source_t"][n]
        if n in result["unmet_t"]:
            c["UNMET"] += result["unmet_t"][n]
        for u in F.predecessors(n):
            inflow_mix, total = mix[u], sum(mix[u].values())
            for origin, t in inflow_mix.items():
                c[origin] += F.edges[u, n]["t"] * t / total if total else 0
        mix[n] = c
    out = {}
    for n, dmd in result["demand_t"].items():
        total = sum(mix.get(n, Counter()).values())
        delivered = min(dmd, total)
        out[G.nodes[n]["name"]] = Counter({k: v * delivered / total for k, v in mix[n].items()}) if total else Counter()
    return out


def run(G: nx.MultiDiGraph, scenario: Scenario = BASELINE, assumptions: SolverAssumptions = SolverAssumptions(),
        graph_config: GraphConfig = GraphConfig()) -> dict:
    H, log = apply_scenario(G, scenario)
    result = solve(H, assumptions)
    graph_id = G.graph.get("variant", "standard")
    return {
        "run_id": hashlib.sha256(json.dumps([G.graph["data_hash"], graph_id, scenario.scenario_id,
                                             assumptions.model_dump(), graph_config.model_dump(),
                                             result["solver_version"]], default=str).encode()).hexdigest()[:10],
        "data_hash": G.graph["data_hash"],
        "graph_variant": graph_id,
        "graph_config": graph_config.model_dump(),
        "assumptions": assumptions.model_dump(),
        "solver_version": result["solver_version"],
        "scenario": scenario.model_dump(),
        "intervention_log": log,
        "graph": H,
        "result": result,
        "origin_mix_t": origin_mix(H, result),
    }


class IncomparableRuns(ValueError):
    pass


def compare(base: dict, shock: dict, min_change_t: float = 10_000) -> dict:
    for key in ("data_hash", "graph_variant", "solver_version", "assumptions", "graph_config"):
        if base[key] != shock[key]:
            raise IncomparableRuns(f"runs differ in {key}; a diff would mix the shock with other changes")

    def label(run, u, v, k):
        d = run["graph"].edges[u, v, k]
        names = (run["graph"].nodes[u].get("name", u), run["graph"].nodes[v].get("name", v))
        return f"{names[0]} -> {names[1]} ({d['mode']}, {d['commodity']})"

    flows = {}
    for tag, r in (("base", base), ("shock", shock)):
        for key, t in r["result"]["edge_flows_t"].items():
            flows.setdefault(label(r, *key), {"base": 0.0, "shock": 0.0})[tag] += t
    edge_changes = sorted(({"edge": e, **f, "delta": f["shock"] - f["base"]} for e, f in flows.items()
                           if abs(f["shock"] - f["base"]) >= min_change_t), key=lambda r: -abs(r["delta"]))

    crackers = sorted(set(base["origin_mix_t"]) | set(shock["origin_mix_t"]))
    supply_changes = []
    for cr in crackers:
        b, s = base["origin_mix_t"].get(cr, Counter()), shock["origin_mix_t"].get(cr, Counter())
        for origin in sorted(set(b) | set(s)):
            if abs(s.get(origin, 0) - b.get(origin, 0)) >= min_change_t:
                supply_changes.append({"cracker": cr, "origin": origin, "base_t": b.get(origin, 0),
                                       "shock_t": s.get(origin, 0), "delta_t": s.get(origin, 0) - b.get(origin, 0)})

    def nm(r, n):
        return r["graph"].nodes[n]["name"] if n in r["graph"] else n

    run_rates = []
    for n in sorted(set(base["result"]["refinery_run_rate"]) | set(shock["result"]["refinery_run_rate"])):
        b, s = base["result"]["refinery_run_rate"].get(n, 0.0), shock["result"]["refinery_run_rate"].get(n, 0.0)
        if abs(s - b) >= 0.01:
            run_rates.append({"refinery": nm(base, n), "base": round(b, 2) + 0.0, "shock": round(s, 2) + 0.0})
    return {
        "baseline_run": base["run_id"], "shock_run": shock["run_id"], "scenario": shock["scenario"]["name"],
        "intervention_log": shock["intervention_log"],
        "cost_index_change": shock["result"]["cost_index"] - base["result"]["cost_index"],
        "naphtha_cost_index_change": shock["result"]["naphtha_cost_index"] - base["result"]["naphtha_cost_index"],
        "unmet_t": {nm(shock, n): t for n, t in shock["result"]["unmet_t"].items()},
        "naphtha_import_t": (base["result"]["source_t"].get("ext:seaborne|naphtha", 0.0),
                             shock["result"]["source_t"].get("ext:seaborne|naphtha", 0.0)),
        "refinery_run_rate_changes": run_rates,
        "supply_changes": supply_changes,
        "edge_changes": edge_changes,
    }
