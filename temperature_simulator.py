#!/usr/bin/env python3
"""
냉장고 온도 시뮬레이터
실제 온도 센서 없이 테스트 가능
"""

import logging
import random
import math
import time

logger = logging.getLogger(__name__)


class TemperatureSimulator:
    """백신 운송용 냉장 온도를 시뮬레이션하는 클래스"""

    def __init__(self, target_temp=5.0):
        """
        온도 시뮬레이터 초기화

        Args:
            target_temp: 목표 온도 (백신 운송 적정 온도, 기본 5°C)
        """
        # 백신 운송 적정 온도 범위: 2°C ~ 8°C
        self.target_temp = max(2.0, min(8.0, target_temp))  # 범위 제한
        self.current_temp = self.target_temp + random.uniform(-0.5, 0.5)  # 초기 온도 (목표 주변)
        self.update_count = 0

        # 온도 상태 범위 설정
        self.temp_ranges = {
            'critical_cold': (-float('inf'), 2.0),
            'cold': (2.0, 2.5),
            'normal': (2.5, 7.5),
            'warm': (7.5, 8.0),
            'critical_hot': (8.0, float('inf'))
        }

        logger.info(f"백신 온도 시뮬레이터 초기화 완료 (목표: {target_temp}°C, 범위: 2°C~8°C)")
    
    def get_temperature_status(self, temperature):
        """온도값에 따른 상태 판단"""
        for status, (min_temp, max_temp) in self.temp_ranges.items():
            if min_temp <= temperature < max_temp:
                return status
        return 'normal'  # 기본값

    def read(self):
        """
        시뮬레이션된 백신 운송 온도 데이터 생성

        백신 운송 온도 특성:
        - 목표 온도 주변에서 안정적인 유지 (2°C ~ 8°C 범위)
        - 약간의 자연 변동
        - 운송 중 진동이나 외부 요인에 의한 미세한 변화
        """
        self.update_count += 1

        # ━━━━━ 백신 운송 온도 시뮬레이션 ━━━━━
        # 기본 온도 변동 (목표 온도 주변 0.5°C 이내)
        base_variation = math.sin(self.update_count * 0.05) * 0.3  # ±0.3도 진동

        # 목표 온도로 천천히 수렴 (냉장 시스템 특성)
        temp_diff = self.target_temp - self.current_temp
        self.current_temp += temp_diff * 0.02  # 천천히 변화

        # 운송 중 미세한 온도 변화 시뮬레이션
        transport_noise = random.uniform(-0.2, 0.2)  # 운송 노이즈

        # 실제 온도 = 현재 온도 + 기본 변동 + 운송 노이즈
        temperature = self.current_temp + base_variation + transport_noise

        # 온도 범위 제한 (2°C ~ 8°C)
        temperature = max(2.0, min(8.0, temperature))

        # ━━━━━ 온도 이벤트 시뮬레이션 ━━━━━
        # 냉장 시스템 고장 이벤트 (매우 낮은 확률, 1000번에 1번꼴)
        if random.random() < 0.001:  # 0.1% 확률로 감소
            temperature += random.uniform(1.0, 3.0)  # 온도 상승 이벤트
            # logger.debug(f"냉장 시스템 이상 감지 (온도 상승: {temperature:.1f}°C)")  # 디버그 레벨로 변경

        # 소수점 2자리로 반올림
        temperature = round(temperature, 2)

        return temperature

    def read_with_status(self):
        """온도와 상태 정보를 함께 반환"""
        temperature = self.read()
        status = self.get_temperature_status(temperature)

        return {
            'temperature': temperature,
            'status': status
        }

    def close(self):
        """시뮬레이터 종료"""
        logger.info("온도 시뮬레이터 종료")


