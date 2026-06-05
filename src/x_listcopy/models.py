from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListReference:
    kind: str
    list_id: str | None = None
    owner_screen_name: str | None = None
    slug: str | None = None


@dataclass(frozen=True)
class GraphQLOperation:
    query_id: str
    operation_type: str
    features: dict[str, bool]
    field_toggles: dict[str, bool]


@dataclass(frozen=True)
class XList:
    id: str
    name: str | None
    member_count: int | None
