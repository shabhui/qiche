import sqlite3
import os
from datetime import datetime

class PCautoPipeline:
    def __init__(self):
        self.conn = None
        self.cursor = None

    def open_spider(self, spider):
        os.makedirs('data', exist_ok=True)
        self.conn = sqlite3.connect('data/pcauto.db')
        self.cursor = self.conn.cursor()
        # 车型表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cars (
                car_id TEXT PRIMARY KEY,
                brand TEXT,
                model TEXT,
                category TEXT,
                price_range TEXT,
                year TEXT,
                engine TEXT,
                transmission TEXT,
                fuel_consumption TEXT,
                rating REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # 评论表（关联到车型ID）
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS car_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                car_id TEXT NOT NULL,
                nickname TEXT,
                publish_time TEXT,
                purchase_price TEXT,
                rating INTEGER,
                advantages TEXT,
                disadvantages TEXT,
                comment_text TEXT,
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (car_id) REFERENCES cars(car_id)
            )
        ''')
        self.conn.commit()

    def process_item(self, item, spider):
        if 'model' in item:   # 车型数据
            self.cursor.execute('''
                INSERT OR REPLACE INTO cars 
                (car_id, brand, model, category, price_range, year, 
                 engine, transmission, fuel_consumption, rating)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (item.get('car_id'), item.get('brand'), item.get('model'),
                  item.get('category'), item.get('price_range'), item.get('year'),
                  item.get('engine'), item.get('transmission'),
                  item.get('fuel_consumption'), item.get('rating')))
        elif 'nickname' in item:   # 评论数据
            self.cursor.execute('''
                INSERT INTO car_comments 
                (car_id, nickname, publish_time, purchase_price, rating, 
                 advantages, disadvantages, comment_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (item.get('car_id'), item.get('nickname'), item.get('publish_time'),
                  item.get('purchase_price'), item.get('rating'),
                  item.get('advantages'), item.get('disadvantages'),
                  item.get('comment_text')))
        self.conn.commit()
        return item

    def close_spider(self, spider):
        if self.conn:
            self.conn.close()