Base image:
https://downloads.raspberrypi.org/raspbian_lite_latest

Install packages:
sudo apt-get update -qq
sudo apt-get dist-upgrade -yqq
sudo apt-get install -yqq \
	git htop iotop iftop python3-virtualenv virtualenvwrapper  tmux vim
rpi-update
reboot


## Videosec

sudo apt-get install gstreamer1.0-omx-bellagio-config gstreamer1.0-omx-rpi gstreamer1.0-tools gstreamer1.0-plugins-good gstreamer1.0-alsa gstreamer1.0-libav