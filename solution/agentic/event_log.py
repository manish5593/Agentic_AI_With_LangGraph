"""Structured, searchable log of every agent decision.

Each event is one JSON object per line (JSON Lines) in `config.EVENT_LOG_PATH`, with a fixed set of
fields (`ts`, `ticket_id`, `agent`, `event`, `message`) plus event-specific ones such as `route`,
`reason`, `tools`, `articles` or `status`. The file can be searched with `search_events()`, `jq` or
`grep`, or loaded straight into a dataframe.
"""
import json
import logging
from datetime import datetime, timezone

from agentic import config

logger = logging.getLogger("udahub")


def log_event(ticket_id, agent: str, event: str, message: str, **fields) -> dict:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "ticket_id": ticket_id,
        "agent": agent,
        "event": event,
        "message": message,
        **fields,
    }
    try:
        path = config.EVENT_LOG_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str, ensure_ascii=False) + "\n")
    except OSError:
        # Logging must never break ticket handling
        logger.exception("Could not write the event log")
    logger.info(message)
    return record


def read_events() -> list[dict]:
    try:
        with config.EVENT_LOG_PATH.open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []


def search_events(text: str = None, since: str = None, **filters) -> list[dict]:
    """Events matching every filter, oldest first.

    Filters compare a field for equality, e.g. `search_events(ticket_id="demo-5")` or
    `search_events(agent="escalation_agent", event="escalate")`. A list field matches if it contains
    the value, e.g. `search_events(tools="request_refund")`. `text` searches the message, and `since`
    (an ISO timestamp) keeps only newer events.
    """
    def matches(e: dict) -> bool:
        for key, want in filters.items():
            have = e.get(key)
            if isinstance(have, list):
                names = [x.get("tool") or x.get("title") if isinstance(x, dict) else x for x in have]
                if want not in names:
                    return False
            elif have != want:
                return False
        if since and e["ts"] < since:
            return False
        return text is None or text.lower() in e.get("message", "").lower()
    return [e for e in read_events() if matches(e)]
