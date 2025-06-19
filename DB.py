import sqlite3
from sqlite3 import Error
import threading
from datetime import datetime


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
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    prediction REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            connection.commit()
            print("Tables created successfully.")
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
            cursor.execute(
                sql, {"given_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
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

    @staticmethod
    def get_predictions():
        sql = "SELECT * FROM predictions ORDER BY timestamp DESC"

        try:
            cursor = DB.get_connection().cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()  # Fetch all rows
            if rows:
                columns = [desc[0] for desc in cursor.description]
                result = [dict(zip(columns, row)) for row in rows]
                return result
            else:
                return None
        except Error as e:
            print(f"Fetch failed: {e}")
            return None

    @staticmethod
    def get_closest_predictions():
        query = """
        WITH HourlyClosest AS (
            SELECT
                prediction
            FROM predictions
            WHERE type = 'hourly'
            ORDER BY timestamp DESC  -- Get the most recent hourly prediction
            LIMIT 1
        ),
        DailyClosest AS (
            SELECT
                prediction
            FROM predictions
            WHERE type = 'daily'
            ORDER BY timestamp DESC  -- Get the most recent daily prediction
            LIMIT 1
        )
        SELECT 'hourly' AS type, prediction FROM HourlyClosest
        UNION ALL
        SELECT 'daily' AS type, prediction FROM DailyClosest;
        """

        cursor = DB.get_connection().cursor()

        # Execute the query
        cursor.execute(query)
        results = cursor.fetchall()

        # Build the dictionary
        predictions = {'hourly': None, 'daily': None}
        for row in results:
            predictions[row[0]] = round(row[1], 2)

        return predictions

    @staticmethod
    def get_readings_for_timestamps(timestamps):
        """
        Get temperature and humidity readings closest to the given timestamps
        
        Args:
            timestamps: List of timestamp strings in format 'YYYY-MM-DD HH:MM:SS'
            
        Returns:
            Dictionary with timestamp as key and {temperature, humidity} as value
        """
        if not timestamps:
            return {}
            
        # Create placeholders for the SQL query
        placeholders = ', '.join(['?'] * len(timestamps))
        
        sql = f"""
        WITH RankedReadings AS (
            SELECT
                r.timestamp as reading_timestamp,
                t.timestamp as target_timestamp,
                r.temperature,
                r.humidity,
                ROW_NUMBER() OVER (
                    PARTITION BY t.timestamp
                    ORDER BY ABS(julianday(r.timestamp) - julianday(t.timestamp))
                ) as rank
            FROM
                (SELECT ? as timestamp) t
            CROSS JOIN
                readings r
        )
        SELECT
            target_timestamp,
            temperature,
            humidity
        FROM
            RankedReadings
        WHERE
            rank = 1
        """
        
        result = {}
        connection = DB.get_connection()
        cursor = connection.cursor()
        
        # Execute query for each timestamp individually to get closest reading
        for timestamp in timestamps:
            try:
                cursor.execute(sql, (timestamp,))
                row = cursor.fetchone()
                if row:
                    result[timestamp] = {
                        'temperature': row[1],
                        'humidity': row[2]
                    }
                else:
                    result[timestamp] = {
                        'temperature': None,
                        'humidity': None
                    }
            except Error as e:
                print(f"Error fetching readings for timestamp {timestamp}: {e}")
                result[timestamp] = {
                    'temperature': None,
                    'humidity': None
                }
        
        return result
