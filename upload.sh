ip=192.168.177.214

ssh root@$ip "mkdir -p /usr/bin/gpio-daemon"
scp led.py root@$ip:/usr/bin/gpio-daemon/led.py
scp mt7688gpio.py root@$ip:/usr/bin/gpio-daemon/mt7688gpio.py
scp main.py root@$ip:/usr/bin/gpio-daemon/main.py
scp button.py root@$ip:/usr/bin/gpio-daemon/button.py
scp start.sh root@$ip:/usr/bin/gpio-daemon/start.sh
