"""
Agent tool definitions and executor.

Two tool sets:
  CARRIER_TOOL_DEFINITIONS  — safe for inbound carrier email processing.
                              Only point lookups by known ID. No table scans.
  INTERNAL_TOOL_DEFINITIONS — for the internal chat/ops endpoint.
                              Includes search_loads for lane/status queries.

Tool definitions follow the OpenAI function-calling schema.
ToolExecutor holds the business logic for each tool, backed by repositories.
"""
import json
import logging
import time
from collections import Counter

from app.repositories.carrier_repository import CarrierRepository
from app.repositories.load_repository import LoadRepository
from app.repositories.rate_history_repository import RateHistoryRepository

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenAI tool schemas — carrier-safe (used in email / voice processing)
# ---------------------------------------------------------------------------

CARRIER_TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "name": "get_load_details",
        "description": (
            "Retrieve details for a freight load by its load ID. "
            "Returns equipment type, offered rate, and current status."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "load_id": {
                    "type": "string",
                    "description": "The load reference ID (e.g. '29372312')",
                }
            },
            "required": ["load_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_carrier_profile",
        "description": (
            "Retrieve a carrier's full profile by their MC number. "
            "Returns authority status, insurance expiry, reliability score, "
            "equipment types, preferred lanes, payment terms, and relationship history."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "mc_number": {
                    "type": "string",
                    "description": "The Motor Carrier number (e.g. '774321')",
                }
            },
            "required": ["mc_number"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_market_rate",
        "description": (
            "Get current market rate benchmarks for a lane. "
            "Returns average, minimum, and maximum rates in USD."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "origin_state": {
                    "type": "string",
                    "description": "Two-letter origin state abbreviation (e.g. 'TX')",
                },
                "destination_state": {
                    "type": "string",
                    "description": "Two-letter destination state abbreviation (e.g. 'FL')",
                },
                "equipment_type": {
                    "type": "string",
                    "description": "Equipment type (e.g. 'Sprinter Van', 'Dry Van', 'Reefer', 'Flatbed')",
                },
            },
            "required": ["origin_state", "destination_state", "equipment_type"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_rate_history",
        "description": (
            "Look up historical weekly per-mile rate data ($/mile) from Goodlane's internal rate database. "
            "Use this when a carrier asks about historical rates, average rates, lowest/highest rates, "
            "rate trends, or anything about what rates have been on a lane over time. "
            "All parameters are optional — pass null for any you don't know. "
            "If no matching data is found the tool returns an empty list; tell the carrier there is "
            "not enough data for that lane or time period."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "origin_state": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "description": "Two-letter origin state code (e.g. 'PA'). Null to match any.",
                },
                "destination_state": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "description": "Two-letter destination state code (e.g. 'MD'). Null to match any.",
                },
                "equipment_type": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "description": "Equipment type (e.g. 'Box Truck'). Null to match any.",
                },
                "week_start": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "description": "ISO date of a specific week's Monday (e.g. '2025-12-01'). Null for recent weeks.",
                },
                "weeks_back": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "description": "How many recent weeks to return (default 4). Ignored if week_start is set.",
                },
            },
            "required": ["origin_state", "destination_state", "equipment_type", "week_start", "weeks_back"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]

# ---------------------------------------------------------------------------
# Internal-only tools (chat / ops endpoint — never used for carrier emails)
# ---------------------------------------------------------------------------

_SEARCH_LOADS_DEFINITION: dict = {
    "type": "function",
    "name": "search_loads",
    "description": (
        "Search the Goodlane load board for loads matching any combination of "
        "origin state, destination state, equipment type, or status. "
        "Use this for operational questions like: 'any open loads from PA to NJ?', "
        "'how many loads are covered this week?', 'show me all flatbed loads'. "
        "Returns a count summary AND a sample of matching loads. "
        "Do NOT use this for carrier-facing email responses — only for internal ops queries."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "origin_state": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "description": "Two-letter origin state code (e.g. 'PA'). Null to match any.",
            },
            "destination_state": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "description": "Two-letter destination state code (e.g. 'NJ'). Null to match any.",
            },
            "equipment_type": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "description": "Equipment type (e.g. 'Box Truck', 'Flatbed'). Null to match any.",
            },
            "status": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "description": "Load status filter: 'open', 'covered', 'delivered', or null for all.",
            },
        },
        "required": ["origin_state", "destination_state", "equipment_type", "status"],
        "additionalProperties": False,
    },
    "strict": True,
}

# Full set available to internal chat — carrier tools + search
INTERNAL_TOOL_DEFINITIONS: list[dict] = CARRIER_TOOL_DEFINITIONS + [_SEARCH_LOADS_DEFINITION]

# Backwards-compatible alias so existing imports keep working unchanged
TOOL_DEFINITIONS = CARRIER_TOOL_DEFINITIONS


# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------

class ToolExecutor:
    """Executes agent tool calls using repository data."""

    def __init__(
        self,
        load_repo: LoadRepository,
        carrier_repo: CarrierRepository,
        rate_history_repo: RateHistoryRepository,
    ) -> None:
        self.load_repo = load_repo
        self.carrier_repo = carrier_repo
        self.rate_history_repo = rate_history_repo

    def execute(self, name: str, arguments_json: str) -> str:
        """Execute a named tool and return the result as a JSON string."""
        try:
            arguments = json.loads(arguments_json)
            logger.debug("tool=%s  args=%s", name, json.dumps(arguments))
            t0 = time.perf_counter()
            result = self._dispatch(name, arguments)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            logger.info("tool=%s  elapsed=%.1fms  status=ok", name, elapsed_ms)
            logger.debug("tool=%s  result=%s", name, json.dumps(result))
            return json.dumps(result)
        except Exception as exc:
            logger.warning("tool=%s  status=error  reason=%s", name, exc)
            return json.dumps({"error": str(exc)})

    def _dispatch(self, name: str, arguments: dict) -> dict | list:
        if name == "get_load_details":
            return self._get_load_details(**arguments)
        if name == "get_carrier_profile":
            return self._get_carrier_profile(**arguments)
        if name == "get_market_rate":
            return self._get_market_rate(**arguments)
        if name == "get_rate_history":
            return self._get_rate_history(**arguments)
        if name == "search_loads":
            return self._search_loads(**arguments)
        raise ValueError(f"Unknown tool: {name}")

    def _get_load_details(self, load_id: str) -> dict:
        load = self.load_repo.get_by_load_id(load_id)
        if not load:
            return {"error": f"Load {load_id} not found"}
        return {
            "load_id": load["load_id"],
            "origin": f"{load.get('origin_city', '')}, {load.get('origin_state', '')} {load.get('origin_zip', '')}".strip(", "),
            "destination": f"{load.get('destination_city', '')}, {load.get('destination_state', '')} {load.get('destination_zip', '')}".strip(", "),
            "origin_state": load.get("origin_state"),
            "destination_state": load.get("destination_state"),
            "distance_miles": load.get("distance_miles"),
            "equipment_type": load.get("equipment_type"),
            "weight_lbs": load.get("weight_lbs"),
            "pickup_date": str(load.get("pickup_date", "")),
            "pickup_window": load.get("pickup_window"),
            "delivery_date": str(load.get("delivery_date", "")) if load.get("delivery_date") else None,
            "offered_rate_usd": load.get("offered_rate_usd"),
            "status": load.get("status"),
            "shipper_name": load.get("shipper_name"),
            "internal_notes": load.get("internal_notes"),
        }

    def _get_carrier_profile(self, mc_number: str) -> dict:
        carrier = self.carrier_repo.get_by_mc_number(mc_number)
        if not carrier:
            return {"error": f"Carrier MC#{mc_number} not found"}
        return {
            "mc_number": carrier.get("mc_number"),
            "dot_number": carrier.get("dot_number"),
            "company_name": carrier.get("company_name"),
            "primary_contact": carrier.get("primary_contact"),
            "email": carrier.get("email"),
            "phone": carrier.get("phone"),
            "address": carrier.get("address"),
            "equipment_types": carrier.get("equipment_types", []),
            "preferred_lanes": carrier.get("preferred_lanes", []),
            "home_base_zip": carrier.get("home_base_zip"),
            "factoring_company": carrier.get("factoring_company"),
            "payment_terms_preference": carrier.get("payment_terms_preference"),
            "reliability_score": carrier.get("reliability_score"),
            "loads_completed_with_goodlane": carrier.get("loads_completed_with_goodlane"),
            "avg_response_time_hours": carrier.get("avg_response_time_hours"),
            "insurance_expiry": str(carrier.get("insurance_expiry", "")),
            "authority_status": carrier.get("authority_status"),
            "safety_rating": carrier.get("safety_rating"),
            "onboarded": carrier.get("onboarded"),
            "notes": carrier.get("notes"),
        }

    def _get_market_rate(self, origin_state: str, destination_state: str, equipment_type: str) -> dict:
        # In production this would call DAT, Truckstop, or similar market data API.
        # For V1 we use static benchmarks by equipment type.
        benchmarks: dict[str, tuple[int, int]] = {
            "Dry Van":      (200, 350),
            "Reefer":       (250, 450),
            "Refrigerated": (250, 450),  # same as Reefer
            "Flatbed":      (220, 380),
            "Sprinter Van": (150, 280),
            "Box Truck":    (180, 320),
        }
        min_rate, max_rate = benchmarks.get(equipment_type, (200, 350))
        avg_rate = round((min_rate + max_rate) / 2)
        return {
            "lane": f"{origin_state} → {destination_state}",
            "equipment_type": equipment_type,
            "avg_rate": avg_rate,
            "min_rate": min_rate,
            "max_rate": max_rate,
        }

    def _get_rate_history(
        self,
        origin_state: str | None,
        destination_state: str | None,
        equipment_type: str | None,
        week_start: str | None,
        weeks_back: int | None,
    ) -> dict:
        rows = self.rate_history_repo.query(
            origin_state=origin_state,
            destination_state=destination_state,
            equipment_type=equipment_type,
            week_start=week_start,
            weeks_back=weeks_back or 4,
        )

        if not rows:
            filters = ", ".join(filter(None, [
                f"lane={origin_state}→{destination_state}" if origin_state and destination_state else None,
                f"equipment={equipment_type}" if equipment_type else None,
                f"week={week_start}" if week_start else f"last {weeks_back or 4} weeks",
            ]))
            return {"data": [], "message": f"No rate history found for: {filters}"}

        # Surface a quick summary alongside the raw rows
        avg_rates = [r["avg_rate"] for r in rows if r.get("avg_rate") is not None]
        min_rates = [r["min_rate"] for r in rows if r.get("min_rate") is not None]
        max_rates = [r["max_rate"] for r in rows if r.get("max_rate") is not None]

        return {
            "weeks_returned": len(rows),
            "summary": {
                "overall_avg_rate": round(sum(avg_rates) / len(avg_rates), 2) if avg_rates else None,
                "overall_min_rate": round(min(min_rates), 2) if min_rates else None,
                "overall_max_rate": round(max(max_rates), 2) if max_rates else None,
            },
            "data": [
                {
                    "week_start": str(r.get("week_start", "")),
                    "origin_state": r.get("origin_state"),
                    "destination_state": r.get("destination_state"),
                    "equipment_type": r.get("equipment_type"),
                    "avg_rate": r.get("avg_rate"),
                    "min_rate": r.get("min_rate"),
                    "max_rate": r.get("max_rate"),
                    "load_volume": r.get("load_volume"),
                }
                for r in rows
            ],
        }

    def _search_loads(
        self,
        origin_state: str | None,
        destination_state: str | None,
        equipment_type: str | None,
        status: str | None,
    ) -> dict:
        rows = self.load_repo.search(
            origin_state=origin_state,
            destination_state=destination_state,
            equipment_type=equipment_type,
            status=status,
            limit=20,
        )

        if not rows:
            filters = ", ".join(filter(None, [
                f"origin={origin_state}" if origin_state else None,
                f"destination={destination_state}" if destination_state else None,
                f"equipment={equipment_type}" if equipment_type else None,
                f"status={status}" if status else None,
            ]))
            return {"total_count": 0, "summary": {}, "loads": [],
                    "message": f"No loads found for: {filters or 'no filters'}"}

        # Build aggregate summary so the LLM can answer count/breakdown questions
        # without the model needing to count rows itself.
        by_status = dict(Counter(r.get("status", "unknown") for r in rows))
        by_equipment = dict(Counter(r.get("equipment_type", "unknown") for r in rows))
        rates = [r["offered_rate_usd"] for r in rows if r.get("offered_rate_usd") is not None]

        return {
            "total_count": len(rows),
            "summary": {
                "by_status": by_status,
                "by_equipment_type": by_equipment,
                "avg_offered_rate_usd": round(sum(rates) / len(rates), 2) if rates else None,
                "min_offered_rate_usd": round(min(rates), 2) if rates else None,
                "max_offered_rate_usd": round(max(rates), 2) if rates else None,
            },
            # Cap sample to 5 loads — enough context for the LLM without dumping the table
            "loads": [
                {
                    "load_id": r.get("load_id"),
                    "origin": f"{r.get('origin_city', '')}, {r.get('origin_state', '')}",
                    "destination": f"{r.get('destination_city', '')}, {r.get('destination_state', '')}",
                    "equipment_type": r.get("equipment_type"),
                    "offered_rate_usd": r.get("offered_rate_usd"),
                    "status": r.get("status"),
                    "pickup_date": str(r.get("pickup_date", "")),
                    "distance_miles": r.get("distance_miles"),
                }
                for r in rows[:5]
            ],
        }
