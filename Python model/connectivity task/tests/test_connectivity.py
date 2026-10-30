import json
import shutil
from pathlib import Path

import networkx as nx
import pytest
from pydantic import ValidationError

from connectivity.build_graph import build_graph, load_port_access, load_routes
from connectivity.load import load, validate
from connectivity.model import Commodity, SolverAssumptions, node_id, normalise_status
from connectivity.scenario import (AssetOutage, ChokepointBlock, FacilityOutage, IncomparableRuns, RegionBlock,
                                   Scenario, apply_scenario, compare, run)
from connectivity.upstream import with_illustrative_upstream
from connectivity.trace import trace_upstream

ROOT = Path(__file__).resolve().parents[1]
PERNIS, MOERDIJK_CHEM, CHEMELOT, DOW = "9f444ed5", "1c67c9a5", "6a46fddb", "47cf22ae"
TOTAL_OLEFINS, EXXON_ANTWERP, MOERDIJK_PORT = "74b0c40d", "3cc39dad", "82cc39d7"
NAPHTHA_PIPELINE = "ff619ee1-3a26-5140-918a-5f8da543321a"


def sc(name, *interventions):
    return Scenario(name=name, interventions=interventions)


@pytest.fixture(scope="module")
def data():
    return load(ROOT / "data")


@pytest.fixture(scope="module")
def graph(data):
    G, diag = build_graph(data, port_access=load_port_access(ROOT / "data/reference/port_access.csv"),
                          waterways_csv=ROOT / "data/reference/inland_waterways.csv",
                          routes=load_routes(ROOT / "data/reference/route_geometry.json"))
    return G, diag


def test_status_vocabularies_are_unified():
    assert normalise_status("Active") == normalise_status("Operational") == "operating"
    assert normalise_status("Mothballed").startswith("unknown")


def test_roles_are_derived_from_units(data):
    assert data.facilities[PERNIS].role == "refinery"
    assert data.facilities[MOERDIJK_CHEM].role == "cracker"
    assert data.facilities[MOERDIJK_PORT].role == "port"


def test_validation_flags_known_traps(data):
    text = " ".join(i.message for i in validate(data))
    assert "identical capacity 549,754" in text
    assert "0.74 km apart" in text
    assert "straight two-point line" in text


def test_every_edge_carries_provenance_and_confidence(graph):
    G, _ = graph
    for _, _, d in G.edges(data=True):
        assert d["provenance"] and 0 < d["confidence"] <= 1


def test_snapping_respects_unit_types(graph):
    _, diag = graph
    eth = [s for s in diag.snaps if s["commodity"] == "ethylene"]
    assert any(s["facility"] == "Total Olefins Antwerp" for s in eth)
    assert not any("Refinery" in s["facility"] for s in eth)


def test_pass_by_is_not_a_connection(graph):
    G, diag = graph
    assert any(p["facility"] == "Moerdijk [NL]" for p in diag.pass_bys)
    crude_into_moerdijk = [d for _, _, d in G.in_edges(node_id(MOERDIJK_PORT, Commodity.CRUDE), data=True)
                           if d["mode"] == "pipeline"]
    assert crude_into_moerdijk == []


def test_mapped_naphtha_link_pernis_to_moerdijk(graph):
    G, _ = graph
    edges = G.get_edge_data(node_id(PERNIS, Commodity.NAPHTHA), node_id(MOERDIJK_CHEM, Commodity.NAPHTHA))
    assert edges and any(d["mode"] == "pipeline" for d in edges.values())


def test_package_data_only_leaves_chemelot_on_assumed_links(data):
    G, diag = build_graph(data)
    inbound = [d for _, _, d in G.in_edges(node_id(CHEMELOT, Commodity.NAPHTHA), data=True)]
    assert inbound and all(d["provenance"] == "assumed" for d in inbound)


def test_trace_never_follows_ethylene(graph):
    G, _ = graph
    for path in trace_upstream(G, CHEMELOT):
        assert all(d["commodity"] != "ethylene" for _, _, d in path.edges)


def test_trace_reaches_crude_supply_through_the_refinery(graph):
    G, _ = graph
    origins = {G.nodes[p.origin]["commodity"] for p in trace_upstream(G, MOERDIJK_CHEM) if not p.truncated}
    assert "crude" in origins


def test_scenario_does_not_mutate_the_baseline_graph(graph):
    G, _ = graph
    before = (G.number_of_nodes(), G.number_of_edges())
    apply_scenario(G, sc("x", FacilityOutage(facility_id=PERNIS), ChokepointBlock(chokepoint="westerschelde")))
    assert (G.number_of_nodes(), G.number_of_edges()) == before


def test_facility_offline_removes_its_supply(graph):
    G, _ = graph
    shock = run(G, sc("pernis", FacilityOutage(facility_id=PERNIS)))
    assert node_id(PERNIS, Commodity.NAPHTHA) not in shock["result"]["supply_capacity_t"]
    assert all("Shell Pernis Refinery" not in mix for mix in shock["origin_mix_t"].values())


def test_baseline_delivers_all_demand_and_mix_conserves_volume(graph):
    G, _ = graph
    base = run(G)
    assert base["result"]["unmet_t"] == {}
    for n, demand in base["result"]["demand_t"].items():
        delivered = sum(base["origin_mix_t"][G.nodes[n]["name"]].values())
        assert delivered == pytest.approx(demand, rel=0.01)


def test_blocked_chokepoint_can_leave_demand_unmet(graph):
    G, _ = graph
    shock = run(G, sc("ws", ChokepointBlock(chokepoint="westerschelde")))
    assert shock["result"]["unmet_t"].get(node_id(DOW, Commodity.NAPHTHA), 0) > 0


def test_region_block_removes_sites_inside_polygon(graph):
    G, _ = graph
    poly = "POLYGON((4.20 51.20, 4.45 51.20, 4.45 51.40, 4.20 51.40, 4.20 51.20))"
    H, log = apply_scenario(G, sc("antwerp", RegionBlock(polygon_wkt=poly)))
    assert node_id(TOTAL_OLEFINS, Commodity.NAPHTHA) not in H
    assert node_id(MOERDIJK_CHEM, Commodity.NAPHTHA) in H


def test_hormuz_style_block_on_a_synthetic_graph():
    G = nx.MultiDiGraph(data_hash="synthetic", unit_capacity_t={})
    base = dict(commodity="crude", provenance="inferred", confidence=0.5, distance_km=1.0, asset_id=None,
                unit_ids=[], capacity_t=None, geometry=None)
    for n in ("ras_tanura", "yanbu", "rotterdam"):
        G.add_node(n, kind="facility", lon=0, lat=0, name=n)
    G.add_edge("ras_tanura", "rotterdam", mode="sea", chokepoints=["hormuz", "suez"], **base)
    G.add_edge("yanbu", "rotterdam", mode="sea", chokepoints=["suez"], **base)
    H, log = apply_scenario(G, sc("hormuz", ChokepointBlock(chokepoint="hormuz")))
    assert H.has_edge("yanbu", "rotterdam") and not H.has_edge("ras_tanura", "rotterdam")
    assert len(log) == 1


def test_compare_refuses_runs_with_different_assumptions(graph):
    G, _ = graph
    base = run(G)
    other = run(G, sc("pernis", FacilityOutage(facility_id=PERNIS)),
                assumptions=SolverAssumptions().with_changes(naphtha_yield_on_crude=0.12))
    with pytest.raises(IncomparableRuns):
        compare(base, other)


def test_partial_outage_scales_supply(graph):
    G, _ = graph
    base = run(G)
    partial = run(G, sc("pernis40", FacilityOutage(facility_id=PERNIS, residual=0.4)))
    n = node_id(PERNIS, Commodity.NAPHTHA)
    assert partial["result"]["supply_capacity_t"][n] == pytest.approx(0.4 * base["result"]["supply_capacity_t"][n])


def test_region_block_follows_route_geometry_not_straight_lines(graph):
    G, _ = graph
    box = "POLYGON((3.45 51.30, 4.28 51.30, 4.28 51.46, 3.45 51.46, 3.45 51.30))"
    _, log = apply_scenario(G, sc("ws_box", RegionBlock(polygon_wkt=box)))
    cut = " ".join(e["what"] for e in log if e["change"] == "removed edge")
    assert "Seaborne crude (outside slice) -> Antwerp [BE]" in cut
    assert "Seaborne crude (outside slice) -> Rotterdam [NL]" not in cut


def test_illustrative_hormuz_starves_refineries_and_raises_imports(data, graph):
    G, _ = graph
    ref = ROOT / "data/reference"
    G_up = with_illustrative_upstream(G, data, ref / "illustrative_upstream.csv",
                                      load_routes(ref / "route_geometry.json"),
                                      load_port_access(ref / "port_access.csv"))
    G_up.graph["variant"] = "illustrative_upstream"
    base, shock = run(G_up), run(G_up, sc("hormuz", ChokepointBlock(chokepoint="hormuz")))
    assert sum(shock["result"]["crude_unmet_t"].values()) > sum(base["result"]["crude_unmet_t"].values())
    imp = "ext:seaborne|naphtha"
    assert shock["result"]["source_t"].get(imp, 0) > base["result"]["source_t"].get(imp, 0)
    assert "ext:seaborne|crude" in G


def test_bad_rows_are_quarantined_not_fatal(tmp_path):
    for f in ("facilities.csv", "units.csv", "pipelines.geojson"):
        shutil.copy(ROOT / "data" / f, tmp_path / f)
    fac = (tmp_path / "facilities.csv").read_text().replace("51.9092,4.2794", "95.0,4.2794")
    (tmp_path / "facilities.csv").write_text(fac)
    units = (tmp_path / "units.csv").read_text().replace("CDU,crude_distillation,22259209", "CDU,crude_distillation,-5")
    (tmp_path / "units.csv").write_text(units)
    data = load(tmp_path)
    assert "7ad6df35" not in data.facilities and len(data.facilities) == 15
    assert "u_011" not in data.units
    messages = " ".join(i.message for i in validate(data))
    assert "facility rejected (lat" in messages and "unit rejected (design_capacity_t_per_year" in messages


def test_scenario_requests_are_validated():
    with pytest.raises(ValidationError):
        FacilityOutage(facility_id=PERNIS, residual=1.5)
    with pytest.raises(ValidationError):
        RegionBlock(polygon_wkt="not a polygon")
    with pytest.raises(ValidationError):
        Scenario.model_validate({"name": "x", "interventions": [{"kind": "meteor_strike"}]})
    raw = json.loads((ROOT / "data/reference/scenarios.json").read_text())
    assert all(Scenario.model_validate(s) for group in ("standard", "illustrative") for s in raw[group])


def test_assumptions_are_validated():
    with pytest.raises(ValidationError):
        SolverAssumptions(naphtha_yield_on_crude=1.2)
    with pytest.raises(ValidationError):
        SolverAssumptions().with_changes(cost_per_km={"pipeline": 1.0})


def test_integrated_site_supplies_itself(data):
    from connectivity.model import Unit
    site = data.facilities[TOTAL_OLEFINS]
    cdu = Unit(id="u_test", facility_id=site.id, name="CDU", unit_type="crude_distillation",
               design_capacity_t_per_year=5e6, status="Operational")
    facilities = dict(data.facilities) | {site.id: site.model_copy(update={"units": site.units + (cdu,)})}
    merged = type(data)(facilities, data.units | {cdu.id: cdu}, data.pipelines, data.data_hash)
    assert merged.facilities[site.id].role == "petrochemical_complex"
    G, _ = build_graph(merged)
    assert G.has_edge(node_id(site.id, Commodity.CRUDE), node_id(site.id, Commodity.NAPHTHA))
    assert "Total Olefins Antwerp" in {p.tier1_supplier(G) for p in trace_upstream(G, site.id)}
