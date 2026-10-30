from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator


class Commodity(str, Enum):
    CRUDE = "crude"
    NAPHTHA = "naphtha"
    ETHYLENE = "ethylene"


class UnitType(str, Enum):
    OIL_FIELD = "oil_field_extraction"
    CDU = "crude_distillation"
    CRACKER = "steam_cracker"
    PORT_IMPORT = "port_import"
    PORT_EXPORT = "port_export"


UNIT_IO: dict[UnitType, tuple[set[Commodity], set[Commodity]]] = {
    UnitType.OIL_FIELD: (set(), {Commodity.CRUDE}),
    UnitType.CDU: ({Commodity.CRUDE}, {Commodity.NAPHTHA}),
    UnitType.CRACKER: ({Commodity.NAPHTHA}, {Commodity.ETHYLENE}),
    UnitType.PORT_IMPORT: (set(), set()),
    UnitType.PORT_EXPORT: (set(), set()),
}

# Assumption: the data doesn't say which cargoes a terminal takes.
PORT_COMMODITIES = {Commodity.CRUDE, Commodity.NAPHTHA}


class Mode(str, Enum):
    PIPELINE = "pipeline"
    SEA = "sea"
    BARGE = "barge"
    PORT_LINK = "port_link"
    COLOCATED = "colocated"
    UNMAPPED = "unmapped"
    PROCESS = "process"


class Provenance(str, Enum):
    DERIVED = "derived"
    SNAPPED = "snapped"
    GAP_BRIDGED = "gap_bridged"
    INFERRED = "inferred"
    ASSUMED = "assumed"


# A ranking, not probabilities. A route is as weak as its weakest edge.
CONFIDENCE = {Provenance.DERIVED: 1.0, Provenance.SNAPPED: 0.8, Provenance.GAP_BRIDGED: 0.6,
              Provenance.INFERRED: 0.5, Provenance.ASSUMED: 0.2}

STATUS_MAP = {"active": "operating", "operational": "operating"}


def normalise_status(raw: str) -> str:
    return STATUS_MAP.get(str(raw).strip().lower(), f"unknown:{raw}")


Status = Annotated[str, BeforeValidator(normalise_status)]


class Record(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True, str_strip_whitespace=True)


class Unit(Record):
    id: str = Field(min_length=1)
    facility_id: str = Field(min_length=1)
    name: str
    unit_type: UnitType
    capacity_t_per_year: float = Field(gt=0, alias="design_capacity_t_per_year")
    status: Status

    @property
    def inputs(self) -> set[Commodity]:
        return UNIT_IO[self.unit_type][0]

    @property
    def outputs(self) -> set[Commodity]:
        return UNIT_IO[self.unit_type][1]


class Facility(Record):
    id: str = Field(min_length=1)
    name: str
    country: str = Field(pattern=r"^[A-Z]{3}$")
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    status: Status
    units: tuple[Unit, ...] = ()

    @property
    def unit_types(self) -> set[UnitType]:
        return {u.unit_type for u in self.units}

    @property
    def is_port(self) -> bool:
        return bool(self.unit_types & {UnitType.PORT_IMPORT, UnitType.PORT_EXPORT})

    @property
    def role(self) -> str:
        t = self.unit_types
        if UnitType.CDU in t and UnitType.CRACKER in t:
            return "petrochemical_complex"
        if UnitType.CDU in t:
            return "refinery"
        if UnitType.CRACKER in t:
            return "cracker"
        if self.is_port:
            return "port"
        if UnitType.OIL_FIELD in t:
            return "oil_field"
        return "unknown"

    def consumes(self) -> set[Commodity]:
        return set().union(*(u.inputs for u in self.units))

    def produces(self) -> set[Commodity]:
        return set().union(*(u.outputs for u in self.units))

    def handles(self) -> set[Commodity]:
        return self.consumes() | self.produces() | (PORT_COMMODITIES if self.is_port else set())

    def can_supply(self, c: Commodity) -> bool:
        return c in self.produces() or (self.is_port and c in PORT_COMMODITIES)

    def can_receive(self, c: Commodity) -> bool:
        return c in self.consumes() or (self.is_port and c in PORT_COMMODITIES)


LonLat = tuple[float, float]


class Pipeline(Record):
    id: str = Field(min_length=1)
    commodity: Commodity
    derivation: str = ""
    baseline_distance_km: float = Field(default=0.0, ge=0)
    segment_names: list[str] = []
    parts: list[list[LonLat]] = Field(min_length=1)

    @field_validator("parts")
    @classmethod
    def check_parts(cls, parts):
        for i, part in enumerate(parts):
            if len(part) < 2:
                raise ValueError(f"fragment {i} has fewer than two points")
            for lon, lat in part:
                if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                    raise ValueError(f"fragment {i} has an out-of-range coordinate ({lon}, {lat})")
        return parts

    @model_validator(mode="after")
    def check_names(self):
        if self.segment_names and len(self.segment_names) != len(self.parts):
            raise ValueError(f"{len(self.segment_names)} segment names for {len(self.parts)} fragments")
        return self


def node_id(facility_id: str, commodity: Commodity) -> str:
    return f"{facility_id}|{commodity.value}"


class GraphConfig(Record):
    snap_km: float = Field(4.0, gt=0, description="pipeline end -> site matching distance")
    join_km: float = Field(5.0, ge=0, description="gap between fragments still treated as one line")
    boundary_margin_km: float = Field(10.0, ge=0, description="ends this far outside the slice continue beyond it")
    port_link_km: float = Field(15.0, ge=0, description="port point -> site 'last mile' link")
    colocated_km: float = Field(2.0, ge=0, description="separate records this close may share product")
    unmapped_nearest_ports: int = Field(2, ge=1, description="fallback links for an unconnected site")


class SolverAssumptions(Record):
    naphtha_yield_on_crude: float = Field(0.10, gt=0, le=1)
    ethylene_yield_on_naphtha: float = Field(0.30, gt=0, le=1)
    cracker_utilisation: float = Field(0.85, gt=0, le=1)
    refinery_utilisation: float = Field(0.85, gt=0, le=1)
    cost_per_km: dict[str, float] = {"pipeline": 1.0, "port_link": 1.0, "colocated": 1.0, "sea": 0.5,
                                     "barge": 2.0, "unmapped": 3.0, "process": 0.0}
    port_handling_cost: float = Field(50.0, ge=0)
    import_premium: float = Field(150.0, ge=0)
    unmet_penalty: float = Field(1e6, gt=0)

    @field_validator("cost_per_km")
    @classmethod
    def every_mode_has_a_cost(cls, costs):
        missing = {m.value for m in Mode} - set(costs)
        if missing:
            raise ValueError(f"no cost for modes {sorted(missing)}")
        if any(v < 0 for v in costs.values()):
            raise ValueError("costs must be non-negative")
        return costs

    def cost_rate(self, mode: str) -> float:
        return self.cost_per_km[mode]

    def with_changes(self, **changes) -> SolverAssumptions:
        return SolverAssumptions(**{**self.model_dump(), **changes})  # model_copy would skip validation
