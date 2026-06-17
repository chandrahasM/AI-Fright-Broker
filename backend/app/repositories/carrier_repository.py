from supabase import Client

TABLE = "carriers"


class CarrierRepository:
    def __init__(self, db: Client) -> None:
        self.db = db

    def get_by_mc_number(self, mc_number: str) -> dict | None:
        response = (
            self.db.table(TABLE)
            .select("*")
            .eq("mc_number", mc_number)
            .maybe_single()
            .execute()
        )
        return response.data or None
