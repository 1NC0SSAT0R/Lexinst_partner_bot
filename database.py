import sqlite3
import os

class Database:
    def __init__(self):
        self.connection = sqlite3.connect('bot.db', check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        with self.connection:
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS partners (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    promo_code TEXT UNIQUE,
                    referrals INTEGER DEFAULT 0,
                    balance REAL DEFAULT 0,
                    is_active BOOLEAN DEFAULT FALSE,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER REFERENCES partners(user_id),
                    score INTEGER,
                    total_questions INTEGER,
                    passed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS withdrawal_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER REFERENCES partners(user_id),
                    amount REAL,
                    requisites TEXT,
                    comment TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP
                )
            """)
            
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS used_promo_codes (
                    promo_code TEXT PRIMARY KEY,
                    user_id INTEGER REFERENCES partners(user_id)
                )
            """)

    def add_partner(self, user_id, username, full_name):
        with self.connection:
            self.connection.execute("""
                INSERT OR IGNORE INTO partners (user_id, username, full_name) 
                VALUES (?, ?, ?)
            """, (user_id, username, full_name))

    def set_promo_code(self, user_id, promo_code):
        try:
            with self.connection:
                existing = self.connection.execute(
                    "SELECT * FROM used_promo_codes WHERE promo_code = ?", 
                    (promo_code,)
                ).fetchone()
                if existing:
                    return False
                
                self.connection.execute(
                    "INSERT INTO used_promo_codes (promo_code, user_id) VALUES (?, ?)", 
                    (promo_code, user_id)
                )
                
                self.connection.execute(
                    "UPDATE partners SET promo_code = ?, is_active = TRUE WHERE user_id = ?", 
                    (promo_code, user_id)
                )
                return True
        except:
            return False

    def get_partner(self, user_id):
        cursor = self.connection.execute("SELECT * FROM partners WHERE user_id = ?", (user_id,))
        return cursor.fetchone()

    def get_all_partners(self):
        cursor = self.connection.execute("SELECT * FROM partners ORDER BY registered_at DESC")
        return cursor.fetchall()

    def update_partner_stats(self, user_id, referrals_delta=0, balance_delta=0):
        with self.connection:
            self.connection.execute("""
                UPDATE partners 
                SET referrals = referrals + ?, balance = balance + ? 
                WHERE user_id = ?
            """, (referrals_delta, balance_delta, user_id))

    def set_partner_stats(self, user_id, referrals, balance):
        with self.connection:
            self.connection.execute("""
                UPDATE partners 
                SET referrals = ?, balance = ? 
                WHERE user_id = ?
            """, (referrals, balance, user_id))

    def save_test_result(self, user_id, score, total_questions):
        with self.connection:
            self.connection.execute("""
                INSERT INTO test_results (user_id, score, total_questions) 
                VALUES (?, ?, ?)
            """, (user_id, score, total_questions))

    def create_withdrawal_request(self, user_id, amount, requisites, comment):
        try:
            with self.connection:
                self.connection.execute("""
                    INSERT INTO withdrawal_requests (user_id, amount, requisites, comment) 
                    VALUES (?, ?, ?, ?)
                """, (user_id, amount, requisites, comment))
                return True
        except:
            return False

    def get_pending_withdrawals(self):
        cursor = self.connection.execute("""
            SELECT w.*, p.username, p.full_name 
            FROM withdrawal_requests w 
            JOIN partners p ON w.user_id = p.user_id 
            WHERE w.status = 'pending' 
            ORDER BY w.created_at DESC
        """)
        return cursor.fetchall()

    def complete_withdrawal(self, withdrawal_id):
        try:
            with self.connection:
                cursor = self.connection.execute(
                    "SELECT user_id, amount FROM withdrawal_requests WHERE id = ?", 
                    (withdrawal_id,)
                )
                withdrawal = cursor.fetchone()
                
                if withdrawal:
                    user_id, amount = withdrawal['user_id'], withdrawal['amount']
                    
                    self.connection.execute("""
                        UPDATE withdrawal_requests 
                        SET status = 'completed', processed_at = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    """, (withdrawal_id,))
                    
                    self.connection.execute("""
                        UPDATE partners 
                        SET balance = balance - ? 
                        WHERE user_id = ?
                    """, (amount, user_id))
                    
                    return True
            return False
        except Exception as e:
            print(f"Error completing withdrawal: {e}")
            return False

    def reject_withdrawal(self, withdrawal_id, reject_reason=None):
        try:
            with self.connection:
                if reject_reason:
                    # Добавляем причину отказа к существующему комментарию
                    cursor = self.connection.execute(
                        "SELECT comment FROM withdrawal_requests WHERE id = ?", 
                        (withdrawal_id,)
                    )
                    current_comment = cursor.fetchone()['comment'] or ''
                    
                    new_comment = f"{current_comment}\n\nПричина отказа: {reject_reason}".strip()
                    
                    self.connection.execute("""
                        UPDATE withdrawal_requests 
                        SET status = 'rejected', processed_at = CURRENT_TIMESTAMP, comment = ?
                        WHERE id = ?
                    """, (new_comment, withdrawal_id))
                else:
                    self.connection.execute("""
                        UPDATE withdrawal_requests 
                        SET status = 'rejected', processed_at = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    """, (withdrawal_id,))
                return True
        except Exception as e:
            print(f"Error rejecting withdrawal: {e}")
            return False

    def get_withdrawal_by_id(self, withdrawal_id):
        try:
            cursor = self.connection.execute("""
                SELECT w.*, p.username, p.full_name 
                FROM withdrawal_requests w 
                JOIN partners p ON w.user_id = p.user_id 
                WHERE w.id = ?
            """, (withdrawal_id,))
            return cursor.fetchone()
        except Exception as e:
            print(f"Error getting withdrawal by id: {e}")
            return None

    def search_partners(self, search_term):
        cursor = self.connection.execute("""
            SELECT * FROM partners 
            WHERE CAST(user_id AS TEXT) LIKE ? OR username LIKE ? OR promo_code LIKE ?
        """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
        return cursor.fetchall()