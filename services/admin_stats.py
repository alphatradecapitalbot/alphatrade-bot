from database.models import Database

db = Database()

def get_system_stats():
    """Returns a dictionary with global statistics for the admin panel."""
    return db.get_admin_global_stats()

def get_user_breakdown():
    """Returns a breakdown of users: total, active investors, and those without investment."""
    total, active, without_inv, capital = db.get_admin_user_sections()
    return {
        "total": total,
        "active": active,
        "without_inv": without_inv,
        "capital": capital
    }
