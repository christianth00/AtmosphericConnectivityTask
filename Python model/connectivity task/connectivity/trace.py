from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from .model import Commodity, node_id


@dataclass
class TracePath:
    edges: list[tuple[str, str, dict]]
    truncated: bool = False

    @property
    def origin(self) -> str:
        return self.edges[0][0]

    @property
    def min_confidence(self) -> float:
        return min(d["confidence"] for _, _, d in self.edges)

    @property
    def weakest(self) -> str:
        return min(self.edges, key=lambda e: e[2]["confidence"])[2]["provenance"]

    @property
    def last_leg_confidence(self) -> float:
        idx = max((i for i, (_, _, d) in enumerate(self.edges) if d["mode"] == "process"), default=-1)
        return min((d["confidence"] for _, _, d in self.edges[idx + 1:]), default=1.0)

    def tier1_supplier(self, G) -> str:
        target_commodity = self.edges[-1][2]["commodity"]
        for u, v, d in reversed(self.edges):
            if d["mode"] == "process" and d["commodity"] == target_commodity:
                return G.nodes[v]["name"]
        return G.nodes[self.origin].get("name", self.origin)

    def describe(self, G) -> str:
        parts = [G.nodes[self.origin].get("name", self.origin)]
        for u, v, d in self.edges:
            if d["mode"] == "process":
                parts.append(f"[{d.get('unit_type', 'process')}: {G.nodes[u]['commodity']}->{d['commodity']}]")
            else:
                parts.append(f"--{d['mode']}/{d['provenance']}--> {G.nodes[v].get('name', v)}")
        return " ".join(parts) + (" (truncated)" if self.truncated else "")


def trace_upstream(G: nx.MultiDiGraph, facility_id: str, commodity: Commodity = Commodity.NAPHTHA,
                   max_hops: int = 8) -> list[TracePath]:
    target = node_id(facility_id, commodity)
    if target not in G:
        raise KeyError(f"{target} not in graph (facility offline, or does not handle {commodity.value})")
    paths: list[TracePath] = []

    def is_relay(u: str, v: str, d: dict) -> bool:
        return d["mode"] in ("sea", "barge") and G.nodes[u].get("role") == G.nodes[v].get("role") == "port"

    def walk(node: str, downstream: list, seen: frozenset, relays: dict):
        extended = False
        if len(downstream) < max_hops:
            for u, _, d in G.in_edges(node, data=True):
                if u in seen:
                    continue
                relay = is_relay(u, node, d)
                if relay and relays.get(d["commodity"], 0) >= 1:  # one port-to-port hop per commodity
                    continue
                legs = dict(relays)
                if relay:
                    legs[d["commodity"]] = legs.get(d["commodity"], 0) + 1
                extended = True
                walk(u, [(u, node, d)] + downstream, seen | {u}, legs)
        if not extended and downstream:
            truncated = len(downstream) >= max_hops
            is_origin = G.nodes[node]["kind"] == "boundary" or G.in_degree(node) == 0
            if is_origin or truncated:
                paths.append(TracePath(downstream, truncated=truncated and not is_origin))

    walk(target, [], frozenset({target}), {})
    return paths


def summarise(G, paths: list[TracePath]) -> list[dict]:
    best: dict[tuple, TracePath] = {}
    for p in (p for p in paths if not p.truncated):
        key = (p.tier1_supplier(G), p.origin)
        cur = best.get(key)
        if cur is None or (p.min_confidence, -len(p.edges)) > (cur.min_confidence, -len(cur.edges)):
            best[key] = p
    rows = [{"tier1_supplier": k[0], "origin": G.nodes[k[1]].get("name", k[1]),
             "last_leg_confidence": p.last_leg_confidence, "min_confidence": p.min_confidence,
             "weakest_link": p.weakest, "hops": len(p.edges),
             "path": p.describe(G)} for k, p in best.items()]
    return sorted(rows, key=lambda r: (-r["last_leg_confidence"], -r["min_confidence"], r["hops"]))
