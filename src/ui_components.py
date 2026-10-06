"""Accessible, role-aware app navigation rendered by Streamlit HTML."""
from __future__ import annotations

import html

_ACTION_ROUTES = {
    "report": ("Report Complaint", frozenset({"citizen", "officer", "administrator", "demo"})),
    "track": ("Track Complaint", frozenset({"citizen", "officer", "administrator", "demo"})),
    "help": ("Help Center", frozenset({"citizen", "officer", "administrator", "demo"})),
    "inbox": ("Agency Portal", frozenset({"officer", "administrator", "demo"})),
    "map": ("Live Map", frozenset({"citizen", "officer", "administrator", "demo"})),
    "notifications": ("Notifications", frozenset({"officer", "administrator", "demo"})),
}


def floating_action_target(action: str, role: str) -> str | None:
    """Resolve a query-parameter route only when its server-side role allows it."""
    route = _ACTION_ROUTES.get(str(action).strip().casefold())
    if route is None or role not in route[1]:
        return None
    return route[0]


def floating_action_markup(role: str, unread_count: int = 0) -> str:
    """Return fixed quick-action links appropriate to the authenticated role."""
    if role == "citizen":
        actions = [
            ("report", "Report an issue", "＋", "primary"),
            ("track", "Track request", "◷", "secondary"),
            ("help", "Help", "?", "secondary"),
        ]
        navigation_label = "Citizen quick actions"
    elif role in {"officer", "administrator"}:
        actions = [
            ("inbox", "Inbox", "▤", "primary"),
            ("map", "Map", "⌖", "secondary"),
            ("notifications", "Notifications", "♧", "secondary"),
        ]
        navigation_label = "Agency quick actions"
    else:
        return ""

    primary = actions[0]
    links = []
    for action, label, icon, kind in actions:
        badge = ""
        if action == "notifications":
            count = max(0, int(unread_count))
            badge = f'<span class="fab-badge" aria-label="{count} unread notifications">{count if count < 100 else "99+"}</span>' if count else ""
        links.append(
            f'<a class="fab-action fab-{kind}" href="?nav={action}" '
            f'aria-label="{html.escape(label, quote=True)}" title="{html.escape(label, quote=True)}">'
            f'<span class="fab-icon" aria-hidden="true">{html.escape(icon)}</span>'
            f'<span>{html.escape(label)}</span>{badge}</a>'
        )
    primary_link = links[0]
    secondary_links = "".join(links[1:])
    return (
        f'<nav class="civic-fab" aria-label="{navigation_label}">'
        f'<div class="fab-secondary">{secondary_links}</div>{primary_link}</nav>'
    )
