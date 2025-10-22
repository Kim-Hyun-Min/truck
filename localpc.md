### mqtt 브로커 역할
-- 서버열기 
(관리자 powershell)
& "C:\Program Files\mosquitto\mosquitto.exe" -c "C:\Program Files\mosquitto\mosquitto.conf" -v

### db
(powershell)
 python .\mqtt_to_mariadb.py
