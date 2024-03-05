#! /bin/bash

if [ ! -d '/home/main' ]; then
  #useradd -m main
  adduser --disabled-password --gecos "" main # makes the difference for debian
  # usermod main -aG sudo
fi

if [ ! -d '/home/main/.ssh' ]; then
  mkdir /home/main/.ssh
fi

if [ ! -e '/home/main/.ssh/id_rsa.pub' ]; then
  ssh-keygen -f /home/main/.ssh/id_rsa -t rsa -b 4092 -P ''
  cat /home/main/.ssh/id_rsa.pub >> /home/main/.ssh/authorized_keys
fi
echo 'the main ssh pubkey:'
cat /home/main/.ssh/id_rsa.pub
chown -R main:main /home/main/.ssh

if [ "$#" -eq 1 ]; then
  vTelegramBotKey=$1
  exit
else
  #echo 'no arguments provided! telegram bot key expected!'
  read -p 'enter telegram bot key: ' vTelegramBotKey
fi
if [[ "$vTelegramBotKey" =~ [0-9]+:[0-9A-Za-z]+ ]]; then
  echo 'the telegram key: ' \"$vTelegramBotKey\"
else
  echo 'invalid telegram key format: ' \"$vTelegramBotKey\"
  exit
fi

if [ ! -e "/opt/outline/access.txt" ]; then
  echo 'installing the outline vpn service'
  wget -O - https://raw.githubusercontent.com/Jigsaw-Code/outline-apps/master/server_manager/install_scripts/install_server.sh | sh
fi
#cat /opt/outline/access.txt
vOutlineApiUrl=$(grep "^apiUrl:" /opt/outline/access.txt | cut -d ":" -f 2,3,4)
vOutlineCertSha256=$(grep "^certSha256:" /opt/outline/access.txt | cut -d ":" -f 2)
echo 'outline apiUrl: '\"$vOutlineApiUrl\"
echo 'outline certSha256: '\"$vOutlineCertSha256\"

if [ ! -d "/srv/OutlineVpnBot" ]; then
  echo 'installing the outline vpn bot repo'
  git clone https://github.com/nikozdev/OutlineVpnBot /srv/OutlineVpnBot
  python3 -m venv /srv/OutlineVpnBot/venv
  /srv/OutlineVpnBot/venv/bin/pip install -r /srv/OutlineVpnBot/venv/reqs.txt
fi
echo '' > /srv/OutlineVpnBot/conf/.env
echo 'vTelegramBotKey='\"$vTelegramBotKey\" >> /srv/OutlineVpnBot/conf/.env
echo 'vOutlineApiUrl='\"$vOutlineApiUrl\" >> /srv/OutlineVpnBot/conf/.env
echo 'vOutlineCertSha256='\"$vOutlineCertSha256\" >> /srv/OutlineVpnBot/conf/.env
chown -R main:main /srv/OutlineVpnBot

if [ ! -e "/lib/systemd/system/OutlineVpnBot.service" ]; then
  echo 'installing the outline vpn bot service'
  wget -O - https://raw.githubusercontent.com/nikozdev/OutlineVpnBot/main/conf/OutlineVpnBot.service > /lib/systemd/system/OutlineVpnBot.service
fi
systemctl daemon-reload
systemctl enable OutlineVpnBot
systemctl restart OutlineVpnBot

echo 'success'
