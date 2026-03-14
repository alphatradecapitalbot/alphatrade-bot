from database.models import Database

db = Database()

def get_system_stats():
    """Returns a dictionary with global statistics for the admin panel."""
    stats = db.get_admin_global_stats()
    return {
        "users": stats['users'],
        "capital": stats['capital'],
        "paid": stats['paid'],
        "active_inv": stats['active_inv'],
        "total_deposits": stats['total_deposits'],
        "total_withdrawals": stats['total_withdrawals'],
        "pending_deposits": stats['pending_deposits'],
        "pending_withdrawals": stats['pending_withdrawals']
    }

def get_user_breakdown():
    """Returns a breakdown of users: total, active investors, and those without investment."""
    total, active, without_inv, capital = db.get_admin_user_sections()
    return {
        "total": total,
        "active": active,
        "without_inv": without_inv,
        "capital": capital
    }
