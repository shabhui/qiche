import sqlite3
import os

class PCautoPipeline:
    def __init__(self):
        self.conn = None
        self.cursor = None

    def open_spider(self, spider):
        if spider.name != 'pcauto':
            return
        os.makedirs('data', exist_ok=True)
        self.conn = sqlite3.connect('data/pcauto.db')
        self.cursor = self.conn.cursor()
        # 创建车型表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cars (
                car_id TEXT PRIMARY KEY,
                model_name TEXT,
                brand TEXT,
                price TEXT
            )
        ''')
        # 创建评论表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                car_id TEXT,
                nickname TEXT,
                publish_time TEXT,
                purchase_price TEXT,
                rating REAL,
                advantages TEXT,
                disadvantages TEXT,
                full_comment TEXT
            )
        ''')
        self.conn.commit()

    def process_item(self, item, spider):
        if spider.name != 'pcauto':
            return item
        if 'model_name' in item:   # 车型数据
            self.cursor.execute('''
                INSERT OR REPLACE INTO cars (car_id, model_name, brand, price)
                VALUES (?, ?, ?, ?)
            ''', (item.get('car_id'), item.get('model_name'), item.get('brand'), item.get('price')))
        elif 'nickname' in item:    # 评论数据
            self.cursor.execute('''
                INSERT INTO comments 
                (car_id, nickname, publish_time, purchase_price, rating, advantages, disadvantages, full_comment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (item.get('car_id'), item.get('nickname'), item.get('publish_time'),
                  item.get('purchase_price'), item.get('rating'), item.get('advantages'),
                  item.get('disadvantages'), item.get('full_comment')))
        self.conn.commit()
        return item

    def close_spider(self, spider):
        if self.conn:
            self.conn.close()