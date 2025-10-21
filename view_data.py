#!/usr/bin/env python3
"""
저장된 GPS 데이터를 조회하는 유틸리티
"""

import argparse
import sqlite3
from datetime import datetime
from config import DB_PATH


def print_table_header():
    """테이블 헤더 출력"""
    print("\n" + "=" * 140)
    print(f"{'ID':<8} {'날짜/시간':<22} {'위도':>12} {'경도':>12} {'고도(m)':>10} {'속도(km/h)':>12} {'방향':>8} {'위성':>6} {'온도(°C)':>10}")
    print("=" * 140)


def print_record(record):
    """레코드 출력"""
    # 온도 컬럼이 추가되었을 수 있으므로 유연하게 처리
    if len(record) == 11:  # 온도 포함
        id_, timestamp, dt, lat, lon, alt, speed, heading, sats, fix, temp = record
    else:  # 온도 없음 (구버전 DB)
        id_, timestamp, dt, lat, lon, alt, speed, heading, sats, fix = record
        temp = None
    
    # None 값 처리
    alt_str = f"{alt:.1f}" if alt is not None else "N/A"
    speed_str = f"{speed:.1f}" if speed is not None else "N/A"
    heading_str = f"{heading:.0f}°" if heading is not None else "N/A"
    sats_str = str(sats) if sats is not None else "N/A"
    temp_str = f"{temp:.1f}" if temp is not None else "N/A"
    
    print(f"{id_:<8} {dt:<22} {lat:>12.6f} {lon:>12.6f} {alt_str:>10} {speed_str:>12} {heading_str:>8} {sats_str:>6} {temp_str:>10}")


def show_latest(db_path, limit):
    """최근 데이터 조회"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM gps_data 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (limit,))
    
    records = cursor.fetchall()
    
    if records:
        print_table_header()
        for record in records:
            print_record(record)
        print("=" * 140)
        print(f"\n총 {len(records)}개의 레코드를 표시했습니다.")
    else:
        print("저장된 데이터가 없습니다.")
    
    conn.close()


def show_count(db_path):
    """총 데이터 개수 조회"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM gps_data")
    count = cursor.fetchone()[0]
    
    print(f"\n총 {count:,}개의 GPS 데이터가 저장되어 있습니다.")
    
    if count > 0:
        # 첫 번째와 마지막 데이터 시간
        cursor.execute("SELECT MIN(datetime), MAX(datetime) FROM gps_data")
        first, last = cursor.fetchone()
        print(f"첫 번째 데이터: {first}")
        print(f"마지막 데이터: {last}")
    
    conn.close()


def show_stats(db_path):
    """통계 정보 조회"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "=" * 60)
    print("GPS 데이터 통계")
    print("=" * 60)
    
    # 총 개수
    cursor.execute("SELECT COUNT(*) FROM gps_data")
    count = cursor.fetchone()[0]
    print(f"총 레코드 수: {count:,}")
    
    if count == 0:
        print("데이터가 없습니다.")
        conn.close()
        return
    
    # 시간 범위
    cursor.execute("SELECT MIN(datetime), MAX(datetime) FROM gps_data")
    first, last = cursor.fetchone()
    print(f"\n시간 범위:")
    print(f"  시작: {first}")
    print(f"  종료: {last}")
    
    # 위치 범위
    cursor.execute("""
        SELECT 
            MIN(latitude), MAX(latitude),
            MIN(longitude), MAX(longitude)
        FROM gps_data
    """)
    min_lat, max_lat, min_lon, max_lon = cursor.fetchone()
    print(f"\n위치 범위:")
    print(f"  위도: {min_lat:.6f} ~ {max_lat:.6f}")
    print(f"  경도: {min_lon:.6f} ~ {max_lon:.6f}")
    
    # 속도 통계
    cursor.execute("""
        SELECT 
            MIN(speed), MAX(speed), AVG(speed)
        FROM gps_data
        WHERE speed IS NOT NULL
    """)
    min_speed, max_speed, avg_speed = cursor.fetchone()
    if min_speed is not None:
        print(f"\n속도 통계 (km/h):")
        print(f"  최소: {min_speed:.1f}")
        print(f"  최대: {max_speed:.1f}")
        print(f"  평균: {avg_speed:.1f}")
    
    # 고도 통계
    cursor.execute("""
        SELECT 
            MIN(altitude), MAX(altitude), AVG(altitude)
        FROM gps_data
        WHERE altitude IS NOT NULL
    """)
    min_alt, max_alt, avg_alt = cursor.fetchone()
    if min_alt is not None:
        print(f"\n고도 통계 (m):")
        print(f"  최소: {min_alt:.1f}")
        print(f"  최대: {max_alt:.1f}")
        print(f"  평균: {avg_alt:.1f}")
    
    # 위성 수 통계
    cursor.execute("""
        SELECT 
            MIN(satellites), MAX(satellites), AVG(satellites)
        FROM gps_data
        WHERE satellites IS NOT NULL
    """)
    min_sats, max_sats, avg_sats = cursor.fetchone()
    if min_sats is not None:
        print(f"\n위성 수 통계:")
        print(f"  최소: {min_sats}")
        print(f"  최대: {max_sats}")
        print(f"  평균: {avg_sats:.1f}")
    
    # 온도 통계
    cursor.execute("""
        SELECT 
            MIN(temperature), MAX(temperature), AVG(temperature)
        FROM gps_data
        WHERE temperature IS NOT NULL
    """)
    min_temp, max_temp, avg_temp = cursor.fetchone()
    if min_temp is not None:
        print(f"\n온도 통계 (°C):")
        print(f"  최소: {min_temp:.1f}")
        print(f"  최대: {max_temp:.1f}")
        print(f"  평균: {avg_temp:.1f}")
    
    # 데이터베이스 크기
    cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
    db_size = cursor.fetchone()[0]
    db_size_mb = db_size / (1024 * 1024)
    print(f"\n데이터베이스 크기: {db_size_mb:.2f} MB")
    
    print("=" * 60 + "\n")
    
    conn.close()


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='GPS 데이터 조회 유틸리티',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--latest',
        type=int,
        metavar='N',
        help='최근 N개의 데이터 표시 (기본값: 10)'
    )
    
    parser.add_argument(
        '--count',
        action='store_true',
        help='총 데이터 개수 표시'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='통계 정보 표시'
    )
    
    parser.add_argument(
        '--db',
        default=DB_PATH,
        help=f'데이터베이스 파일 경로 (기본값: {DB_PATH})'
    )
    
    args = parser.parse_args()
    
    # 옵션이 없으면 기본값으로 최근 10개 표시
    if not any([args.latest, args.count, args.stats]):
        args.latest = 10
    
    try:
        if args.count:
            show_count(args.db)
        
        if args.stats:
            show_stats(args.db)
        
        if args.latest:
            show_latest(args.db, args.latest)
    
    except sqlite3.Error as e:
        print(f"데이터베이스 오류: {e}")
    except FileNotFoundError:
        print(f"데이터베이스 파일을 찾을 수 없습니다: {args.db}")


if __name__ == "__main__":
    main()

