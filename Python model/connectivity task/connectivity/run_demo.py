from __future__ import annotations

import csv
import json
from pathlib import Path

from .build_graph import build_graph, load_port_access, load_routes
from .load import issues_to_markdown, load, validate
from .mapviz import build_map, build_static_map
from .model import GraphConfig, SolverAssumptions
from .scenario import BASELINE, Scenario, compare, run
from .trace import summarise, trace_upstream
from .upstream import with_illustrative_upstream

ROOT = Path(__file__).resolve().parents[1]
DATA, REF, OUT = ROOT / "data", ROOT / "data" / "reference", ROOT / "outputs"
MOERDIJK_CRACKER = "1c67c9a5"


def load_scenarios(path: Path) -> dict[str, list[Scenario]]:
    raw = json.loads(path.read_text())
    return {group: [Scenario.model_validate(s) for s in raw[group]] for group in ("standard", "illustrative")}


def md_table(rows: list[dict], cols: list[str]) -> str:
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(r.get(c, "")) for c in cols) + " |" for r in rows]
    return "\n".join(lines)


def kt(t: float) -> int:
    return round(t / 1e3)


def save_run(r: dict, path: Path):
    g = r["graph"]
    name = lambda n: g.nodes[n].get("name", n) if n in g else n
    res = dict(r["result"])
    res["edge_flows_t"] = {f"{name(u)} -> {name(v)} [{g.edges[u, v, k]['mode']}]": t
                           for (u, v, k), t in res["edge_flows_t"].items()}
    for key in ("source_t", "unmet_t", "demand_t", "supply_capacity_t", "crude_source_t", "crude_unmet_t",
                "refinery_run_rate"):
        res[key] = {name(n): t for n, t in res[key].items()}
    record = {k: v for k, v in r.items() if k != "graph"} | {"result": res}
    path.write_text(json.dumps(record, indent=1, default=str))


def write_diagnostics(diag):
    out = ["# Graph-build diagnostics (generated)\n"]
    for title, rows in [("Pipeline ends matched to sites", diag.snaps),
                        ("Loose ends (no site, inside the slice)", diag.loose_ends),
                        ("Pass-bys: site near a line's middle, deliberately not connected", diag.pass_bys),
                        ("Assumed fallback links", diag.unmapped)]:
        rows = [{k: v for k, v in r.items() if not k.endswith("lonlat")} for r in rows]
        out += [f"## {title} ({len(rows)})\n", md_table(rows, list(rows[0])) if rows else "_none_", ""]
    (OUT / "diagnostics.md").write_text("\n".join(out))


def write_tolerance_sensitivity(data, access):
    rows = []
    for snap in (2, 3, 4, 5, 6):
        for join in (3, 5, 8):
            G, diag = build_graph(data, GraphConfig(snap_km=snap, join_km=join), access)
            links = sorted({f"{G.nodes[u]['name']} -> {G.nodes[v]['name']} ({d['commodity']})"
                            for u, v, d in G.edges(data=True) if d["mode"] == "pipeline"
                            and G.nodes[u]["kind"] == G.nodes[v]["kind"] == "facility"})
            rows.append({"snap_km": snap, "join_km": join, "site_to_site_links": len(links),
                         "loose_ends": len(diag.loose_ends), "links": "; ".join(links)})
    with (OUT / "tolerance_sensitivity.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def write_traces(G, data):
    lines = ["# Upstream traces (generated)\n",
             "Which routes exist (not how much flows on them), best route per (tier-1 supplier, origin). "
             "`last_leg` = weakest link after the last transformation; `min` = weakest link on the whole route.\n"]
    for f in data.facilities.values():
        if f.role not in ("cracker", "petrochemical_complex"):
            continue
        rows = [r | {"last_leg": r["last_leg_confidence"], "min": r["min_confidence"]}
                for r in summarise(G, trace_upstream(G, f.id))]
        lines += [f"## {f.name}\n", md_table(rows, ["tier1_supplier", "origin", "last_leg", "min", "hops", "path"]), ""]
    (OUT / "traces.md").write_text("\n".join(lines))


def scenario_section(base: dict, shock: dict) -> list[str]:
    c = compare(base, shock)
    unmet = ", ".join(f"{k} {kt(v):,} kt" for k, v in c["unmet_t"].items()) or "none"
    rows = [r | {k: kt(r[k]) for k in ("base_t", "shock_t", "delta_t")} for r in c["supply_changes"]]
    return [f"\n## {shock['scenario']['name']}: {shock['scenario']['description']}\n",
            f"Shock run `{shock['run_id']}`; {len(c['intervention_log'])} graph elements removed or changed. "
            f"Unmet naphtha demand: {unmet}.\n",
            md_table(rows, ["cracker", "origin", "base_t", "shock_t", "delta_t"]) + "\n\n(kt/yr)"]


def hormuz_section(G, data, routes, access, scenario: Scenario) -> list[str]:
    G_up = with_illustrative_upstream(G, data, REF / "illustrative_upstream.csv", routes, access)
    G_up.graph["variant"] = "illustrative_upstream"
    base, shock = run(G_up), run(G_up, scenario)
    save_run(shock, OUT / "runs" / f"{scenario.name}.json")
    c = compare(base, shock)
    crude = [{"exporter": G_up.nodes[n]["name"], "base_kt": kt(base["result"]["crude_source_t"].get(n, 0)),
              "shock_kt": kt(shock["result"]["crude_source_t"].get(n, 0))}
             for n, d in G_up.nodes(data=True) if d["kind"] == "oil_field"]
    crude.append({"exporter": "UNMET refinery crude", "base_kt": kt(sum(base["result"]["crude_unmet_t"].values())),
                  "shock_kt": kt(sum(shock["result"]["crude_unmet_t"].values()))})
    imp_before, imp_after = c["naphtha_import_t"]
    return ["\n## ILLUSTRATIVE: Strait of Hormuz closed (invented upstream)\n",
            "Two hypothetical exporters (`data/reference/illustrative_upstream.csv`) replace the unlimited seaborne "
            "crude market. Their locations are generic and their capacities are made up, so **the numbers below "
            "show the mechanism, not a forecast.**\n",
            f"{len(c['intervention_log'])} sea lanes cut. Crude by exporter (kt/yr):\n",
            md_table(crude, ["exporter", "base_kt", "shock_kt"]),
            "\nRefinery run rates (share of target crude intake supplied):\n",
            md_table(c["refinery_run_rate_changes"], ["refinery", "base", "shock"]),
            f"\nKnock-on: seaborne naphtha imports {kt(imp_before):,} -> {kt(imp_after):,} kt/yr; unmet cracker "
            f"demand {kt(sum(c['unmet_t'].values())):,} kt/yr.\n",
            "The stand-in solver cuts whole refineries rather than sharing the shortfall; that is a property of "
            "min-cost routing, not a prediction.\n",
            "Trace with the upstream slotted in (Moerdijk, top 3 routes, tracer unchanged):\n",
            md_table(summarise(G_up, trace_upstream(G_up, MOERDIJK_CRACKER))[:3],
                     ["tier1_supplier", "origin", "min_confidence", "path"])]


def main():
    (OUT / "runs").mkdir(parents=True, exist_ok=True)
    data = load(DATA)
    access = load_port_access(REF / "port_access.csv")
    routes = load_routes(REF / "route_geometry.json")
    scenarios = load_scenarios(REF / "scenarios.json")
    cfg = GraphConfig()

    (OUT / "data_quality.md").write_text(issues_to_markdown(validate(data, cfg.colocated_km)))
    G, diag = build_graph(data, cfg, access, waterways_csv=REF / "inland_waterways.csv", routes=routes)
    G_pkg, _ = build_graph(data, cfg, access, routes=routes)
    write_diagnostics(diag)
    write_tolerance_sensitivity(data, access)
    write_traces(G, data)
    build_map(G, data, diag, str(OUT / "network_map.html"))
    build_static_map(G, data, diag, str(OUT / "network_map.png"))

    base, base_pkg = run(G), run(G_pkg)
    save_run(base, OUT / "runs" / "baseline.json")
    md = ["# Scenario results (generated; stand-in solver, illustrative only)\n",
          f"Baseline run `{base['run_id']}`, data `{base['data_hash']}`, solver `{base['solver_version']}`.\n",
          "## Baseline: naphtha delivered to each cracker by original supplier (kt/yr)\n",
          md_table([{"cracker": c, **{k: kt(v) for k, v in m.items()}} for c, m in base["origin_mix_t"].items()],
                   ["cracker"] + sorted({k for m in base["origin_mix_t"].values() for k in m}))]
    coverage = []
    for s in scenarios["standard"]:
        shock, shock_pkg = run(G, s), run(G_pkg, s)
        save_run(shock, OUT / "runs" / f"{s.name}.json")
        md += scenario_section(base, shock)
        coverage.append({"scenario": s.name, "unmet_kt_with_barge_layer": kt(sum(shock["result"]["unmet_t"].values())),
                         "unmet_kt_package_data_only": kt(sum(shock_pkg["result"]["unmet_t"].values()))})
    md += ["\n## Coverage sensitivity: same shock, with and without the assumed barge layer\n",
           md_table(coverage, list(coverage[0]))]

    sensitivity = []
    for y in (0.07, 0.10, 0.13):
        a = SolverAssumptions().with_changes(naphtha_yield_on_crude=y)
        row = {"naphtha_yield": y, "baseline_import_kt": kt(run(G, BASELINE, a)["result"]["source_t"].get("ext:seaborne|naphtha", 0))}
        row |= {f"unmet_kt_{s.name}": kt(sum(run(G, s, a)["result"]["unmet_t"].values())) for s in scenarios["standard"]}
        sensitivity.append(row)
    md += ["\n## Assumption sensitivity: naphtha yield on crude (with barge layer)\n",
           md_table(sensitivity, list(sensitivity[0]))]

    for s in scenarios["illustrative"]:
        md += hormuz_section(G, data, routes, access, s)
    (OUT / "scenarios.md").write_text("\n".join(md) + "\n")
    print(f"Wrote outputs to {OUT}")


if __name__ == "__main__":
    main()
