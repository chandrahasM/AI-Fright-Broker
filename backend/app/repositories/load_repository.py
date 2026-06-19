from supabase import Client

TABLE = "loads"


class LoadRepository:
    def __init__(self, db: Client) -> None:
        self.db = db

    def get_by_load_id(self, load_id: str) -> dict | None:
        response = (
            self.db.table(TABLE)
            .select("*")
            .eq("load_id", load_id)
            .maybe_single()
            .execute()
        )
        return response.data or None

    def search(
        self,
        origin_state: str | None = None,
        destination_state: str | None = None,
        equipment_type: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Filter loads by any combination of lane, equipment, and status."""
        q = self.db.table(TABLE).select("*")
        if origin_state:
            q = q.eq("origin_state", origin_state)
        if destination_state:
            q = q.eq("destination_state", destination_state)
        if equipment_type:
            q = q.eq("equipment_type", equipment_type)
        if status:
            q = q.eq("status", status)
        return q.limit(limit).execute().data or []
