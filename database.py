import sqlite3
import logging
from datetime import datetime
from config import DB_PATH

logger = logging.getLogger(__name__)

class GPSDatabase:
    """GPS 데이터를 저장하기 위한 SQLite 데이터베이스 관리 클래스"""
    
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """데이터베이스 연결"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            logger.info(f"데이터베이스 연결 성공: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"데이터베이스 연결 실패: {e}")
            raise
    
    def create_tables(self):
        """GPS 데이터 저장을 위한 테이블 생성 (서버 데이터 구조에 맞춤)"""
        try:
            # GPS + 온도 데이터를 저장하는 테이블 생성 (사용자 서버 구조에 맞춤)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS gps_temperature_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id TEXT NOT NULL DEFAULT 'V001',
                    timestamp REAL NOT NULL,
                    datetime TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    altitude REAL,
                    speed REAL,
                    heading REAL,
                    temperature REAL,
                    status TEXT DEFAULT 'normal',
                    sent BOOLEAN DEFAULT FALSE,
                    sent_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 인덱스 생성 (검색 성능 향상)
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON gps_temperature_data(timestamp)
            """)

            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_datetime
                ON gps_temperature_data(datetime)
            """)
            
            self.conn.commit()
            logger.info("데이터베이스 테이블 생성 완료")
        except sqlite3.Error as e:
            logger.error(f"테이블 생성 실패: {e}")
            raise
    
    def insert_gps_temperature_data(self, latitude=None, longitude=None, altitude=None,
                                   speed=None, heading=None, temperature=None,
                                   vehicle_id='V001', status='normal'):
        """GPS + 온도 데이터 삽입 (사용자 서버 구조에 맞춤)"""
        timestamp = datetime.now().timestamp()
        datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

        try:
            self.cursor.execute("""
                INSERT INTO gps_temperature_data
                (vehicle_id, timestamp, datetime, latitude, longitude, altitude, speed, heading, temperature, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (vehicle_id, timestamp, datetime_str, latitude, longitude, altitude, speed, heading, temperature, status))

            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"GPS+온도 데이터 삽입 실패: {e}")
            return None
    
    def get_latest_gps_temperature_data(self, limit=10):
        """최근 GPS+온도 데이터 조회"""
        try:
            self.cursor.execute("""
                SELECT id, vehicle_id, timestamp, datetime, latitude, longitude, altitude, speed, heading, temperature, status, sent, sent_at, created_at
                FROM gps_temperature_data
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"GPS+온도 데이터 조회 실패: {e}")
            return []

    def get_unsent_gps_temperature_data(self, limit=10):
        """전송하지 않은 GPS+온도 데이터 조회 (중복 전송 방지)"""
        try:
            self.cursor.execute("""
                SELECT id, vehicle_id, timestamp, datetime, latitude, longitude, altitude, speed, heading, temperature, status, sent, sent_at, created_at
                FROM gps_temperature_data
                WHERE sent = FALSE OR sent IS NULL
                ORDER BY timestamp ASC
                LIMIT ?
            """, (limit,))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"미전송 GPS+온도 데이터 조회 실패: {e}")
            return []
    
    def get_gps_temperature_data_count(self):
        """저장된 총 GPS+온도 데이터 개수 조회"""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM gps_temperature_data")
            return self.cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"GPS+온도 데이터 카운트 조회 실패: {e}")
            return 0

    def mark_gps_temperature_data_as_sent(self, data_ids):
        """전송 완료된 GPS+온도 데이터 표시 (중복 전송 방지)"""
        try:
            if not data_ids:
                return

            # IN 절을 위한 플레이스홀더 생성
            placeholders = ','.join(['?'] * len(data_ids))

            self.cursor.execute(f"""
                UPDATE gps_temperature_data SET sent = TRUE, sent_at = ?
                WHERE id IN ({placeholders})
            """, [datetime.now()] + data_ids)

            self.conn.commit()
            logger.debug(f"{len(data_ids)}개 GPS+온도 데이터 전송 완료 표시")
        except sqlite3.Error as e:
            logger.error(f"GPS+온도 데이터 전송 완료 표시 실패: {e}")

    def get_sent_gps_temperature_count(self):
        """전송 완료된 GPS+온도 데이터 개수 조회"""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM gps_temperature_data WHERE sent = TRUE")
            return self.cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"전송 완료 GPS+온도 데이터 카운트 조회 실패: {e}")
            return 0

    def get_unsent_gps_temperature_count(self):
        """전송 대기 중인 GPS+온도 데이터 개수 조회"""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM gps_temperature_data WHERE sent = FALSE OR sent IS NULL")
            return self.cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"미전송 GPS+온도 데이터 카운트 조회 실패: {e}")
            return 0
    
    def close(self):
        """데이터베이스 연결 종료"""
        if self.conn:
            self.conn.close()
            logger.info("데이터베이스 연결 종료")
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

