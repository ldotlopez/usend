# Housekeeper OS
Base image:
https://downloads.raspberrypi.org/raspbian_lite_latest

Install packages:

```
sudo apt-get update -qq
sudo apt-get dist-upgrade -yqq
sudo apt-get install -yqq \
	htop \
	git \
	iftop \
	iotop \
	python3-virtualenv \
	tmux \
	vim \
	virtualenvwrapper
sudo rpi-update
sudo reboot
```


## Videosec

```
sudo apt-get install -yqq \
	gstreamer1.0-alsa \
	gstreamer1.0-libav \
	gstreamer1.0-omx-rpi \
	gstreamer1.0-plugins-good \
	gstreamer1.0-plugins-bad \
	gstreamer1.0-tools \
```

List video formats for v4l2:

`v4l2-ctl --list-formats-ext`


Test it:

```
gst-launch-1.0 v4l2src \
	! 'video/x-raw,width=800,height=600,framerate=(fraction)30/1' ! \
	! decodebin \
	! videoconvert \
	! fbdevsink
```

### OpenCV Appendix

```
sudo mkdir -p /usr/share/OpenCV/haarcascades
wget -O - https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml \
	| sudo tee -a "/usr/share/OpenCV/haarcascades/haarcascade_frontalface_default.xml"
```
