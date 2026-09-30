ssh hilink "mkdir -p /usr/bin/gpio-daemon"
scp main.py hilink:/usr/bin/gpio-daemon/main.py
scp led.py hilink:/usr/bin/gpio-daemon/led.py
scp mt7688gpio.py hilink:/usr/bin/gpio-daemon/mt7688gpio.py
scp button.py hilink:/usr/bin/gpio-daemon/button.py
scp start.sh hilink:/usr/bin/gpio-daemon/start.sh
echo "Upload complete. Restarting Service"
ssh hilink "/etc/init.d/gpio-daemon restart"
echo "Done"