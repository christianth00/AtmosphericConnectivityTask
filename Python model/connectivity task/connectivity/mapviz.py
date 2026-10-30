from __future__ import annotations

import folium

from .build_graph import Diagnostics
from .load import NetworkData

COLOURS = {
    "port": "#f2c200", "refinery": "#1f4e9c", "cracker": "#d62728", "petrochemical_complex": "#7b2d8b",
    "boundary": "#888888", "pipeline": "#f08c00", "sea": "#1a3a8a", "barge": "#2bb3d9",
    "port_link": "#8e44ad", "colocated": "#8e44ad", "unmapped": "#888888",
}

LEGEND = """
<div style="position: fixed; bottom: 24px; left: 24px; z-index: 9999; background: white; padding: 10px 12px;
            border: 1px solid #bbb; border-radius: 6px; font: 12px/1.5 sans-serif;">
<b>Edges</b> (solid = mapped geometry, dashed = inferred or assumed)<br>
<span style="color:#f08c00">&#9473;</span> pipeline (package geometry) &nbsp;
<span style="color:#f08c00">&#9476;</span> snap: pipeline end &rarr; site<br>
<span style="color:#1a3a8a">&#9476;</span> sea lane (inferred; hand-drawn waypoint route)<br>
<span style="color:#2bb3d9">&#9476;</span> barge (assumed; hand-drawn waypoint route)<br>
<span style="color:#8e44ad">&#9476;</span> port link / co-located site (inferred)<br>
<span style="color:#888">&#9476;</span> unmapped fallback (assumed)<br>
<b>Sites</b>: <span style="color:#f2c200">&#9679;</span> port <span style="color:#1f4e9c">&#9679;</span> refinery
<span style="color:#d62728">&#9679;</span> cracker <span style="color:#888">&#9679;</span> beyond slice
</div>
"""


def _latlon(coords):
    return [(lat, lon) for lon, lat in coords]


def build_map(G, data: NetworkData, diag: Diagnostics, path: str) -> None:
    m = folium.Map(location=[51.45, 4.6], zoom_start=9, tiles="OpenStreetMap")

    raw = folium.FeatureGroup(name="Pipelines: package geometry")
    for p in data.pipelines:
        for i, part in enumerate(p.parts):
            seg = p.segment_names[i] if i < len(p.segment_names) else "?"
            folium.PolyLine(_latlon(part), color=COLOURS["pipeline"], weight=4, opacity=0.9,
                            tooltip=f"{p.commodity.value} | {seg} | fragment {i} | {p.id[:8]}").add_to(raw)
    for s in diag.snaps:
        folium.PolyLine(_latlon([s["end_lonlat"], s["facility_lonlat"]]), color=COLOURS["pipeline"], weight=2,
                        dash_array="4 4", tooltip=f"snap {s['distance_km']} km -> {s['facility']}").add_to(raw)
    raw.add_to(m)

    groups = {mode: folium.FeatureGroup(name=label) for mode, label in [
        ("sea", "Sea lanes (inferred)"), ("barge", "Barge (assumed)"), ("port_link", "Port links (inferred)"),
        ("colocated", "Co-located sites (inferred)"), ("unmapped", "Unmapped fallback (assumed)")]}
    drawn = set()
    for u, v, d in G.edges(data=True):
        if d["mode"] not in groups or not d.get("geometry"):
            continue
        key = (d["mode"], tuple(sorted((G.nodes[u].get("facility_id", u), G.nodes[v].get("facility_id", v)))))
        if key in drawn:
            continue
        drawn.add(key)
        for line in d["geometry"]:
            folium.PolyLine(_latlon(line), color=COLOURS[d["mode"]], weight=2.5, dash_array="6 6", opacity=0.8,
                            tooltip=f"{d['mode']} | {d['provenance']} (conf {d['confidence']}) | "
                                    f"{G.nodes[u].get('name')} -> {G.nodes[v].get('name')}"
                                    + (f" | chokepoints: {', '.join(d['chokepoints'])}" if d["chokepoints"] else "")
                            ).add_to(groups[d["mode"]])
    for g in groups.values():
        g.add_to(m)

    sites = folium.FeatureGroup(name="Sites")
    for f in data.facilities.values():
        caps = "<br>".join(f"{u.name}: {u.unit_type.value}, {u.capacity_t_per_year / 1e6:.2f} Mt/yr" for u in f.units)
        folium.CircleMarker((f.lat, f.lon), radius=7, color="white", weight=1.5, fill=True, fill_opacity=1,
                            fill_color=COLOURS.get(f.role, "#333"),
                            popup=folium.Popup(f"<b>{f.name}</b> ({f.role})<br>{caps}", max_width=320),
                            tooltip=f.name).add_to(sites)
    for n, d in G.nodes(data=True):
        if d["kind"] == "boundary":
            folium.CircleMarker((d["lat"], d["lon"]), radius=5, color=COLOURS["boundary"], fill=True,
                                tooltip=d["name"]).add_to(sites)
    sites.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    m.get_root().html.add_child(folium.Element(LEGEND))
    m.save(path)


def build_static_map(G, data: NetworkData, diag: Diagnostics, path: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 8), dpi=130)
    styles = {"sea": ("--", 1.0), "barge": ("--", 1.6), "port_link": (":", 1.6),
              "colocated": (":", 1.6), "unmapped": ("--", 1.0)}
    seen = set()
    for u, v, d in G.edges(data=True):
        if d["mode"] not in styles or not d.get("geometry"):
            continue
        if d["mode"] == "sea" and G.nodes[u]["kind"] == G.nodes[v]["kind"] == "facility":
            continue
        key = (d["mode"], tuple(sorted((G.nodes[u].get("facility_id", u), G.nodes[v].get("facility_id", v)))))
        if key in seen:
            continue
        seen.add(key)
        ls, lw = styles[d["mode"]]
        for line in d["geometry"]:
            xs, ys = zip(*line)
            ax.plot(xs, ys, ls, color=COLOURS[d["mode"]], lw=lw, alpha=0.7, zorder=1,
                    label=f"{d['mode']} ({d['provenance']})")
    for p in data.pipelines:
        for part in p.parts:
            xs, ys = zip(*part)
            ax.plot(xs, ys, "-", color=COLOURS["pipeline"], lw=2.6, zorder=2,
                    label="pipeline geometry (package)")
    for s in diag.snaps:
        (x1, y1), (x2, y2) = s["end_lonlat"], s["facility_lonlat"]
        ax.plot([x1, x2], [y1, y2], ":", color=COLOURS["pipeline"], lw=1.4, zorder=2, label="snap: end -> site")
    for f in data.facilities.values():
        ax.scatter(f.lon, f.lat, s=70, color=COLOURS.get(f.role, "#333"), edgecolor="white", zorder=4,
                   label=f.role)
        ax.annotate(f.name.replace(" Refinery", "").replace(" Chemical Complex", ""), (f.lon, f.lat),
                    xytext=(5, 4), textcoords="offset points", fontsize=7, zorder=5)
    for n, d in G.nodes(data=True):
        if d["kind"] == "boundary" and d.get("role") == "boundary":
            ax.scatter(d["lon"], d["lat"], s=40, marker="s", color=COLOURS["boundary"], zorder=4, label="beyond slice")
    ax.annotate("Seaborne market\n(outside slice)", (3.0, 52.0), xytext=(4, -22), textcoords="offset points",
                fontsize=7, color=COLOURS["sea"])
    handles, labels = ax.get_legend_handles_labels()
    uniq = dict(zip(labels, handles))
    ax.legend(uniq.values(), uniq.keys(), fontsize=7, loc="lower right", frameon=True)
    ax.set_xlim(2.9, 6.4)
    ax.set_ylim(50.5, 52.1)
    ax.set_aspect(1 / 0.62)
    ax.set_xlabel("longitude")
    ax.set_ylabel("latitude")
    ax.set_title("NW Europe slice: mapped pipelines (solid) and inferred / assumed links (dashed, dotted)", fontsize=10)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
