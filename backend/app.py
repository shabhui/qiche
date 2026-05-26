from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import sys
app = Flask(__name__)
CORS(app)




def get_db():
    # 判断是否是 PyInstaller 打包后的 exe 运行
    if getattr(sys, 'frozen', False):
        # exe 所在目录
        base_dir = os.path.dirname(sys.executable)
    else:
        # 开发环境：app.py 所在目录的父目录（项目根目录）
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, 'data', 'pcauto.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# 搜索车型（含价格筛选）
@app.route('/api/cars/search')
def search_cars():
    brand = request.args.get('brand', '')
    model = request.args.get('model', '')
    category = request.args.get('category', '')
    price_min = request.args.get('price_min', type=float)
    price_max = request.args.get('price_max', type=float)
    page = request.args.get('page', 0, type=int)
    size = request.args.get('size', 10, type=int)

    conn = get_db()
    cursor = conn.cursor()

    # 动态提取最低价作为 min_price，并进行过滤
    query = """
            SELECT *,
                   CAST(
                           CASE
                               WHEN price LIKE '%-%' THEN SUBSTR(price, 1, INSTR(price, '-') - 1)
                               WHEN price LIKE '%起%' THEN REPLACE(SUBSTR(price, 1, INSTR(price, '万') - 1), ' ', '')
                               ELSE REPLACE(SUBSTR(price, 1, INSTR(price, '万') - 1), ' ', '')
                               END AS REAL
                   ) AS min_price
            FROM cars
            WHERE 1 = 1 \
            """
    params = []

    if brand:
        query += " AND brand LIKE ?"
        params.append(f'%{brand}%')
    if model:
        query += " AND model_name LIKE ?"
        params.append(f'%{model}%')

    # 价格筛选（使用 min_price 列）
    if price_min is not None:
        query += " AND min_price >= ?"
        params.append(price_min)
    if price_max is not None:
        query += " AND min_price <= ?"
        params.append(price_max)

    # 获取总数
    count_query = f"SELECT COUNT(*) FROM ({query})"
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    # 分页
    query += " LIMIT ? OFFSET ?"
    params.extend([size, page * size])
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    cars = [dict(row) for row in rows]
    return jsonify({'content': cars, 'totalElements': total})


# 车型对比
# 车型对比
@app.route('/api/cars/compare')
def compare_cars():
    ids = request.args.get('ids', '')
    if not ids:
        return jsonify([])
    ids_list = ids.split(',')
    placeholders = ','.join('?' * len(ids_list))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT c.car_id, c.model_name, c.brand, c.price,
               ROUND(AVG(co.rating), 1) AS avg_rating
        FROM cars c
        LEFT JOIN comments co ON c.car_id = co.car_id
        WHERE c.car_id IN ({placeholders})
        GROUP BY c.car_id
    """, ids_list)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


# 获取车型评论
@app.route('/api/cars/comments/<car_id>')
def get_comments(car_id):
    page = request.args.get('page', 0, type=int)
    size = request.args.get('size', 10, type=int)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM comments WHERE car_id=?", (car_id,))
    total = cursor.fetchone()[0]
    cursor.execute("SELECT AVG(rating) FROM comments WHERE car_id=? AND rating > 0", (car_id,))
    avg_row = cursor.fetchone()
    avg_rating = round(avg_row[0], 2) if avg_row and avg_row[0] else None

    cursor.execute("""
                   SELECT nickname, publish_time, purchase_price, rating, advantages, disadvantages, full_comment
                   FROM comments
                   WHERE car_id = ?
                   ORDER BY id DESC LIMIT ?
                   OFFSET ?
                   """, (car_id, size, page * size))
    rows = cursor.fetchall()
    conn.close()
    return jsonify({
        'comments': [dict(row) for row in rows],
        'total': total,
        'avg_rating': avg_rating  # 新增：返回总体平均评分
    })


# 品牌统计
@app.route('/api/stats/brands')
def brand_stats():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT brand, COUNT(*) as car_count FROM cars WHERE brand IS NOT NULL GROUP BY brand ORDER BY car_count DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{'brand': r['brand'], 'count': r['car_count']} for r in rows])


if __name__ == '__main__':
    app.run(debug=True, port=5000)