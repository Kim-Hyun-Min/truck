#!/usr/bin/env python3
"""
GPS 시뮬레이터 - 테스트용
실제 GPS 하드웨어 없이 시스템을 테스트할 수 있도록 가상 GPS 데이터 생성
"""

import logging
import random
import math
import time

logger = logging.getLogger(__name__)


class GPSSimulator:
    """가상 GPS 데이터를 생성하는 시뮬레이터"""
    
    def __init__(self):
        # 시작 위치 (서울 시청 근처)
        self.base_lat = 37.5665
        self.base_lon = 126.9780
        
        # 현재 위치
        self.current_lat = self.base_lat
        self.current_lon = self.base_lon
        self.current_altitude = 50.0
        self.current_speed = 0.0
        self.current_heading = 0.0
        
        # 이동 파라미터
        self.speed_kmh = 60.0  # 평균 속도 (km/h)
        self.update_count = 0
        
        logger.info("GPS 시뮬레이터 초기화 완료")
    
    def read(self):
        """시뮬레이션된 GPS 데이터 생성"""
        self.update_count += 1
        
        # 간단한 원형 경로 시뮬레이션
        angle = (self.update_count * 0.01) % (2 * math.pi)
        radius = 0.01  # 약 1km
        
        self.current_lat = self.base_lat + radius * math.cos(angle)
        self.current_lon = self.base_lon + radius * math.sin(angle)
        
        # 속도에 약간의 변화 추가
        self.current_speed = self.speed_kmh + random.uniform(-5, 5)
        
        # 방향 계산
        self.current_heading = (math.degrees(angle) + 90) % 360
        
        # 고도에 약간의 변화
        self.current_altitude = 50.0 + random.uniform(-5, 5)
        
        return {
            'latitude': self.current_lat + random.uniform(-0.00001, 0.00001),
            'longitude': self.current_lon + random.uniform(-0.00001, 0.00001),
            'altitude': self.current_altitude,
            'speed': max(0, self.current_speed),
            'heading': self.current_heading,
            'satellites': random.randint(8, 12),
            'fix_quality': 1
        }
    
    def close(self):
        """시뮬레이터 종료"""
        logger.info("GPS 시뮬레이터 종료")

