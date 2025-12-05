ip=192.168.177.178

echo "Uploading to $ip"
sshpass -f "passwordfile" ssh root@$ip "mkdir -p /usr/bin/gpio-daemon"
sshpass -f "passwordfile" scp main.py root@$ip:/usr/bin/gpio-daemon/main.py
sshpass -f "passwordfile" scp led.py root@$ip:/usr/bin/gpio-daemon/led.py
sshpass -f "passwordfile" scp mt7688gpio.py root@$ip:/usr/bin/gpio-daemon/mt7688gpio.py
sshpass -f "passwordfile" scp button.py root@$ip:/usr/bin/gpio-daemon/button.py
sshpass -f "passwordfile" scp start.sh root@$ip:/usr/bin/gpio-daemon/start.sh
echo "Upload complete. Restarting Service"
sshpass -f "passwordfile" ssh root@$ip "/etc/init.d/gpio-daemon restart"
echo "Done"