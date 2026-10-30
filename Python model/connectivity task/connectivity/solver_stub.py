"""Stand-in for the real solver: crude, then naphtha, each as a min-cost flow. Illustrative only."""
from __future__ import annotations

import networkx as nx

from .model import Commodity, SolverAssumptions

SOLVER_VERSION = "stub-mincost-0.2"
SRC, SINK = "__source__", "__sink__"


def _kt(t: float) -> int:
    return int(round(t / 1000))


def _min_cost_flow(G: nx.MultiDiGraph, c: Commodity, supply: dict, demand: dict,
                   market_supply: dict, a: SolverAssumptions) -> dict:
    total = sum(demand.values())
    H = nx.DiGraph()
    H.add_node(SRC, demand=-_kt(total))
    H.add_node(SINK, demand=_kt(total))
    for n, s in supply.items():
        if n in G:
            H.add_edge(SRC, n, capacity=_kt(s), weight=0)
    for n, cost in market_supply.items():
        if n in G:
            H.add_edge(SRC, n, weight=int(cost))
    for n, dmd in demand.items():
        H.add_edge(n, SINK, capacity=_kt(dmd), weight=0)
        H.add_edge(SRC, ("unmet", n), capacity=_kt(dmd), weight=int(a.unmet_penalty))
        H.add_edge(("unmet", n), n, weight=0)

    # Every sea leg through a terminal passes the same gate, so its capacity is shared, not per route.
    def gate(frm, unit_id: str, cap_t: float):
        g_in, g_out = ("gate_in", unit_id), ("gate_out", unit_id)
        H.add_edge(g_in, g_out, capacity=_kt(cap_t), weight=0)
        H.add_edge(frm, g_in, weight=0)
        return g_out

    unit_caps = G.graph.get("unit_capacity_t", {})
    heads = {}
    for u, v, k, d in G.edges(keys=True, data=True):
        if d["commodity"] != c.value or d["mode"] == "process":
            continue
        mid = ("edge", u, v, k)
        cost = a.cost_rate(d["mode"]) * d["distance_km"] + (a.port_handling_cost if d["mode"] == "sea" else 0)
        head = gate(u, d["export_unit"], unit_caps[d["export_unit"]]) if d.get("export_unit") else u
        H.add_edge(head, mid, weight=int(round(cost)))
        heads[(u, v, k)] = head
        tail = gate(mid, d["import_unit"], unit_caps[d["import_unit"]]) if d.get("import_unit") else mid
        H.add_edge(tail, v, weight=0)

    cost, flow = nx.network_simplex(H)
    unmet = {n[1]: flow[SRC][n] * 1000 for n in flow[SRC] if isinstance(n, tuple) and flow[SRC][n] > 0}
    return {
        "edge_flows_t": {key: flow[h][("edge", *key)] * 1000 for key, h in heads.items()
                         if flow[h][("edge", *key)] > 0},
        "source_t": {n: flow[SRC][n] * 1000 for n in flow[SRC] if not isinstance(n, tuple) and flow[SRC][n] > 0},
        "unmet_t": unmet,
        "objective": cost,
        "cost_index": cost - sum(t / 1000 for t in unmet.values()) * int(a.unmet_penalty),
    }


def solve(G: nx.MultiDiGraph, a: SolverAssumptions = SolverAssumptions()) -> dict:
    cdus = [(u, v, d) for u, v, d in G.edges(data=True)
            if d["mode"] == "process" and d["commodity"] == Commodity.NAPHTHA.value]
    crackers = [(u, v, d) for u, v, d in G.edges(data=True)
                if d["mode"] == "process" and G.nodes[u]["commodity"] == Commodity.NAPHTHA.value]

    crude_demand: dict[str, float] = {}
    for u, _, d in cdus:
        crude_demand[u] = crude_demand.get(u, 0.0) + d["capacity_t"] * a.refinery_utilisation
    crude_supply = {n: d["supply_t"] for n, d in G.nodes(data=True)
                    if d.get("commodity") == "crude" and d.get("supply_t")}
    crude_market = {"ext:seaborne|crude": a.import_premium}
    crude = _min_cost_flow(G, Commodity.CRUDE, crude_supply, crude_demand, crude_market, a)
    run_rate = {n: 1 - crude["unmet_t"].get(n, 0.0) / dmd if dmd else 0.0 for n, dmd in crude_demand.items()}

    supply: dict[str, float] = {}
    for u, v, d in cdus:
        supply[v] = supply.get(v, 0.0) + d["capacity_t"] * a.naphtha_yield_on_crude * run_rate.get(u, 0.0)
    demand: dict[str, float] = {}
    for u, _, d in crackers:
        demand[u] = demand.get(u, 0.0) + d["capacity_t"] / a.ethylene_yield_on_naphtha * a.cracker_utilisation
    naphtha = _min_cost_flow(G, Commodity.NAPHTHA, supply, demand, {"ext:seaborne|naphtha": a.import_premium}, a)

    return {
        "solver_version": SOLVER_VERSION,
        "edge_flows_t": {**crude["edge_flows_t"], **naphtha["edge_flows_t"]},
        "source_t": naphtha["source_t"],
        "unmet_t": naphtha["unmet_t"],
        "demand_t": demand,
        "supply_capacity_t": supply,
        "crude_source_t": crude["source_t"],
        "crude_unmet_t": crude["unmet_t"],
        "refinery_run_rate": run_rate,
        "objective": crude["objective"] + naphtha["objective"],
        "cost_index": crude["cost_index"] + naphtha["cost_index"],
        "naphtha_cost_index": naphtha["cost_index"],
    }
