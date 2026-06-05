from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from .models import GraphQLOperation, XList
from .parsing import (
    extract_users_from_timeline,
    is_list_response_decode_error,
    parse_list_reference,
)

X_HOME = "https://x.com/home"
GRAPHQL_URL = "https://x.com/i/api/graphql/{query_id}/{operation}"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
)
REQUIRED_OPERATIONS = [
    "Viewer",
    "ListByRestId",
    "ListBySlug",
    "ListMembers",
    "ListAddMember",
    "CreateList",
]


class XClient:
    def __init__(self, auth_token: str, ct0: str, bearer_token: str | None = None):
        self.auth_token = auth_token
        self.ct0 = ct0
        self.bearer_token = bearer_token or fetch_current_bearer()
        self.operations = discover_operations(REQUIRED_OPERATIONS)

    @classmethod
    def from_env(cls) -> "XClient":
        auth_token = os.environ.get("X_AUTH_TOKEN")
        ct0 = os.environ.get("X_CT0")
        if not auth_token or not ct0:
            raise SystemExit("Set X_AUTH_TOKEN and X_CT0 before running this command.")
        return cls(
            auth_token=auth_token,
            ct0=ct0,
            bearer_token=os.environ.get("X_BEARER_TOKEN"),
        )

    def viewer(self) -> dict:
        data = self.graphql(
            "Viewer",
            {"withCommunitiesMemberships": False},
            field_toggles={"isDelegate": False},
        )
        result = (
            data.get("data", {})
            .get("viewer", {})
            .get("user_results", {})
            .get("result", {})
        )
        if not result.get("rest_id"):
            raise RuntimeError("Could not verify the logged-in X account.")
        return result

    def resolve_list(self, value: str) -> XList:
        ref = parse_list_reference(value)
        if ref.kind == "id":
            try:
                data = self.graphql("ListByRestId", {"listId": ref.list_id})
                list_obj = data.get("data", {}).get("list")
            except RuntimeError:
                return XList(id=ref.list_id, name=None, member_count=None)
        else:
            data = self.graphql(
                "ListBySlug",
                {"screenName": ref.owner_screen_name, "listSlug": ref.slug},
            )
            list_obj = data.get("data", {}).get("user_by_screen_name", {}).get("list")
        return normalize_list(list_obj)

    def fetch_members(
        self,
        list_id: str,
        limit: int | None = None,
        count: int = 100,
    ) -> list[dict[str, str | None]]:
        cursor: str | None = None
        members: list[dict[str, str | None]] = []
        seen: set[str] = set()

        while True:
            variables = {"listId": list_id, "count": count}
            if cursor:
                variables["cursor"] = cursor
            data = self.graphql("ListMembers", variables)
            timeline = (
                data.get("data", {})
                .get("list", {})
                .get("members_timeline", {})
                .get("timeline")
            )
            if not timeline:
                raise RuntimeError("ListMembers did not return a members timeline.")
            batch, cursor = extract_users_from_timeline(timeline)
            for user in batch:
                user_id = user.get("id")
                if user_id and user_id not in seen:
                    seen.add(user_id)
                    members.append(user)
                    if limit and len(members) >= limit:
                        return members
            if not cursor or not batch:
                return members

    def create_list(self, name: str, description: str = "", private: bool = False) -> XList:
        data = self.graphql(
            "CreateList",
            {"isPrivate": private, "name": name, "description": description},
            method="POST",
        )
        return normalize_list(data.get("data", {}).get("list"))

    def add_member(self, list_id: str, user_id: str) -> XList:
        try:
            data = self.graphql(
                "ListAddMember",
                {"listId": list_id, "userId": user_id},
                method="POST",
            )
        except RuntimeError as exc:
            if is_list_response_decode_error(str(exc)):
                return XList(id=list_id, name=None, member_count=None)
            raise
        return normalize_list(data.get("data", {}).get("list"))

    def graphql(
        self,
        operation: str,
        variables: dict,
        method: str = "GET",
        field_toggles: dict[str, bool] | None = None,
    ) -> dict:
        meta = self.operations[operation]
        toggles = dict(meta.field_toggles)
        toggles.update(field_toggles or {})
        payload = {"variables": variables, "features": meta.features}
        if toggles:
            payload["fieldToggles"] = toggles

        url = GRAPHQL_URL.format(query_id=meta.query_id, operation=operation)
        headers = self._headers()
        if method == "GET":
            query = urllib.parse.urlencode(
                {
                    key: json.dumps(value, separators=(",", ":"))
                    for key, value in payload.items()
                }
            )
            return self._request(url + "?" + query, headers=headers)

        headers = {**headers, "Content-Type": "application/json"}
        body = json.dumps(payload, separators=(",", ":")).encode()
        return self._request(url, data=body, headers=headers)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": "Bearer " + self.bearer_token,
            "Cookie": f"auth_token={self.auth_token}; ct0={self.ct0}",
            "X-Csrf-Token": self.ct0,
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Client-Language": "en",
            "User-Agent": USER_AGENT,
            "Referer": X_HOME,
        }

    def _request(
        self,
        url: str,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict:
        req = urllib.request.Request(url, data=data, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode()
        except urllib.error.HTTPError as err:
            body = err.read().decode(errors="replace")
            raise RuntimeError(f"X request failed HTTP {err.code}: {body[:1000]}") from err

        parsed = json.loads(body)
        if parsed.get("errors"):
            raise RuntimeError(
                f"X GraphQL error: {json.dumps(parsed['errors'], ensure_ascii=False)}"
            )
        return parsed


def normalize_list(list_obj: dict | None) -> XList:
    if not isinstance(list_obj, dict):
        raise RuntimeError("X did not return a list object.")
    legacy = list_obj.get("legacy") or {}
    list_id = list_obj.get("rest_id") or legacy.get("id_str")
    if not list_id:
        raise RuntimeError("X list object did not include a rest_id.")
    return XList(
        id=str(list_id),
        name=legacy.get("name") or list_obj.get("name"),
        member_count=legacy.get("member_count"),
    )


def fetch_current_bearer() -> str:
    html = _fetch_text(X_HOME)
    for url in _script_urls(html):
        text = _fetch_text(url)
        match = re.search(r"AAAA[A-Za-z0-9%+=_-]{80,}", text)
        if match:
            return urllib.parse.unquote(match.group(0))
    raise RuntimeError("Could not find the current X web bearer token.")


def discover_operations(names: list[str]) -> dict[str, GraphQLOperation]:
    remaining = set(names)
    found: dict[str, GraphQLOperation] = {}
    html = _fetch_text(X_HOME)

    for url in _script_urls(html):
        text = _fetch_text(url)
        for name in list(remaining):
            operation = _extract_operation(text, name)
            if operation:
                found[name] = operation
                remaining.remove(name)
        if not remaining:
            break

    if remaining:
        raise RuntimeError("Could not find X GraphQL operations: " + ", ".join(sorted(remaining)))
    return found


def _extract_operation(bundle: str, name: str) -> GraphQLOperation | None:
    pattern = (
        r'queryId:"(?P<query_id>[^"]+)",'
        r'operationName:"' + re.escape(name) + r'",'
        r'operationType:"(?P<operation_type>[^"]+)",'
        r"metadata:\{featureSwitches:\[(?P<features>[^\]]*)\]"
        r"(?:,fieldToggles:\[(?P<field_toggles>[^\]]*)\])?"
    )
    match = re.search(pattern, bundle)
    if not match:
        return None
    return GraphQLOperation(
        query_id=match.group("query_id"),
        operation_type=match.group("operation_type"),
        features={name: True for name in re.findall(r'"([^"]+)"', match.group("features"))},
        field_toggles={
            name: True
            for name in re.findall(r'"([^"]+)"', match.group("field_toggles") or "")
        },
    )


def _fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode(errors="replace")


def _script_urls(html: str) -> list[str]:
    urls = re.findall(r'https://abs\.twimg\.com/responsive-web/client-web/[^"\\]+\.js', html)
    seen: set[str] = set()
    ordered = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            ordered.append(url)
    return ordered
