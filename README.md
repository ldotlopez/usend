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
	net-tools \
	python3-virtualenv \
	tmux \
	vim \
	virtualenvwrapper
	python3-venv virtualenvwrapper \
	raspberrypi-sys-mods \
	telnet \
	vim

sudo update-alternatives --set editor /usr/bin/vim.basic
sudo rpi-update
sudo reboot
```

Links:

* [read-only file system](https://github.com/adafruit/Raspberry-Pi-Installer-Scripts/blob/master/read-only-fs.sh)


## WebCam

### Stream to youtube

Using ffmpeg and a h264-capable webcam

```
ffmpeg  -re -strict experimental \
	-f v4l2 -input_format h264 -framerate 15 -video_size 1280x720 -i /dev/video0 \
	-f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 \
	-c:v copy \
	-c:a libmp3lame -ab 128k -ar 44100 \
	-f flv "rtmp://a.rtmp.youtube.com/live2/xxxx-xxxx-xxxx-xxxx"
```

*Notes:*

* YouTube is very strict about streams, any subtle changes on any parameter may broke stream process on yt side.
* We are using **-input_format h264** to get h264 from webcam and **-c:v copy** to pass it directly to the flv muxer
* We are generating a dumb audio stream (**-f lavfi -i anullsrc**) instead of using audio from webcam


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

Motion detection:

gst-launch-1.0 -m v4l2src ! decodebin ! videoconvert ! motioncells ! videoconvert ! autovideosink


#### Links:

[https://wiki.oz9aec.net/index.php?title=Gstreamer_cheat_sheet](https://wiki.oz9aec.net/index.php?title=Gstreamer_cheat_sheet)


### OpenCV Appendix

```
TMPD="$(mktemp -d)"
git clone https://github.com/opencv/opencv.git "$TMPD"
sudo mkdir -p /usr/share/OpenCV/haarcascades/
cp "$TMPD"/data/haarcascades/*.xml "/usr/share/OpenCV/haarcascades/"
```

### Camnoopy PT100

gst-launch-1.0 rtspsrc location='rtsp://user:pass@x.x.x.x/onvif1' ! decodebin ! autovideosink


### Spotify VM

qemu-system-x86
qemu-utils


### Screensaver (kind-of)

gst-launch-1.0 audiotestsrc ! audioconvert ! goom ! videoconvert ! 'video/x-raw,width=800,height=480' ! videoscale method=0 add-borders=true ! fbdevsink
