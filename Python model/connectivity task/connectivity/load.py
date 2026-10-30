from __future__ import annotations

import csv
import hashlib
import itertools
import json
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from .geo import km, metric_line, metric_point
from .model import Commodity, Facility, Pipeline, Unit


@dataclass(frozen=True)
class Issue:
    severity: str
    entity: str
    message: str


@dataclass
class NetworkData:
    facilities: dict[str, Facility]
    units: dict[str, Unit]
    pipelines: list[Pipeline]
    data_hash: str
    rejected: list[Issue] = field(default_factory=list)


def _first_error(e: ValidationError) -> str:
    err = e.errors()[0]
    return f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}"


def load(data_dir: str | Path) -> NetworkData:
    data_dir = Path(data_dir)
    rejected: list[Issue] = []

    units: dict[str, Unit] = {}
    with (data_dir / "units.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                u = Unit.model_validate(row)
                units[u.id] = u
            except ValidationError as e:  # report and skip the row; don't stop the run
                rejected.append(Issue("high", row.get("id", "?"), f"unit rejected ({_first_error(e)})"))

    facilities: dict[str, Facility] = {}
    with (data_dir / "facilities.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            own_units = tuple(u for u in units.values() if u.facility_id == row.get("id"))
            try:
                f = Facility.model_validate({**row, "units": own_units})
                facilities[f.id] = f
            except ValidationError as e:
                rejected.append(Issue("high", row.get("id", "?"), f"facility rejected ({_first_error(e)})"))

    pipelines: list[Pipeline] = []
    geo = json.loads((data_dir / "pipelines.geojson").read_text(encoding="utf-8"))
    for feat in geo.get("features", []):
        props, g = feat.get("properties", {}), feat.get("geometry", {})
        parts = g.get("coordinates", []) if g.get("type") == "MultiLineString" else [g.get("coordinates", [])]
        try:
            pipelines.append(Pipeline.model_validate({**props, "parts": parts}))
        except ValidationError as e:
            rejected.append(Issue("high", str(props.get("id", "?"))[:8], f"pipeline rejected ({_first_error(e)})"))

    digest = hashlib.sha256()
    for name in ("facilities.csv", "units.csv", "pipelines.geojson"):
        digest.update((data_dir / name).read_bytes())
    return NetworkData(facilities, units, pipelines, digest.hexdigest()[:12], rejected)


def validate(data: NetworkData, colocated_km: float = 2.0) -> list[Issue]:
    issues = list(data.rejected)
    fac = data.facilities

    for u in data.units.values():
        if u.facility_id not in fac:
            issues.append(Issue("high", u.id, "unit belongs to a facility that is missing or was rejected"))
    for f in fac.values():
        if not f.units:
            issues.append(Issue("high", f.id, f"{f.name}: facility has no units, so no role"))
        if f.status.startswith("unknown") or any(u.status != f.status for u in f.units):
            issues.append(Issue("low", f.id, f"{f.name}: status unknown or inconsistent with its units"))

    by_cap: dict[float, list[Unit]] = {}
    for u in data.units.values():
        by_cap.setdefault(u.capacity_t_per_year, []).append(u)
    for cap, us in by_cap.items():
        if len(us) > 1:
            names = ", ".join(f"{fac[u.facility_id].name} / {u.name}" for u in us if u.facility_id in fac)
            issues.append(Issue("medium", "units", f"identical capacity {cap:,.0f} t/yr: {names}"))

    for a, b in itertools.combinations(fac.values(), 2):
        d = km(metric_point(a.lon, a.lat), metric_point(b.lon, b.lat))
        if d < colocated_km and "port" not in (a.role, b.role):
            issues.append(Issue("medium", f"{a.id},{b.id}", f"{a.name} ({a.role}) and {b.name} ({b.role}) "
                                f"are {d:.2f} km apart: one integrated site, or neighbours?"))

    for p in data.pipelines:
        pid = p.id[:8]
        issues.append(Issue("high", pid, f"{p.commodity.value} pipeline: {len(p.parts)} disjoint fragments and "
                            "no endpoint facility ids; connectivity must be inferred"))
        geom_km = sum(metric_line(part).length for part in p.parts) / 1000
        if p.baseline_distance_km and abs(geom_km / p.baseline_distance_km - 1) > 0.05:
            issues.append(Issue("medium", pid, f"geometry length {geom_km:.0f} km vs baseline_distance_km "
                                f"{p.baseline_distance_km:.0f} km; meaning of the field is unclear"))
        systems = sorted(set(p.segment_names) - {"UNK"})
        if len(systems) > 1:
            issues.append(Issue("medium", pid, f"one {p.commodity.value} feature stitches several named systems "
                                f"{systems}; the label may not hold for every segment"))
        for i, part in enumerate(p.parts):
            rounded = all(abs(c * 100 - round(c * 100)) < 1e-9 for xy in part for c in xy)
            if len(part) == 2 and rounded:
                issues.append(Issue("medium", pid, f"fragment {i} ({p.segment_names[i] if p.segment_names else '?'}) "
                                    f"is a straight two-point line with rounded coordinates despite "
                                    f"derivation={p.derivation}: drawn, not surveyed"))
        if p.commodity not in (Commodity.CRUDE, Commodity.NAPHTHA):
            issues.append(Issue("medium", pid, f"{p.commodity.value} is a cracker product: not used for naphtha tracing"))
    return issues


def issues_to_markdown(issues: list[Issue]) -> str:
    order = {"high": 0, "medium": 1, "low": 2}
    rows = ["| Severity | Entity | Issue |", "| --- | --- | --- |"]
    rows += [f"| {i.severity} | {i.entity} | {i.message} |" for i in sorted(issues, key=lambda x: order[x.severity])]
    return "# Data quality report (generated)\n\n" + "\n".join(rows) + "\n"
