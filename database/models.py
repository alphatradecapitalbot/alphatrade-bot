import sqlite3
import logging
from datetime import datetime
from config import DB_PATH

logger = logging.getLogger(__name__)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        registration_date DATETIME,
        referral_id INTEGER,
        referral_count INTEGER DEFAULT 0,
        balance REAL DEFAULT 0.0,
        referral_earnings REAL DEFAULT 0.0,
        active_investment BOOLEAN DEFAULT 0,
        FOREIGN KEY (referral_id) REFERENCES users (id)
    )
    ''')
    
    # Deposits table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS deposits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        plan TEXT,
        amount REAL,
        profit REAL,
        total_return REAL,
        duration TEXT DEFAULT '24h',
        network TEXT, -- TRC20
        tx_hash TEXT,
        proof_type TEXT,
        proof_data TEXT,
        deposit_method TEXT,
        status TEXT DEFAULT 'pending', -- pending, confirmed, rejected
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Withdrawals table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        wallet TEXT,
        status TEXT, -- pending, paid, rejected
        txid TEXT,
        paid_at DATETIME,
        timestamp DATETIME,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Investments table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS investments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        plan TEXT,
        amount REAL,
        profit REAL DEFAULT 0.0,
        total REAL DEFAULT 0.0,
        start_time DATETIME,
        end_time DATETIME,
        status TEXT, -- pending, active, completed, rejected
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Migration: Add columns if they don't exist
    columns_to_add = [
        ("deposits", "plan", "TEXT"),
        ("deposits", "profit", "REAL"),
        ("deposits", "total_return", "REAL"),
        ("deposits", "duration", "TEXT DEFAULT '24h'"),
        ("investments", "plan", "TEXT"),
        ("withdrawals", "txid", "TEXT"),
        ("withdrawals", "paid_at", "DATETIME"),
        ("users", "referral_count", "INTEGER DEFAULT 0")
    ]
    for table, col, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass # Already exists

    # Settings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')

    # Payments table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        status TEXT DEFAULT 'Pagado',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Used TXIDs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS used_txids (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        txid TEXT UNIQUE,
        user_id INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Operation History
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS operation_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        result TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def get_setting(self, key, default=None):
        self.cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = self.cursor.fetchone()
        return row['value'] if row else default

    def update_setting(self, key, value):
        self.cursor.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value)
        )
        self.conn.commit()

    def register_user(self, user_id, username, referral_id=None):
        user = self.get_user(user_id)
        if not user:
            self.cursor.execute(
                "INSERT INTO users (id, username, registration_date, referral_id) VALUES (?, ?, ?, ?)",
                (user_id, username, datetime.now(), referral_id)
            )
            self.conn.commit()
            return True
        else:
            # Update username if it has changed
            if user['username'] != username:
                self.cursor.execute(
                    "UPDATE users SET username = ? WHERE id = ?",
                    (username, user_id)
                )
                self.conn.commit()
            return False

    def get_user(self, user_id):
        self.cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return self.cursor.fetchone()

    def get_all_users(self):
        self.cursor.execute("SELECT * FROM users")
        return self.cursor.fetchall()

    def add_deposit(self, user_id, amount, network, tx_hash, proof_type, proof_data, deposit_method, plan=None, profit=None, total_return=None):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO deposits (user_id, plan, amount, profit, total_return, network, tx_hash, proof_type, proof_data, deposit_method, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, plan, amount, profit, total_return, network, tx_hash, proof_type, proof_data, deposit_method, 'pending')
            )
            return cursor.lastrowid

    def update_deposit_status(self, deposit_id, status):
        self.cursor.execute("UPDATE deposits SET status = ? WHERE id = ?", (status, deposit_id))
        self.conn.commit()

    def add_investment(self, user_id, amount, profit, total):
        from datetime import timedelta
        from config import INVESTMENT_DURATION
        start = datetime.now()
        end = start + timedelta(hours=INVESTMENT_DURATION)
        self.cursor.execute(
            "INSERT INTO investments (user_id, amount, profit, total, start_time, end_time, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, amount, profit, total, start, end, 'active')
        )
        self.conn.commit()

    def create_investment(self, user_id, capital, profit, start_time, end_time, status, plan=None):
        total = capital + profit
        self.cursor.execute(
            "INSERT INTO investments (user_id, plan, amount, profit, total, start_time, end_time, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, plan, capital, profit, total, start_time, end_time, status)
        )
        self.conn.commit()

    def get_investment_history(self, user_id):
        self.cursor.execute(
            "SELECT * FROM investments WHERE user_id = ? ORDER BY start_time DESC",
            (user_id,)
        )
        return self.cursor.fetchall()

    def get_active_investment(self, user_id):
        self.cursor.execute("SELECT * FROM investments WHERE user_id = ? AND status = 'active' LIMIT 1", (user_id,))
        return self.cursor.fetchone()

    def set_user_active_investment(self, user_id, active):
        val = 1 if active else 0
        self.cursor.execute("UPDATE users SET active_investment = ? WHERE id = ?", (val, user_id))
        self.conn.commit()

    def is_cycle_active(self, user_id):
        self.cursor.execute("SELECT 1 FROM investments WHERE user_id = ? AND status = 'active'", (user_id,))
        return self.cursor.fetchone() is not None

    def is_txid_used(self, txid: str) -> bool:
        self.cursor.execute("SELECT id FROM used_txids WHERE txid = ?", (txid,))
        return self.cursor.fetchone() is not None

    def mark_txid_used(self, txid: str, user_id: int):
        try:
            self.cursor.execute("INSERT INTO used_txids (txid, user_id) VALUES (?, ?)", (txid, user_id))
            self.conn.commit()
        except Exception:
            pass

    def handle_referral(self, user_id, amount):
        user = self.get_user(user_id)
        if user and user['referral_id']:
            from config import REFERRAL_PERCENTAGE
            commission = amount * REFERRAL_PERCENTAGE
            self.cursor.execute(
                "UPDATE users SET referral_earnings = referral_earnings + ? WHERE id = ?",
                (commission, user['referral_id'])
            )
            self.conn.commit()

    def add_referral_reward(self, referrer_id, reward_amount):
        self.cursor.execute(
            "UPDATE users SET referral_earnings = referral_earnings + ?, referral_count = referral_count + ? WHERE id = ?",
            (reward_amount, 1, referrer_id)
        )
        self.conn.commit()

    def get_user_stats(self, user_id):
        user = self.get_user(user_id)
        self.cursor.execute("SELECT * FROM investments WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
        investment = self.cursor.fetchone()
        
        return {
            "balance": user['balance'] if user else 0.0,
            "investment": investment,
            "referral_count": user['referral_count'] if user else 0,
            "referral_earnings": user['referral_earnings'] if user else 0.0
        }

    def get_all_stats(self):
        self.cursor.execute("SELECT COUNT(*) FROM users")
        total_users = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT SUM(amount) FROM investments WHERE status = 'active'")
        total_invested = self.cursor.fetchone()[0] or 0.0
        self.cursor.execute("SELECT COUNT(*) FROM withdrawals WHERE status = 'paid'")
        total_withdrawals = self.cursor.fetchone()[0]
        
        return {
            "total_users": total_users,
            "total_invested": total_invested,
            "total_withdrawals": total_withdrawals
        }

    def get_ranking(self):
        self.cursor.execute('''
            SELECT u.username, SUM(i.profit) as total_profit
            FROM users u
            JOIN investments i ON u.id = i.user_id
            WHERE i.status = 'completed'
            GROUP BY u.id
            ORDER BY total_profit DESC
            LIMIT 10
        ''')
        return self.cursor.fetchall()

    def add_operation_record(self, title, result):
        self.cursor.execute(
            "INSERT INTO operation_history (title, result) VALUES (?, ?)",
            (title, result)
        )
        self.conn.commit()

    def get_operation_history(self):
        self.cursor.execute("SELECT * FROM operation_history ORDER BY timestamp DESC LIMIT 10")
        return self.cursor.fetchall()

    def process_matured_investments(self):
        now = datetime.now()
        self.cursor.execute("SELECT * FROM investments WHERE status = 'active' AND end_time <= ?", (now,))
        matured = self.cursor.fetchall()
        
        results = []
        for inv in matured:
            inv_id = inv['id']
            user_id = inv['user_id']
            total_payout = inv['total']
            
            self.cursor.execute("UPDATE investments SET status = 'completed' WHERE id = ?", (inv_id,))
            self.cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (total_payout, user_id))
            self.cursor.execute("INSERT INTO payments (user_id, amount) VALUES (?, ?)", (user_id, total_payout))
            
            results.append({
                'user_id': user_id,
                'amount': total_payout,
                'capital': inv['amount'],
                'profit': inv['profit'],
                'inv_id': inv_id
            })
            
        if matured:
            self.conn.commit()
        return results

    def subtract_user_balance(self, user_id, amount):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, user_id))
            self.conn.commit()

    def add_withdrawal(self, user_id, amount, wallet):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO withdrawals (user_id, amount, wallet, status, timestamp) VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, wallet, 'pending', datetime.now())
            )
            return cursor.lastrowid

    def has_pending_withdrawal(self, user_id):
        self.cursor.execute("SELECT 1 FROM withdrawals WHERE user_id = ? AND status = 'pending'", (user_id,))
        return self.cursor.fetchone() is not None

    def get_pending_deposits(self):
        self.cursor.execute("SELECT d.*, u.username FROM deposits d JOIN users u ON d.user_id = u.id WHERE d.status = 'pending'")
        return self.cursor.fetchall()

    def get_pending_withdrawals(self):
        self.cursor.execute("SELECT w.*, u.username FROM withdrawals w JOIN users u ON w.user_id = u.id WHERE w.status = 'pending'")
        return self.cursor.fetchall()

    # --- New User History Methods ---

    def get_user_deposits(self, user_id):
        self.cursor.execute(
            "SELECT * FROM deposits WHERE user_id = ? ORDER BY timestamp DESC",
            (user_id,)
        )
        return self.cursor.fetchall()

    def get_user_withdrawals(self, user_id):
        self.cursor.execute(
            "SELECT * FROM withdrawals WHERE user_id = ? ORDER BY timestamp DESC",
            (user_id,)
        )
        return self.cursor.fetchall()

    # --- Improved Admin Monitoring Methods ---

    def get_admin_recent_deposits(self, limit=10):
        self.cursor.execute('''
            SELECT d.*, u.username 
            FROM deposits d 
            JOIN users u ON d.user_id = u.id 
            ORDER BY d.timestamp DESC 
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()

    def get_admin_recent_withdrawals(self, limit=10):
        self.cursor.execute('''
            SELECT w.*, u.username 
            FROM withdrawals w 
            JOIN users u ON w.user_id = u.id 
            ORDER BY w.timestamp DESC 
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()

    def get_admin_user_sections(self):
        """Returns total users, active investors, and users without investment."""
        self.cursor.execute("SELECT COUNT(*) FROM users")
        total = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(DISTINCT user_id) FROM investments WHERE status = 'active'")
        active_investors = self.cursor.fetchone()[0]
        
        without_inv = total - active_investors
        
        self.cursor.execute("SELECT SUM(amount) FROM investments WHERE status = 'active'")
        total_capital = self.cursor.fetchone()[0] or 0.0
        
        return total, active_investors, without_inv, total_capital

    def get_recent_verified_deposits(self, limit=10):
        self.cursor.execute('''
            SELECT d.*, u.username 
            FROM deposits d 
            JOIN users u ON d.user_id = u.id 
            WHERE d.status = 'confirmed' 
            ORDER BY d.timestamp DESC 
            LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()

    def get_admin_active_investments(self):
        self.cursor.execute('''
            SELECT i.*, u.username 
            FROM investments i 
            JOIN users u ON i.user_id = u.id 
            WHERE i.status = 'active'
            ORDER BY i.start_time DESC
        ''')
        return self.cursor.fetchall()

    def search_user_info(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return None
            
        self.cursor.execute("SELECT SUM(amount) FROM deposits WHERE user_id = ? AND status = 'confirmed'", (user_id,))
        total_invested = self.cursor.fetchone()[0] or 0.0
        
        self.cursor.execute("SELECT SUM(profit) FROM investments WHERE user_id = ? AND status = 'completed'", (user_id,))
        total_profit = self.cursor.fetchone()[0] or 0.0
        
        self.cursor.execute("SELECT SUM(amount) FROM withdrawals WHERE user_id = ? AND status = 'paid'", (user_id,))
        total_withdrawn = self.cursor.fetchone()[0] or 0.0
        
        self.cursor.execute("SELECT COUNT(*) FROM investments WHERE user_id = ? AND status = 'active'", (user_id,))
        active_count = self.cursor.fetchone()[0]
        
        return {
            "id": user_id,
            "username": user['username'],
            "total_invested": total_invested,
            "total_withdrawn": total_withdrawn,
            "active_investments": active_count,
            "referral_earnings": user['referral_earnings']
        }

    def get_admin_global_stats(self):
        self.cursor.execute("SELECT COUNT(*) FROM users")
        total_users = self.cursor.fetchone()[0]
        
        # total_capital → sum(investments.amount)
        self.cursor.execute("SELECT SUM(amount) FROM investments")
        total_capital = self.cursor.fetchone()[0] or 0.0
        
        # total_profit → sum(withdrawals.amount where status = paid)
        self.cursor.execute("SELECT SUM(amount) FROM withdrawals WHERE status = 'paid'")
        total_profit = self.cursor.fetchone()[0] or 0.0
        
        # active_investments → count(investments where status = active)
        self.cursor.execute("SELECT COUNT(*) FROM investments WHERE status = 'active'")
        active_investments = self.cursor.fetchone()[0]

        # total_deposits → sum(deposits.amount where status = approved)
        # In our DB 'confirmed' is the 'approved' status for deposits
        self.cursor.execute("SELECT SUM(amount) FROM deposits WHERE status = 'confirmed'")
        total_deposits = self.cursor.fetchone()[0] or 0.0

        # total_withdrawals → sum(withdrawals.amount where status = paid)
        self.cursor.execute("SELECT SUM(amount) FROM withdrawals WHERE status = 'paid'")
        total_withdrawals = self.cursor.fetchone()[0] or 0.0

        # pending_deposits → count(deposits where status = pending)
        self.cursor.execute("SELECT COUNT(*) FROM deposits WHERE status = 'pending'")
        pending_deposits = self.cursor.fetchone()[0]

        # pending_withdrawals → count(withdrawals where status = pending)
        self.cursor.execute("SELECT COUNT(*) FROM withdrawals WHERE status = 'pending'")
        pending_withdrawals = self.cursor.fetchone()[0]
        
        # today_capital → sum(investments.amount where date = today)
        self.cursor.execute("SELECT SUM(amount) FROM investments WHERE date(start_time) = date('now')")
        today_capital = self.cursor.fetchone()[0] or 0.0

        # total_referral_rewards
        self.cursor.execute("SELECT SUM(referral_earnings) FROM users")
        total_referral_rewards = self.cursor.fetchone()[0] or 0.0
        
        return {
            "total_users": total_users,
            "total_capital": total_capital,
            "total_profit": total_profit,
            "active_investments": active_investments,
            "total_deposits": total_deposits,
            "total_withdrawals": total_withdrawals,
            "pending_deposits": pending_deposits,
            "pending_withdrawals": pending_withdrawals,
            "today_capital": today_capital,
            "total_referral_rewards": total_referral_rewards
        }

    def get_withdraw(self, withdrawal_id):
        self.cursor.execute("SELECT * FROM withdrawals WHERE id = ?", (withdrawal_id,))
        return self.cursor.fetchone()

    def update_withdraw_status(self, withdrawal_id, status, txid=None):
        if status == 'paid':
            self.cursor.execute(
                "UPDATE withdrawals SET status = ?, txid = ?, paid_at = ? WHERE id = ?",
                (status, txid, datetime.now(), withdrawal_id)
            )
        else:
            self.cursor.execute("UPDATE withdrawals SET status = ? WHERE id = ?", (status, withdrawal_id))
        self.conn.commit()

    def add_user_balance(self, user_id, amount):
        self.cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))
        self.conn.commit()

    def __del__(self):
        try:
            self.conn.close()
        except:
            pass
