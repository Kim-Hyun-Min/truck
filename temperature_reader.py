#!/usr/bin/env python3
"""
냉장고 온도 센서 읽기
DS18B20, DHT22, MCP9600 등 다양한 온도 센서 지원
"""

import logging
import gpiozero
import time
import sys
from config import TEMP_RANGES

logger = logging.getLogger(__name__)


class TemperatureReader:
    """실제 온도 센서에서 데이터를 읽는 클래스"""

    def __init__(self, sensor_type='MCP9600'):
        """
        온도 센서 초기화

        Args:
            sensor_type: 'MCP9600', 'DS18B20', 'DHT22', 'ANALOG' 등
        """
        self.sensor_type = sensor_type
        self.sensor = None

        # 백신 운송 온도 상태 범위 설정 (config.py에서 가져옴)
        self.temp_ranges = TEMP_RANGES

        self.connect()

    def get_temperature_status(self, temperature):
        """온도값에 따른 상태 판단"""
        if temperature is None:
            return 'unknown'

        for status, (min_temp, max_temp) in self.temp_ranges.items():
            if min_temp <= temperature < max_temp:
                return status
        return 'normal'  # 기본값

    def connect(self):
        """센서 연결"""
        try:
            if self.sensor_type == 'MCP9600':
                # MCP9600 I2C 온도 센서 (열전대 증폭기)
                import adafruit_mcp9600
                import board
                import busio

                try:
                    # I2C 버스 초기화 (다양한 주파수 시도)
                    for freq in [100000, 10000, 400000]:
                        try:
                            i2c = busio.I2C(board.SCL, board.SDA, frequency=freq)
                            break
                        except Exception as e:
                            if freq == 400000:
                                raise e
                            continue

                    # MCP9600 센서 초기화 (다양한 주소 시도)
                    sensor_addresses = [0x67, 0x60, 0x66, 0x61, 0x65, 0x62, 0x64, 0x63]
                    for address in sensor_addresses:
                        try:
                            self.sensor = adafruit_mcp9600.MCP9600(i2c, address=address)
                            logger.info(f"MCP9600 온도 센서 연결 성공 (I2C 주소: 0x{address:02X})")
                            break
                        except Exception as e:
                            if address == sensor_addresses[-1]:
                                raise Exception(f"모든 주소 시도 실패: {e}")
                            continue

                    # 열전대 타입 설정 (K-type이 가장 일반적)
                    # self.sensor.thermocouple_type = adafruit_mcp9600.THERMOCOUPLE_TYPE_K

                except Exception as e:
                    logger.warning(f"MCP9600 센서 연결 실패: {e}")
                    raise
            
            elif self.sensor_type == 'DS18B20':
                # DS18B20 1-Wire 온도 센서
                # /sys/bus/w1/devices/28-xxxx/w1_slave 파일 읽기
                import glob

                # 1-Wire 인터페이스 활성화 확인 및 장치 검색
                device_folders = glob.glob('/sys/bus/w1/devices/28*')
                if device_folders:
                    self.sensor_file = device_folders[0] + '/w1_slave'
                    logger.info(f"DS18B20 온도 센서 연결 성공: {device_folders[0]}")
                else:
                    # 1-Wire 인터페이스가 로드되지 않았을 수 있으므로 재시도
                    logger.warning("1-Wire 장치가 감지되지 않습니다. 인터페이스를 확인합니다...")
                    raise FileNotFoundError("DS18B20 센서를 찾을 수 없습니다. 1-Wire 인터페이스가 활성화되어 있는지 확인해주세요.")
            
            elif self.sensor_type == 'DHT22':
                # DHT22 센서 (Adafruit 라이브러리 사용)
                import adafruit_dht
                import board
                self.sensor = adafruit_dht.DHT22(board.D4)  # GPIO4
                logger.info("DHT22 온도 센서 연결 성공")

            elif self.sensor_type == 'GY21':
                # GY-21 I2C 온도/습도 센서 (SHT20 기반)
                import board
                import busio

                # I2C 버스 초기화 (Adafruit-Blinka 사용, 10kHz로 설정)
                self.i2c_bus = busio.I2C(board.SCL, board.SDA, frequency=10000)

                # GY-21의 가능한 I2C 주소들 (여러 개 시도)
                self.possible_addresses = [0x40, 0x41]  # 기본 주소와 대체 주소
                self.gy21_address = self.possible_addresses[0]  # 우선 첫 번째 주소 사용

                logger.info(f"GY-21 온도 센서 초기화 (시도 주소: {self.possible_addresses})")

            else:
                raise ValueError(f"지원하지 않는 센서 타입: {self.sensor_type}")
                
        except Exception as e:
            logger.error(f"온도 센서 연결 실패: {e}")
            raise
    
    def read_mcp9600(self):
        """MCP9600 센서 읽기"""
        try:
            # MCP9600은 열전대 온도와 주변 온도 모두 읽을 수 있음
            # temperature: 열전대로 측정한 온도 (냉장고 내부 온도)
            # ambient_temperature: 센서 자체의 주변 온도
            temperature = self.sensor.temperature
            return temperature
        except Exception as e:
            logger.error(f"MCP9600 읽기 오류: {e}")
            return None
    
    def read_ds18b20(self):
        """DS18B20 센서 읽기"""
        try:
            with open(self.sensor_file, 'r') as f:
                lines = f.readlines()
            
            # 체크섬 확인
            if lines[0].strip()[-3:] != 'YES':
                return None
            
            # 온도 파싱
            temp_pos = lines[1].find('t=')
            if temp_pos != -1:
                temp_string = lines[1][temp_pos+2:]
                temp_c = float(temp_string) / 1000.0
                return temp_c
        except Exception as e:
            logger.error(f"DS18B20 읽기 오류: {e}")
            return None
    
    def read_dht22(self):
        """DHT22 센서 읽기"""
        try:
            temperature = self.sensor.temperature
            # humidity = self.sensor.humidity  # 필요시 사용
            return temperature
        except RuntimeError as e:
            # DHT22는 간혹 읽기 실패
            logger.debug(f"DHT22 읽기 재시도 필요: {e}")
            return None
        except Exception as e:
            logger.error(f"DHT22 읽기 오류: {e}")
            return None

    def find_i2c_device(self):
        """연결된 I2C 장치 찾기"""
        logger.info("연결된 I2C 장치 검색 중...")

        found_devices = []
        for address in range(0x03, 0x78):  # 일반적인 I2C 주소 범위
            try:
                # 장치가 응답하는지 테스트
                self.i2c_bus.writeto(address, b'')
                found_devices.append(address)
                logger.info(f"주소 0x{address:02X}에 장치 발견")
            except:
                pass  # 응답 없음, 계속 진행

        if found_devices:
            logger.info(f"발견된 I2C 장치들: {[f'0x{addr:02X}' for addr in found_devices]}")
            return found_devices
        else:
            logger.warning("연결된 I2C 장치를 찾을 수 없습니다")
            return []

    def read_gy21(self):
        """GY-21 센서 읽기 (SHT20 기반)"""
        try:
            # 먼저 연결된 장치들 확인
            devices = self.find_i2c_device()
            if not devices:
                logger.error("읽을 수 있는 I2C 장치가 없습니다")
                return None

            # 발견된 장치들 중에서 시도
            for device_addr in devices:
                try:
                    logger.info(f"장치 0x{device_addr:02X}에서 온도 읽기 시도...")

                    # 온도 측정 명령 전송 (0xF3)
                    self.i2c_bus.writeto(device_addr, bytes([0xF3]))
                    time.sleep(0.1)  # 측정 완료 대기 (최소 85ms 필요)

                    # 2바이트 데이터 읽기
                    buffer = bytearray(2)
                    self.i2c_bus.readfrom_into(device_addr, buffer)

                    logger.info(f"수신된 데이터: {list(buffer)}")

                    # Raw 데이터 결합
                    raw_temp = (buffer[0] << 8) + buffer[1]

                    # 온도 계산 (SHT20 공식)
                    temperature = -46.85 + 175.72 * (raw_temp / 65536.0)

                    logger.info(f"계산된 온도: {temperature:.2f}°C")
                    return temperature

                except Exception as e:
                    logger.warning(f"장치 0x{device_addr:02X} 읽기 실패: {e}")
                    continue

            logger.error("모든 장치에서 읽기 실패")
            return None

        except Exception as e:
            logger.error(f"GY-21 읽기 오류: {e}")
            return None
    
    def read(self):
        """온도 읽기"""
        temperature = None

        if self.sensor_type == 'MCP9600':
            temperature = self.read_mcp9600()
        elif self.sensor_type == 'DS18B20':
            temperature = self.read_ds18b20()
        elif self.sensor_type == 'DHT22':
            temperature = self.read_dht22()
        elif self.sensor_type == 'GY21':
            temperature = self.read_gy21()

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
        """센서 연결 종료"""
        if self.sensor_type == 'DHT22' and self.sensor:
            self.sensor.exit()
        # GY21의 경우 busio.I2C는 특별한 종료 처리 불필요
        # (Adafruit-Blinka의 I2C 객체는 자동 관리됨)
        logger.info("온도 센서 연결 종료")

    def gpio_debug_info(self):
        """GPIO 디버깅 정보 출력"""
        logger.info("=== GPIO 디버깅 정보 ===")

        try:
            # I2C 관련 핀들 확인 (SCL=3, SDA=2)
            scl_pin = gpiozero.Button(3)  # GPIO 3 (SCL)
            sda_pin = gpiozero.Button(2)  # GPIO 2 (SDA)

            logger.info(f"SCL 핀 (GPIO 3) 상태: {'HIGH' if scl_pin.value else 'LOW'}")
            logger.info(f"SDA 핀 (GPIO 2) 상태: {'HIGH' if sda_pin.value else 'LOW'}")

            # DHT22 센서 핀 확인 (GPIO 4)
            if self.sensor_type == 'DHT22':
                dht_pin = gpiozero.Button(4)  # GPIO 4
                logger.info(f"DHT22 핀 (GPIO 4) 상태: {'HIGH' if dht_pin.value else 'LOW'}")

            # 1-Wire 핀 확인 (GPIO 4 - DS18B20용)
            if self.sensor_type == 'DS18B20':
                ow_pin = gpiozero.Button(4)  # GPIO 4
                logger.info(f"1-Wire 핀 (GPIO 4) 상태: {'HIGH' if ow_pin.value else 'LOW'}")

            scl_pin.close()
            sda_pin.close()
            if self.sensor_type in ['DHT22', 'DS18B20']:
                dht_pin.close()

        except Exception as e:
            logger.error(f"GPIO 디버깅 오류: {e}")

    def gpio_test_signal(self, pin_number, duration=1.0):
        """GPIO 핀에 테스트 신호 전송"""
        logger.info(f"=== GPIO {pin_number}번 핀 테스트 신호 전송 ===")

        try:
            # LED나 간단한 출력 장치로 테스트
            test_pin = gpiozero.DigitalOutputDevice(pin_number)

            logger.info(f"{pin_number}번 핀에 HIGH 신호 전송 ({duration}초)")
            test_pin.on()
            time.sleep(duration)

            logger.info(f"{pin_number}번 핀에 LOW 신호 전송")
            test_pin.off()

            test_pin.close()
            logger.info(f"GPIO {pin_number}번 핀 테스트 완료")

        except Exception as e:
            logger.error(f"GPIO 테스트 신호 전송 오류: {e}")

    def check_i2c_communication(self):
        """I2C 통신 상태 확인"""
        logger.info("=== I2C 통신 상태 확인 ===")

        try:
            # I2C 장치 목록 확인
            import subprocess
            result = subprocess.run(['i2cdetect', '-y', '1'], capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("I2C 장치 목록:")
                logger.info(result.stdout)
            else:
                logger.error(f"I2C 감지 오류: {result.stderr}")

        except FileNotFoundError:
            logger.error("i2cdetect 명령어를 찾을 수 없습니다")
        except Exception as e:
            logger.error(f"I2C 확인 중 오류 발생: {e}")

    def sensor_connection_test(self):
        """센서 연결 상태 테스트"""
        logger.info(f"=== {self.sensor_type} 센서 연결 테스트 ===")

        if self.sensor_type == 'GY21':
            try:
                # 먼저 모든 연결된 I2C 장치 검색
                logger.info("연결된 모든 I2C 장치 검색...")
                devices = self.find_i2c_device()

                if devices:
                    logger.info(f"발견된 장치들: {[f'0x{addr:02X}' for addr in devices]}")

                    # 각 장치에서 온도 읽기 시도
                    for device_addr in devices:
                        try:
                            logger.info(f"장치 0x{device_addr:02X}에서 온도 읽기 시도...")

                            # 온도 측정 명령 전송 (0xF3)
                            self.i2c_bus.writeto(device_addr, bytes([0xF3]))
                            time.sleep(0.1)

                            buffer = bytearray(2)
                            self.i2c_bus.readfrom_into(device_addr, buffer)

                            logger.info(f"장치 0x{device_addr:02X} 응답 데이터: {list(buffer)}")

                            # 온도 계산 시도
                            raw_temp = (buffer[0] << 8) + buffer[1]
                            temperature = -46.85 + 175.72 * (raw_temp / 65536.0)

                            logger.info(f"장치 0x{device_addr:02X} 온도: {temperature:.2f}°C")
                            logger.info("GY-21 센서 연결 정상")

                        except Exception as e:
                            logger.warning(f"장치 0x{device_addr:02X} 읽기 실패: {e}")
                else:
                    logger.error("연결된 I2C 장치를 찾을 수 없습니다")

            except Exception as e:
                logger.error(f"GY-21 센서 연결 테스트 오류: {e}")

        elif self.sensor_type == 'MCP9600':
            try:
                # MCP9600 센서가 응답하는지 확인
                temp = self.sensor.temperature
                logger.info(f"MCP9600 센서 응답 온도: {temp}°C")
                logger.info("MCP9600 센서 연결 정상")

            except Exception as e:
                logger.error(f"MCP9600 센서 연결 오류: {e}")

        elif self.sensor_type == 'DHT22':
            try:
                # DHT22 센서가 응답하는지 확인
                temp = self.sensor.temperature
                logger.info(f"DHT22 센서 응답 온도: {temp}°C")
                logger.info("DHT22 센서 연결 정상")

            except Exception as e:
                logger.error(f"DHT22 센서 연결 오류: {e}")

        elif self.sensor_type == 'DS18B20':
            try:
                # DS18B20 센서 파일 존재 확인
                import glob
                device_folder = glob.glob('/sys/bus/w1/devices/28*')

                if device_folder:
                    logger.info(f"DS18B20 센서 발견: {device_folder[0]}")
                    logger.info("DS18B20 센서 연결 정상")
                else:
                    logger.error("DS18B20 센서를 찾을 수 없습니다")

            except Exception as e:
                logger.error(f"DS18B20 센서 연결 오류: {e}")


def test_temperature_sensor(sensor_type='GY21'):
    """온도 센서 단독 테스트"""
    print(f"=== {sensor_type} 온도 센서 단독 테스트 ===")

    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    try:
        reader = TemperatureReader(sensor_type=sensor_type)
        print(f"{sensor_type} 센서 초기화 완료")

        # GPIO 상태 확인
        print("\n=== GPIO 상태 확인 ===")
        reader.gpio_debug_info()

        # I2C 통신 상태 확인
        print("\n=== I2C 통신 상태 확인 ===")
        reader.check_i2c_communication()

        # 센서 연결 테스트
        print("\n=== 센서 연결 테스트 ===")
        reader.sensor_connection_test()

        # 실제 온도 읽기 시도
        print("\n=== 온도 읽기 테스트 ===")
        for i in range(3):  # 3번 시도
            print(f"시도 {i+1}/3...")
            temperature = reader.read()
            if temperature is not None:
                print(f"✅ 성공! 온도: {temperature:.2f}°C")
                break
            else:
                print("❌ 읽기 실패")
            time.sleep(1)

        reader.close()
        return True

    except Exception as e:
        print(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    """단독 실행 시 테스트 모드"""
    sensor_type = 'GY21'  # 기본값

    # 명령줄 인자로 센서 타입 지정 가능
    if len(sys.argv) > 1:
        sensor_type = sys.argv[1]

    print(f"온도 센서 타입: {sensor_type}")
    success = test_temperature_sensor(sensor_type)

    if success:
        print("\n🎉 테스트 완료!")
    else:
        print("\n💥 테스트 실패!")


