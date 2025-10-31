#!/usr/bin/env python3
import sqlite3
from datetime import datetime
from flask import Flask, render_template, jsonify
from config import DB_PATH
import urllib.request
import urllib.parse
import json as jsonlib
import socket


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/latest')
def api_latest():
    """가장 최신 GPS+온도 1건 반환"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, vehicle_id, timestamp, datetime, latitude, longitude, altitude, speed, heading, temperature, status
        FROM gps_temperature_data
        ORDER BY timestamp DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        return jsonify({}), 200

    return jsonify({k: row[k] for k in row.keys()})


@app.route('/api/temperature-series')
def api_temperature_series():
    """최근 20분의 온도 시리즈 반환 (RETENTION_SECONDS 기준)"""
    # RETENTION_SECONDS는 config.py에서 정의됨 (기본 1200초 = 20분)
    retention_seconds = 1200  # 20분
    since_ts = datetime.now().timestamp() - retention_seconds

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT timestamp, datetime, temperature
        FROM gps_temperature_data
        WHERE temperature IS NOT NULL AND timestamp >= ?
        ORDER BY timestamp ASC
        """,
        (since_ts,)
    )
    rows = cur.fetchall()
    conn.close()

    series = [
        {
            't': r['datetime'],
            'x': r['timestamp'],
            'y': r['temperature'],
        }
        for r in rows
    ]
    return jsonify(series)


@app.route('/api/reverse-geocode')
def api_reverse_geocode():
    """간단한 리버스 지오코딩 (BigDataCloud API 사용)"""
    try:
        from flask import request
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        if lat is None or lon is None:
            return jsonify({}), 400

        # BigDataCloud Reverse Geocoding API 사용 (한국어 지원)
        url = f"http://api.bigdatacloud.net/data/reverse-geocode-client?latitude={lat}&longitude={lon}&localityLanguage=ko"
        req = urllib.request.Request(url, headers={'User-Agent': 'TruckGPS/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = jsonlib.loads(resp.read().decode('utf-8'))
        
        # 한국 주소 우선 조합 (시/도 + 시/군/구)
        city = data.get('city', '') or data.get('principalSubdivision', '')
        locality = data.get('locality', '')
        display = ' '.join([p for p in [city, locality] if p])
        return jsonify({ 'display': display })
    except Exception as e:
        # 에러 발생 시 빈 문자열 반환
        return jsonify({ 'display': '' })


@app.route('/api/health/internet')
def api_health_internet():
    """간단한 인터넷 연결 상태 확인 (HTTP 204 체크)"""
    try:
        url = "http://connectivitycheck.gstatic.com/generate_204"
        req = urllib.request.Request(url, headers={'User-Agent': 'TruckGPS/1.0'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            # 204 또는 200 아무거나 오면 연결된 것으로 간주
            code = resp.getcode()
            return jsonify({ 'connected': code in (204, 200) })
    except Exception:
        return jsonify({ 'connected': False })


@app.route('/api/health/temperature')
def api_health_temperature():
    """최근 온도 데이터 수집 여부로 센서 연결 상태 추정"""
    try:
        from datetime import datetime
        import time
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT timestamp, temperature
            FROM gps_temperature_data
            WHERE temperature IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            return jsonify({ 'connected': False, 'age_s': None })
        last_ts, last_temp = row
        age = max(0.0, time.time() - float(last_ts))
        # 15초 이내 업데이트면 연결 OK로 판단
        return jsonify({ 'connected': age <= 5.0, 'age_s': age })
    except Exception:
        return jsonify({ 'connected': False, 'age_s': None })


if __name__ == '__main__':
    import os
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=int(os.getenv('DASHBOARD_PORT', '5001')))
    args = parser.parse_args()
    # 라즈베리파이 로컬 모니터 표시용으로 0.0.0.0 바인드, 기본 5001 포트
    app.run(host='0.0.0.0', port=args.port, debug=False)


