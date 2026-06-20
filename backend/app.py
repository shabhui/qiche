from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import sys

app = Flask(__name__)
CORS(app)


def get_db():
    # 根据运行环境定位数据库文件
    if getattr(sys, 'frozen', False):
        # 打包为 exe 后，数据库位于程序所在目录
        base_dir = os.path.dirname(sys.executable)
    else:
        # 开发环境下，数据库位于项目根目录
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    db_path = os.path.join(base_dir, 'data', 'pcauto.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# 搜索车型，支持价格区间筛选
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

    # 从价格文本中提取最低价，用于区间筛选
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

    # 使用提取出的最低价进行筛选
    if price_min is not None:
        query += " AND min_price >= ?"
        params.append(price_min)
    if price_max is not None:
        query += " AND min_price <= ?"
        params.append(price_max)

    # 统计符合条件的车型总数
    count_query = f"SELECT COUNT(*) FROM ({query})"
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    # 分页返回当前结果
    query += " LIMIT ? OFFSET ?"
    params.extend([size, page * size])
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    cars = [dict(row) for row in rows]
    return jsonify({'content': cars, 'totalElements': total})


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


# 获取指定车型的评论列表
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
        'avg_rating': avg_rating  # 返回当前车型的平均评分
    })


# 统计各品牌车型数量
@app.route('/api/stats/brands')
def brand_stats():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT brand, COUNT(*) as car_count FROM cars WHERE brand IS NOT NULL GROUP BY brand ORDER BY car_count DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{'brand': r['brand'], 'count': r['car_count']} for r in rows])


if __name__ == '__main__':
    app.run(debug=True, port=5000)
