import sqlite3

def get_db_connection():
    conn = sqlite3.connect('data/pcauto.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_all_brands():
    """获取所有品牌列表（用于前端筛选）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT brand FROM cars WHERE brand IS NOT NULL AND brand != ''")
    brands = [row['brand'] for row in cursor.fetchall()]
    conn.close()
    return brands

def get_all_categories():
    """获取所有车辆级别/品类（用于前端筛选）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM cars WHERE category IS NOT NULL AND category != ''")
    categories = [row['category'] for row in cursor.fetchall()]
    conn.close()
    return categories