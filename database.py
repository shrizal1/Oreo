import mysql.connector


def connect_db(_with_db: bool = True):
    if _with_db:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="mkkapri",
            database="oreo",
        )
    # Server-level connection (used during bootstrap before DB exists)
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="mkkapri",
    )


def create_database():
    connection = connect_db(_with_db=False)
    cursor = connection.cursor()

    cursor.execute("CREATE DATABASE IF NOT EXISTS oreo;")
    cursor.execute("USE oreo;")

    # USERS Table (used for staff + members)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) NOT NULL,
            email VARCHAR(150) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            phone VARCHAR(20),
            address TEXT
        );
        """
    )

    # Add membership / role columns to users if missing
    def _ensure_user_membership_columns():
        def _ensure(col, ddl):
            cursor.execute("SHOW COLUMNS FROM users LIKE %s", (col,))
            exists = cursor.fetchone() is not None
            if not exists:
                cursor.execute(ddl)

        # staff vs member
        _ensure(
            "role",
            "ALTER TABLE users "
            "ADD COLUMN role ENUM('admin', 'employee', 'member') DEFAULT 'member'"
        )
        # public membership number (customer shows this at checkout)
        _ensure(
            "member_number",
            "ALTER TABLE users "
            "ADD COLUMN member_number VARCHAR(50) UNIQUE NULL"
        )
        # loyalty tier
        _ensure(
            "membership_level",
            "ALTER TABLE users "
            "ADD COLUMN membership_level ENUM('Bronze','Silver','Gold') "
            "DEFAULT 'Bronze'"
        )

    _ensure_user_membership_columns()

    # CATEGORY Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS category (
            category_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT
        );
        """
    )

    # PRODUCTS Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS product (
            product_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            description TEXT,
            price DECIMAL(10,2) NOT NULL,
            stock INT DEFAULT 0,
            category_id INT,
            details VARCHAR(255),
            image_url VARCHAR(255),
            FOREIGN KEY (category_id) REFERENCES category(category_id) ON DELETE SET NULL
        );
        """
    )

    # CART Table (linked to staff user_id who is operating the POS)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cart (
            cart_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            product_id INT,
            quantity INT DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES product(product_id) ON DELETE CASCADE
        );
        """
    )

    # ORDERS Table – now has member_id + discount + net_amount
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            order_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            total_amount DECIMAL(10,2) NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status ENUM('Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled') DEFAULT 'Pending',
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
        );
        """
    )

    def _ensure_orders_extra_columns():
        def _ensure(col, ddl):
            cursor.execute("SHOW COLUMNS FROM orders LIKE %s", (col,))
            exists = cursor.fetchone() is not None
            if not exists:
                cursor.execute(ddl)

        _ensure(
            "member_id",
            "ALTER TABLE orders "
            "ADD COLUMN member_id INT NULL AFTER user_id"
        )
        _ensure(
            "discount_amount",
            "ALTER TABLE orders "
            "ADD COLUMN discount_amount DECIMAL(10,2) DEFAULT 0 AFTER total_amount"
        )
        _ensure(
            "net_amount",
            "ALTER TABLE orders "
            "ADD COLUMN net_amount DECIMAL(10,2) DEFAULT 0 AFTER discount_amount"
        )

        # Add FK for member_id (ignore if already exists)
        try:
            cursor.execute(
                "ALTER TABLE orders "
                "ADD CONSTRAINT fk_orders_member "
                "FOREIGN KEY (member_id) REFERENCES users(user_id) "
                "ON DELETE SET NULL"
            )
        except mysql.connector.Error:
            pass

    _ensure_orders_extra_columns()

    # PAYMENT Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS payment (
            payment_id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT,
            payment_method ENUM('Card', 'Cash on Delivery', 'UPI', 'Bank Transfer') DEFAULT 'Card',
            amount DECIMAL(10,2) NOT NULL,
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status ENUM('Pending', 'Completed', 'Failed') DEFAULT 'Pending',
            FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
        );
        """
    )

    # ORDER ITEMS Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS order_items (
            item_id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT,
            product_id INT,
            quantity INT,
            price DECIMAL(10,2),
            FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES product(product_id) ON DELETE CASCADE
        );
        """
    )

    # Add analytics columns to users (login counts / total spent)
    def _ensure_user_analytics_columns():
        def _ensure(col, ddl):
            cursor.execute("SHOW COLUMNS FROM users LIKE %s", (col,))
            exists = cursor.fetchone() is not None
            if not exists:
                cursor.execute(ddl)

        _ensure("login_count", "ALTER TABLE users ADD COLUMN login_count INT DEFAULT 0")
        _ensure("total_spent", "ALTER TABLE users ADD COLUMN total_spent DECIMAL(12,2) DEFAULT 0")
        _ensure("last_login", "ALTER TABLE users ADD COLUMN last_login TIMESTAMP NULL DEFAULT NULL")

    _ensure_user_analytics_columns()

    # RATINGS Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ratings (
            rating_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            product_id INT NOT NULL,
            rating TINYINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uniq_user_product (user_id, product_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES product(product_id) ON DELETE CASCADE
        );
        """
    )

    # Ensure there is at least one admin account for staff login
    cursor.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
    admin_count = cursor.fetchone()[0]
    if admin_count == 0:
        cursor.execute(
            """
            INSERT INTO users (username, email, password, phone, address, role, member_number, membership_level)
            VALUES ('admin', 'admin@local', 'admin', '', '', 'admin', NULL, 'Gold')
            """
        )

    connection.commit()
    cursor.close()
    connection.close()
    print("Database and tables created/updated successfully!")


# ---------- Helper functions for analytics & loyalty ----------

def increment_login_counter(user_id):
    db = connect_db()
    cur = db.cursor()
    try:
        cur.execute(
            "UPDATE users SET login_count = COALESCE(login_count,0) + 1, last_login = NOW() WHERE user_id=%s",
            (user_id,),
        )
        db.commit()
    finally:
        db.close()


def add_user_spend(user_id, amount):
    """Legacy helper."""
    db = connect_db()
    cur = db.cursor()
    try:
        cur.execute(
            "UPDATE users SET total_spent = COALESCE(total_spent,0) + %s WHERE user_id=%s",
            (amount, user_id),
        )
        db.commit()
    finally:
        db.close()


def _calculate_membership_level(total_spent: float) -> str:
    """
    Basic loyalty tier:
      - Bronze: default, < 500
      - Silver: >= 500
      - Gold:   >= 1000
    """
    if total_spent >= 1000:
        return "Gold"
    elif total_spent >= 500:
        return "Silver"
    else:
        return "Bronze"


def record_order_effects(order_id):
    """Update member's loyalty (total_spent + membership_level) after an order."""
    db = connect_db()
    cur = db.cursor()
    try:
        # Use net_amount if present; otherwise fallback to total_amount
        cur.execute(
            "SELECT member_id, COALESCE(net_amount, total_amount) "
            "FROM orders WHERE order_id=%s",
            (order_id,),
        )
        row = cur.fetchone()
        if not row:
            return
        member_id, amount = row
        if not member_id:
            # walk-in customer with no membership
            return

        # Update total_spent
        cur.execute(
            "UPDATE users SET total_spent = COALESCE(total_spent,0) + %s WHERE user_id=%s",
            (amount, member_id),
        )

        # Re-fetch total_spent and update membership_level
        cur.execute(
            "SELECT COALESCE(total_spent,0) FROM users WHERE user_id=%s",
            (member_id,),
        )
        total_spent = float(cur.fetchone()[0] or 0)
        new_level = _calculate_membership_level(total_spent)

        cur.execute(
            "UPDATE users SET membership_level=%s WHERE user_id=%s",
            (new_level, member_id),
        )

        db.commit()
    finally:
        db.close()


def add_or_update_rating(user_id, product_id, rating, comment=None):
    if rating < 1 or rating > 5:
        raise ValueError("rating must be between 1 and 5")
    db = connect_db()
    cur = db.cursor()
    try:
        cur.execute(
            """
            INSERT INTO ratings (user_id, product_id, rating, comment)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE rating=VALUES(rating), comment=VALUES(comment), created_at=CURRENT_TIMESTAMP
            """,
            (user_id, product_id, rating, comment),
        )
        db.commit()
    finally:
        db.close()


def get_product_rating(product_id):
    """Returns (average_rating, ratings_count) for a product."""
    db = connect_db()
    cur = db.cursor()
    try:
        cur.execute(
            "SELECT COALESCE(AVG(rating),0), COUNT(*) FROM ratings WHERE product_id=%s",
            (product_id,),
        )
        avg_rating, count = cur.fetchone()
        return float(avg_rating or 0), int(count or 0)
    finally:
        db.close()


def get_user_stats(user_id):
    """Returns dict with total_spent, login_count, last_login, membership_level."""
    db = connect_db()
    cur = db.cursor()
    try:
        cur.execute(
            "SELECT COALESCE(total_spent,0), COALESCE(login_count,0), last_login, membership_level "
            "FROM users WHERE user_id=%s",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return {"total_spent": 0.0, "login_count": 0, "last_login": None, "membership_level": "Bronze"}
        total_spent, login_count, last_login, membership_level = row
        return {
            "total_spent": float(total_spent or 0),
            "login_count": int(login_count or 0),
            "last_login": last_login,
            "membership_level": membership_level or "Bronze"
        }
    finally:
        db.close()


def get_most_sold_products(limit=10):
    """Returns list of (product_id, name, total_sold) sorted desc by sold quantity."""
    db = connect_db()
    cur = db.cursor()
    try:
        cur.execute(
            """
            SELECT p.product_id, p.name, COALESCE(SUM(oi.quantity), 0) AS total_sold
            FROM product p
            LEFT JOIN order_items oi ON oi.product_id = p.product_id
            GROUP BY p.product_id, p.name
            ORDER BY total_sold DESC, p.product_id ASC
            LIMIT %s
            """,
            (limit,),
        )
        return cur.fetchall()
    finally:
        db.close()


def get_least_sold_products(limit=10):
    """Returns list of (product_id, name, total_sold) sorted asc by sold quantity (includes zeros)."""
    db = connect_db()
    cur = db.cursor()
    try:
        cur.execute(
            """
            SELECT p.product_id, p.name, COALESCE(SUM(oi.quantity), 0) AS total_sold
            FROM product p
            LEFT JOIN order_items oi ON oi.product_id = p.product_id
            GROUP BY p.product_id, p.name
            ORDER BY total_sold ASC, p.product_id ASC
            LIMIT %s
            """,
            (limit,),
        )
        return cur.fetchall()
    finally:
        db.close()


# Auto-bootstrap DB
create_database()
