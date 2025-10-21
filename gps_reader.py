#!/usr/bin/env python3
"""
실제 GPS 모듈에서 데이터를 읽는 클래스
GPSD 또는 시리얼 포트를 통해 GPS 데이터 수신
"""

import logging
import serial
import time
from config import GPS_PORT, GPS_BAUDRATE

logger = logging.getLogger(__name__)


class GPSReader:
    """GPS 모듈에서 NMEA 데이터를 읽는 클래스"""

    def __init__(self):
        self.serial_conn = None
        self.last_successful_read = None
        self.connection_attempts = 0
        self.max_connection_attempts = 5
        self.connect()
    
    def connect(self):
        """GPS 모듈에 연결"""
        try:
            # 기존 연결이 있으면 종료
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.close()

            self.serial_conn = serial.Serial(
                GPS_PORT,
                baudrate=GPS_BAUDRATE,
                timeout=1,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )

            # 연결 직후 약간의 대기 시간
            time.sleep(0.1)

            self.connection_attempts = 0
            logger.info(f"✅ GPS 모듈 연결 성공: {GPS_PORT}")

        except serial.SerialException as e:
            self.connection_attempts += 1
            logger.error(f"❌ GPS 모듈 연결 실패 (시도 {self.connection_attempts}/{self.max_connection_attempts}): {e}")

            if self.connection_attempts >= self.max_connection_attempts:
                logger.error(f"❌ 최대 연결 시도 횟수 초과. GPS 모듈이 연결되지 않았거나 포트가 사용 중입니다.")
                raise
            else:
                logger.info("재연결을 시도합니다...")
                time.sleep(2)  # 잠시 대기 후 재시도
                self.connect()

    def is_connected(self):
        """연결 상태 확인"""
        return self.serial_conn is not None and self.serial_conn.is_open

    def reconnect(self):
        """연결 재시도"""
        logger.info("GPS 모듈 재연결을 시도합니다...")
        self.connect()
    
    def parse_nmea_gga(self, sentence):
        """GPGGA NMEA 문장 파싱"""
        try:
            parts = sentence.split(',')
            
            if len(parts) < 15 or parts[0] not in ['$GPGGA', '$GNGGA']:
                return None
            
            # 위도 파싱
            if parts[2] and parts[3]:
                lat_deg = float(parts[2][:2])
                lat_min = float(parts[2][2:])
                latitude = lat_deg + lat_min / 60.0
                if parts[3] == 'S':
                    latitude = -latitude
            else:
                return None
            
            # 경도 파싱
            if parts[4] and parts[5]:
                lon_deg = float(parts[4][:3])
                lon_min = float(parts[4][3:])
                longitude = lon_deg + lon_min / 60.0
                if parts[5] == 'W':
                    longitude = -longitude
            else:
                return None
            
            # 추가 정보
            fix_quality = int(parts[6]) if parts[6] else 0
            satellites = int(parts[7]) if parts[7] else 0
            altitude = float(parts[9]) if parts[9] else None
            
            return {
                'latitude': latitude,
                'longitude': longitude,
                'altitude': altitude,
                'satellites': satellites,
                'fix_quality': fix_quality
            }
        except (ValueError, IndexError) as e:
            logger.debug(f"NMEA 파싱 오류: {e}")
            return None
    
    def parse_nmea_rmc(self, sentence):
        """GPRMC NMEA 문장 파싱 (속도, 방향 정보)"""
        try:
            parts = sentence.split(',')
            
            if len(parts) < 12 or parts[0] not in ['$GPRMC', '$GNRMC']:
                return None
            
            # 속도 (노트를 km/h로 변환)
            speed = float(parts[7]) * 1.852 if parts[7] else None
            
            # 방향 (도)
            heading = float(parts[8]) if parts[8] else None
            
            return {
                'speed': speed,
                'heading': heading
            }
        except (ValueError, IndexError) as e:
            logger.debug(f"NMEA 파싱 오류: {e}")
            return None
    
    def read(self):
        """GPS 데이터 읽기"""
        if not self.is_connected():
            logger.warning("GPS 연결이 끊어져 재연결을 시도합니다")
            try:
                self.reconnect()
            except:
                logger.error("GPS 재연결 실패")
                return None

        gps_data = {}

        try:
            # 연결 상태 확인
            if not self.serial_conn.is_open:
                logger.warning("시리얼 포트가 닫혀있습니다. 재연결을 시도합니다")
                self.reconnect()
                return None

            # 여러 NMEA 문장을 읽어서 완전한 데이터 구성
            for attempt in range(15):  # 최대 15번 시도
                try:
                    if self.serial_conn.in_waiting > 0:
                        line = self.serial_conn.readline().decode('ascii', errors='ignore').strip()

                        if not line:
                            continue

                        if line.startswith('$GPGGA') or line.startswith('$GNGGA'):
                            gga_data = self.parse_nmea_gga(line)
                            if gga_data:
                                gps_data.update(gga_data)

                        elif line.startswith('$GPRMC') or line.startswith('$GNRMC'):
                            rmc_data = self.parse_nmea_rmc(line)
                            if rmc_data:
                                gps_data.update(rmc_data)

                        # 위도/경도가 있으면 반환
                        if 'latitude' in gps_data and 'longitude' in gps_data:
                            self.last_successful_read = time.time()
                            return gps_data
                    else:
                        # 데이터가 없으면 잠시 대기
                        time.sleep(0.05)
                        continue

                except UnicodeDecodeError as e:
                    logger.debug(f"데이터 디코딩 오류: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"데이터 읽기 중 오류: {e}")
                    break

            # 데이터가 불완전한 경우 로그 기록
            if gps_data:
                missing_fields = []
                if 'latitude' not in gps_data:
                    missing_fields.append('위도')
                if 'longitude' not in gps_data:
                    missing_fields.append('경도')

                if missing_fields:
                    logger.warning(f"불완전한 GPS 데이터 수신: {', '.join(missing_fields)} 누락")

            return gps_data if gps_data else None

        except serial.SerialException as e:
            logger.error(f"시리얼 통신 오류: {e}")
            # 연결이 끊어진 것 같으면 재연결 시도
            if "device reports readiness to read but returned no data" in str(e):
                logger.info("장치 연결이 끊어진 것 같습니다. 재연결을 시도합니다...")
                try:
                    self.reconnect()
                except:
                    logger.error("GPS 재연결 실패")
            return None
        except Exception as e:
            logger.error(f"GPS 읽기 중 예상치 못한 오류: {e}")
            return None
    
    def close(self):
        """연결 종료"""
        if self.serial_conn:
            try:
                self.serial_conn.close()
                logger.info("GPS 모듈 연결 종료")
            except Exception as e:
                logger.warning(f"연결 종료 중 오류 발생: {e}")

    def get_status(self):
        """GPS 상태 정보 반환"""
        return {
            'connected': self.is_connected(),
            'last_successful_read': self.last_successful_read,
            'connection_attempts': self.connection_attempts,
            'port': GPS_PORT,
            'baudrate': GPS_BAUDRATE
        }

