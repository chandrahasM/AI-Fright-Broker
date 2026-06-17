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
