from __future__ import annotations

import shapely
from pyproj import Geod, Transformer
from shapely.geometry import LineString, Point

_TO_METRIC = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)


def to_metric(geom):
    return shapely.transform(geom, lambda x, y: _TO_METRIC.transform(x, y), interleaved=False)


def metric_point(lon: float, lat: float) -> Point:
    return to_metric(Point(lon, lat))


def metric_line(coords) -> LineString:
    return to_metric(LineString(coords))


def km(a, b) -> float:
    return a.distance(b) / 1000.0


_GEOD = Geod(ellps="WGS84")


def path_km(coords) -> float:
    lons, lats = zip(*coords)
    return _GEOD.line_length(lons, lats) / 1000.0
