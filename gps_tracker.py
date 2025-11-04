#!/usr/bin/env python3
"""
트럭 GPS 위치 추적 시스템
라즈베리파이에서 GPS 데이터를 실시간으로 수집하고 로컬 DB에 저장
"""

import time
import logging
import signal
import sys
import threading
from collections import deque
from datetime import datetime
from database import GPSDatabase
from server_sender import ServerSender
from config import DB_PATH, SAMPLE_RATE, INTERVAL, LOG_LEVEL, LOG_FILE, VEHICLE_ID, RETENTION_SECONDS, TEMP_RANGES

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GPSTracker:
    """GPS 데이터를 수집하고 데이터베이스에 저장하는 클래스"""

    def __init__(self):
        self.running = False
        self.db = None
        self.gps_reader = None
        self.temp_reader = None  # 온도 센서 추가
        self.server_sender = None  # 서버 전송기 추가

        # 데이터 버퍼 (초당 데이터 수 모니터링용)
        self.gps_buffer = deque(maxlen=100)  # 최근 100개 GPS 데이터
        self.temp_buffer = deque(maxlen=100)  # 최근 100개 온도 데이터
        self.buffer_lock = threading.Lock()

        # 데이터 읽기 스레드
        self.gps_reader_thread = None
        self.temp_reader_thread = None

        # 온도 상태 범위 설정 (config.py에서 가져옴)
        self.temp_ranges = TEMP_RANGES

    def get_temperature_status(self, temperature):
        """온도값에 따른 상태 판단"""
        if temperature is None:
            return 'unknown'

        for status, (min_temp, max_temp) in self.temp_ranges.items():
            if min_temp <= temperature < max_temp:
                return status
        return 'normal'

    def check_gps_connection(self):
        """GPS 연결 상태 확인 및 재연결"""
        if not self.gps_reader:
            return

        try:
            gps_status = self.gps_reader.get_status()

            if not gps_status['connected']:
                logger.warning("GPS 연결이 끊어져 있습니다. 재연결을 시도합니다...")
                try:
                    self.gps_reader.reconnect()
                    logger.info("GPS 재연결 성공")
                except Exception as e:
                    logger.error(f"GPS 재연결 실패: {e}")
                    # GPS 시뮬레이터로 전환 시도
                    self.switch_to_gps_simulator()

        except Exception as e:
            logger.error(f"GPS 연결 상태 확인 중 오류: {e}")

    def switch_to_gps_simulator(self):
        """GPS 연결 실패 시 시뮬레이터로 전환"""
        try:
            logger.info("GPS 시뮬레이터로 전환을 시도합니다...")
            from gps_simulator import GPSSimulator

            # 기존 GPS 리더 정리
            if self.gps_reader:
                self.gps_reader.close()

            # GPS 시뮬레이터로 교체
            self.gps_reader = GPSSimulator()
            logger.info("✅ GPS 시뮬레이터로 전환 완료")

        except Exception as e:
            logger.error(f"GPS 시뮬레이터 전환 실패: {e}")
        
    def setup(self):
        """초기 설정"""
        logger.info("GPS 추적 시스템 초기화 중...")
        
        # 데이터베이스 연결
        self.db = GPSDatabase()
        self.db.connect()
        self.db.create_tables()
        
        # GPS 리더 초기화 (실제 GPS 모듈 또는 시뮬레이터)
        try:
            from gps_reader import GPSReader
            self.gps_reader = GPSReader()
            logger.info("GPS 리더 초기화 완료 - 실제 GPS 모듈 사용")
        except (ImportError, Exception) as e:
            logger.warning(f"GPS 하드웨어 연결 실패 ({e}). 시뮬레이터 모드로 전환합니다.")
            from gps_simulator import GPSSimulator
            self.gps_reader = GPSSimulator()
            logger.info("GPS 시뮬레이터 초기화 완료 - 테스트 데이터 생성 중")
        
        # 온도 센서 초기화 (실제 센서 또는 시뮬레이터)
        try:
            from temperature_reader import TemperatureReader
            self.temp_reader = TemperatureReader()
            logger.info("온도 센서 초기화 완료 - 실제 센서 사용")
        except (ImportError, Exception) as e:
            logger.warning(f"온도 센서 연결 실패 ({e}). 시뮬레이터 모드로 전환합니다.")
            from temperature_simulator import TemperatureSimulator
            self.temp_reader = TemperatureSimulator()
            logger.info("온도 시뮬레이터 초기화 완료 - 냉장고 온도 시뮬레이션 중")

        # 서버 전송기 초기화
        self.server_sender = ServerSender(DB_PATH)
        logger.info("서버 전송기 초기화 완료")
    
    def gps_reader_loop(self):
        """GPS 데이터를 지속적으로 읽는 백그라운드 스레드"""
        while self.running:
            try:
                gps_data = self.gps_reader.read()
                if gps_data and gps_data.get('latitude') and gps_data.get('longitude'):
                    with self.buffer_lock:
                        self.gps_buffer.append({
                            'data': gps_data,
                            'timestamp': time.time()
                        })
            except Exception as e:
                logger.error(f"GPS 읽기 오류: {e}")
            time.sleep(0.01)  # 10ms마다 시도
    
    def temp_reader_loop(self):
        """온도 데이터를 지속적으로 읽는 백그라운드 스레드"""
        while self.running:
            try:
                temperature = self.temp_reader.read()
                if temperature is not None:
                    with self.buffer_lock:
                        self.temp_buffer.append({
                            'data': temperature,
                            'timestamp': time.time()
                        })
            except Exception as e:
                logger.error(f"온도 읽기 오류: {e}")
            time.sleep(0.01)  # 10ms마다 시도
    
    def get_data_rate_per_second(self, buffer):
        """버퍼에서 초당 데이터 수 계산"""
        with self.buffer_lock:
            if len(buffer) == 0:
                return 0
            
            now = time.time()
            # 최근 1초 내의 데이터만 카운트 (버퍼를 리스트로 복사하여 안전하게 반복)
            buffer_copy = list(buffer)
        
        # lock 밖에서 계산 (더 빠름)
        count = sum(1 for item in buffer_copy if now - item['timestamp'] <= 1.0)
        return count
    
    def get_latest_data(self, buffer):
        """버퍼에서 가장 최근 데이터 가져오기"""
        with self.buffer_lock:
            if len(buffer) > 0:
                return buffer[-1]['data']
        return None
    
    def start(self):
        """GPS 데이터 수집 시작 (초당 데이터 수 모니터링 및 적응형 저장)"""
        self.running = True
        logger.info(f"GPS + 온도 데이터 수집 시작 (목표: 초당 {SAMPLE_RATE}개)")
        logger.info("- 초당 10개 미만: 가장 최근 데이터 저장")
        logger.info("- 초당 11개 이상: 0.1초당 한번씩 가장 최근 데이터 저장")
        
        # 백그라운드 데이터 읽기 스레드 시작
        self.gps_reader_thread = threading.Thread(target=self.gps_reader_loop, daemon=True)
        self.temp_reader_thread = threading.Thread(target=self.temp_reader_loop, daemon=True)
        self.gps_reader_thread.start()
        self.temp_reader_thread.start()
        logger.info("센서 데이터 읽기 스레드 시작됨")

        # 서버 전송 스레드 시작
        if self.server_sender:
            self.server_sender.start()

        # 서버 전송 시작
        try:
            if self.server_sender:
                self.server_sender.start()
                logger.info("서버 데이터 전송 시작됨")
        except Exception as e:
            logger.error(f"서버 전송 시작 실패: {e}")
        
        sample_count = 0
        start_time = time.time()
        last_gps_data = None
        last_temp_data = None
        
        try:
            while self.running:
                # GPS 연결 상태 주기적 확인 (10초마다)
                if sample_count % 100 == 0:  # 10초마다 체크 (0.1초 * 100 = 10초)
                    self.check_gps_connection()
                # 30초마다(0.1초*300) 보관기간 초과 데이터 자동 삭제
                if sample_count % 300 == 0 and self.db:
                    try:
                        self.db.purge_older_than_seconds(RETENTION_SECONDS)
                    except Exception as _:
                        pass

                # 정확한 시간까지 대기 (0.1초 간격)
                target_time = start_time + (sample_count * INTERVAL)
                now = time.time()
                sleep_time = target_time - now

                if sleep_time > 0:
                    time.sleep(sleep_time)
                
                # 초당 데이터 수 확인
                gps_rate = self.get_data_rate_per_second(self.gps_buffer)
                temp_rate = self.get_data_rate_per_second(self.temp_buffer)
                
                # GPS 데이터 가져오기
                gps_data = self.get_latest_data(self.gps_buffer)
                if gps_data:
                    last_gps_data = gps_data
                elif last_gps_data:
                    gps_data = last_gps_data  # 캐시된 데이터 재사용
                
                # 온도 데이터 가져오기
                temperature = self.get_latest_data(self.temp_buffer)
                if temperature is not None:
                    last_temp_data = temperature
                elif last_temp_data is not None:
                    temperature = last_temp_data  # 캐시된 데이터 재사용
                
                # 데이터 저장 조건:
                # 1. GPS/온도 데이터가 초당 10개 미만: 가장 최근 데이터 저장
                # 2. GPS/온도 데이터가 초당 11개 이상: 0.1초당 한번씩 가장 최근 데이터 저장
                should_save = False
                
                if gps_rate < 10 or temp_rate < 10:
                    # 초당 10개 미만: 무조건 저장 (가장 최근 데이터)
                    should_save = True
                elif gps_rate >= 11 or temp_rate >= 11:
                    # 초당 11개 이상: 0.1초당 한번씩 저장
                    should_save = True
                else:
                    # 초당 정확히 10개: 목표 달성, 0.1초당 한번씩 저장
                    should_save = True
                
                # GPS 또는 온도 데이터 중 하나라도 있으면 저장 (독립적으로 동작)
                has_gps = gps_data and gps_data.get('latitude') and gps_data.get('longitude')
                has_temp = temperature is not None
                
                if should_save and (has_gps or has_temp):
                    # 온도 상태 판단
                    temp_status = self.get_temperature_status(temperature) if temperature is not None else 'unknown'

                    # GPS + 온도 데이터 저장 (GPS 또는 온도 중 하나만 있어도 저장)
                    record_id = self.db.insert_gps_temperature_data(
                        latitude=gps_data['latitude'] if has_gps else None,
                        longitude=gps_data['longitude'] if has_gps else None,
                        altitude=gps_data.get('altitude') if has_gps else None,
                        speed=gps_data.get('speed') if has_gps else None,
                        heading=gps_data.get('heading') if has_gps else None,
                        temperature=temperature,
                        vehicle_id=VEHICLE_ID,
                        status=temp_status
                    )
                    
                    sample_count += 1
                    
                    # 10개마다 로그 출력 (정확히 1초마다)
                    if sample_count % 10 == 0:
                        elapsed = time.time() - start_time
                        save_rate = sample_count / elapsed
                        temp_str = f"{temperature:.1f}°C" if temperature is not None else "N/A"
                        gps_str = f"위도: {gps_data['latitude']:.6f}, 경도: {gps_data['longitude']:.6f}, 속도: {gps_data.get('speed', 0):.1f}km/h, 위성: {gps_data.get('satellites', 0)}개" if has_gps else "GPS: 없음"
                        logger.info(
                            f"샘플 #{sample_count} | "
                            f"GPS율: {gps_rate}/초, 온도율: {temp_rate}/초 | "
                            f"{gps_str} | "
                            f"온도: {temp_str} | "
                            f"저장율: {save_rate:.2f}/초"
                        )
                else:
                    logger.debug(f"데이터 대기 중... GPS율: {gps_rate}/초, 온도율: {temp_rate}/초")
                
        except KeyboardInterrupt:
            logger.info("사용자에 의해 중단됨")
        except Exception as e:
            logger.error(f"오류 발생: {e}", exc_info=True)
        finally:
            self.stop()
    
    def stop(self):
        """GPS 데이터 수집 중지"""
        if not self.running:
            return  # 이미 종료됨
        
        self.running = False
        
        if self.db:
            try:
                total_count = self.db.get_data_count()
                logger.info(f"총 저장된 데이터: {total_count}개")
            except Exception:
                pass  # 이미 닫힌 경우 무시
            self.db.close()
            self.db = None
        
        if self.gps_reader:
            self.gps_reader.close()
            self.gps_reader = None
        
        if self.temp_reader:
            self.temp_reader.close()
            self.temp_reader = None

        if self.server_sender:
            self.server_sender.stop()
            self.server_sender = None

        logger.info("GPS + 온도 추적 시스템 종료")
    
    def signal_handler(self, signum, frame):
        """시스템 시그널 처리"""
        logger.info(f"시그널 {signum} 수신")
        self.stop()
        sys.exit(0)


def main():
    """메인 함수"""
    tracker = GPSTracker()
    
    # 시그널 핸들러 등록 (Ctrl+C 등)
    signal.signal(signal.SIGINT, tracker.signal_handler)
    signal.signal(signal.SIGTERM, tracker.signal_handler)
    
    # 시스템 설정 및 시작
    tracker.setup()
    tracker.start()


if __name__ == "__main__":
    main()

