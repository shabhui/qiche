from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

def get_db():
    conn = sqlite3.connect('data/pcauto.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/cars/search')
def search_cars():
    brand = request.args.get('brand', '')
    model = request.args.get('model', '')
    category = request.args.get('category', '')
    price_min = request.args.get('price_min', type=int)
    price_max = request.args.get('price_max', type=int)
    page = request.args.get('page', 0, type=int)
    size = request.args.get('size', 10, type=int)

    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM cars WHERE 1=1"
    params = []
    if brand:
        query += " AND brand LIKE ?"
        params.append(f'%{brand}%')
    if model:
        query += " AND model LIKE ?"
        params.append(f'%{model}%')
    if category:
        query += " AND category = ?"
        params.append(category)
    if price_min:
        query += " AND CAST(SUBSTR(price_range, 1, INSTR(price_range, '-')-1) AS REAL) >= ?"
        params.append(price_min)
    if price_max:
        query += " AND CAST(SUBSTR(price_range, INSTR(price_range, '-')+1, LENGTH(price_range)-INSTR(price_range, '-')-4) AS REAL) <= ?"
        params.append(price_max)

    # 获取总数
    count_query = f"SELECT COUNT(*) FROM ({query})"
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    query += " LIMIT ? OFFSET ?"
    params.extend([size, page * size])
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    cars = [dict(row) for row in rows]
    return jsonify({'content': cars, 'totalElements': total})


@app.route('/api/cars/compare')
def compare_cars():
    """多车型对比接口"""
    ids = request.args.get('ids', '').split(',')
    if not ids or ids == ['']:
        return jsonify([])
    placeholders = ','.join('?' * len(ids))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM cars WHERE car_id IN ({placeholders})", ids)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.route('/api/cars/comments/<car_id>')
def get_car_comments(car_id):
    """获取某个车型的评论列表（支持分页）"""
    page = request.args.get('page', 0, type=int)
    size = request.args.get('size', 20, type=int)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM car_comments WHERE car_id = ?", (car_id,))
    total = cursor.fetchone()[0]
    cursor.execute("""
        SELECT nickname, publish_time, purchase_price, rating, 
               advantages, disadvantages, comment_text
        FROM car_comments WHERE car_id = ? 
        ORDER BY crawled_at DESC LIMIT ? OFFSET ?
    """, (car_id, size, page * size))
    rows = cursor.fetchall()
    conn.close()
    return jsonify({
        'comments': [dict(row) for row in rows],
        'total': total
    })


@app.route('/api/stats/brands')
def brand_stats():
    """品牌销量/热度统计"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT brand, COUNT(*) as car_count, AVG(rating) as avg_rating 
        FROM cars GROUP BY brand ORDER BY car_count DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


if __name__ == '__main__':
    app.run(debug=True, port=5000)