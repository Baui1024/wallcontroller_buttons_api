ip=192.168.177.51

ssh root@$ip "mkdir -p wallcontroller"
scp led.py root@$ip:wallcontroller/led.py
scp main.py root@$ip:wallcontroller/main.py
scp button.py root@$ip:wallcontroller/button.py
scp cert.pem root@$ip:wallcontroller/cert.pem
scp key.pem root@$ip:wallcontroller/key.pem