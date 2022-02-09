USER=$(logname)
curl https://packages.microsoft.com/config/ubuntu/18.04/multiarch/packages-microsoft-prod.deb > /tmp/packages-microsoft-prod.deb
apt install -y /tmp/packages-microsoft-prod.deb
apt-get update
apt-get install -y moby-engine python3.8 python3.8-venv python3-pip
apt-get update
apt-get install -y aziot-edge
usermod -G docker $USER
newgrp docker
