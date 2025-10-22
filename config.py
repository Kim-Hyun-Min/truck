# GPS 트럭 위치 추적 시스템 설정

# 데이터베이스 설정
DB_PATH = "truck_gps.db"

# GPS 설정
# NK-GPS-U는 보통 /dev/ttyACM0 또는 /dev/ttyUSB0로 인식됩니다
# 실제 포트는 'ls -l /dev/ttyACM* /dev/ttyUSB*' 명령으로 확인하세요
GPS_PORT = "/dev/ttyACM0"  # NK-GPS-U 기본 포트
GPS_BAUDRATE = 9600        # NK-GPS-U 기본 통신 속도 (9600 또는 38400)

# 데이터 수집 설정
# GPS가 초당 1개만 보내더라도 마지막 데이터를 반복 저장
SAMPLE_RATE = 10  # 초당 샘플 수
INTERVAL = 1.0 / SAMPLE_RATE  # 샘플 간격 (0.1초)

# 온도 센서 설정
TEMP_SENSOR_TYPE = "MCP9600"  # MCP9600, DS18B20, DHT22, ANALOG 등
# MCP9600: I2C 열전대 증폭기 (냉장고 온도 측정에 적합, 넓은 온도 범위)
# DS18B20: 1-Wire 디지털 온도 센서 (가장 흔함, 방수 가능)
# DHT22: 온습도 센서

# 서버 전송 설정 (MySQL)
SERVER_HOST = "192.168.0.3"  # 서버 호스트
SERVER_PORT = 3306  # 서버 포트
SERVER_DATABASE = "vaccine_logistics"  # 데이터베이스 이름
SERVER_USERNAME = "vaccine"  # 사용자명
SERVER_PASSWORD = "dlsvmfk0331"  # 비밀번호

# API 설정 (테스트용)
SERVER_API_URL = "https://your-server.com/api/gps-data"  # 실제 서버 URL로 변경
SERVER_API_KEY = "your-api-key"  # 실제 API 키로 변경


# MQTT 브로커 설정
MQTT_BROKER_HOST = "192.168.0.102"  # MQTT 브로커 IP (예: Windows PC)
MQTT_BROKER_PORT = 1883
MQTT_TOPIC = "truck/gps/data"
MQTT_CLIENT_ID = "truck_gps_client"
MQTT_QOS = 1
MQTT_RETAIN = False


# 차량 설정
VEHICLE_ID = "V001"  # 차량 고유 ID

# 전송 설정
SEND_INTERVAL = 0.1  # 서버 전송 간격 (초), 실시간 전송(초당 10회) 목표
BATCH_SIZE = 1  # 한 번에 전송할 데이터 개수 (가장 최신 1개)
RETRY_ATTEMPTS = 3  # 전송 실패 시 재시도 횟수
RETRY_DELAY = 1  # 재시도 간격 (초)

# 로깅 설정
LOG_LEVEL = "INFO"
LOG_FILE = "gps_tracker.log"

