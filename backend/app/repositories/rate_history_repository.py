from datetime import date, timedelta

from supabase import Client

TABLE = "rate_history"


class RateHistoryRepository:
    def __init__(self, db: Client) -> None:
        self.db = db

    def query(
        self,
        origin_state: str | None = None,
        destination_state: str | None = None,
        equipment_type: str | None = None,
        week_start: str | None = None,   # ISO date string, e.g. "2025-12-01"
        weeks_back: int = 4,
    ) -> list[dict]:
        """
        Return rate_history rows matching the given filters.
        - If week_start is given, return only that week.
        - Otherwise return the most recent `weeks_back` weeks.
        - Unspecified lane/equipment filters are not applied (any value matches).
        """
        q = self.db.table(TABLE).select("*")

        if origin_state:
            q = q.eq("origin_state", origin_state.upper())
        if destination_state:
            q = q.eq("destination_state", destination_state.upper())
        if equipment_type:
            q = q.eq("equipment_type", equipment_type)

        if week_start:
            q = q.eq("week_start", week_start)
        else:
            # Default: most recent N weeks
            cutoff = date.today() - timedelta(weeks=weeks_back)
            q = q.gte("week_start", cutoff.isoformat())

        rows = q.order("week_start", desc=True).execute().data
        return rows or []
