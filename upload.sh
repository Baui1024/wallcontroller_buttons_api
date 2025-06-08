ip=192.168.177.51

ssh root@$ip "mkdir -p wallcontroller"
scp led.py root@$ip:/usr/bin/gpio-daemon/led.py
scp main.py root@$ip:/usr/bin/gpio-daemon/main.py
scp button.py root@$ip:/usr/bin/gpio-daemon/button.py
scp cert.pem root@$ip:/usr/bin/gpio-daemon/cert.pem
scp key.pem root@$ip:/usr/bin/gpio-daemon/key.pem