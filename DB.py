import sqlite3
from sqlite3 import Error
import threading

class DB:
    _thread_local = threading.local()

    @staticmethod
    def get_connection():
        if not hasattr(DB._thread_local, "connection"):
            DB._thread_local.connection = sqlite3.connect('database.db')
        return DB._thread_local.connection
    
    @staticmethod
    def init():
        try:
            connection = DB.get_connection()
            print("Database connection successful")
            
            cursor = connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    temperature REAL NOT NULL,
                    humidity REAL NOT NULL,
                    device_id TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            connection.commit()
            print("Table 'readings' created successfully.")
        except Error as e:
            print(f"Database connection failed: {e}")

    @staticmethod
    def insert_data(table_name, data):
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data.values()])
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

        try:
            cursor = DB.get_connection().cursor()
            cursor.execute(sql, tuple(data.values()))
            DB.get_connection().commit()
            return cursor.lastrowid
        except Error as e:
            print(f"Insert failed: {e}")
            return None

    @staticmethod
    def get_data():
        sql = """
            WITH ClosestReadings AS (
                SELECT 
                    device_id,
                    temperature,
                    humidity,
                    timestamp,
                    ROW_NUMBER() OVER (
                        PARTITION BY device_id
                        ORDER BY
                            ABS(strftime('%H:%M:%S', timestamp) - strftime('%H:%M:%S', :given_timestamp)),
                            ABS(julianday(timestamp) - julianday(:given_timestamp))
                    ) AS rank
                FROM readings
            )
            SELECT 
                AVG(temperature) AS avg_temperature,
                AVG(humidity) AS avg_humidity
            FROM ClosestReadings
            WHERE rank = 1;
        """

        try:
            cursor = DB.get_connection().cursor()
            cursor.execute(sql, {"given_timestamp": "2024-12-19 12:00:00"})  # Replace with your desired timestamp
            result = cursor.fetchone()
            if result:
                return {
                    "temperature": result[0],
                    "humidity": result[1],
                }
            else:
                return {"temperature": None, "humidity": None}
        except Error as e:
            print(f"Fetch failed: {e}")
            return {"temperature": None, "humidity": None}


