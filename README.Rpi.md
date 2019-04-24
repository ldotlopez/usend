## Headless install

_(Run those commands in the install image)_

1. Enable ssh by default  
`touch /boot/ssh`

2. Configure WiFi

Write `/boot/wpa_supplicant.conf` with this info:

<pre>
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=your_ISO-3166-1_two-letter_country_code

network={
    ssid="your_SSID"
    psk="your_PSK"
    key_mgmt=WPA-PSK
}
</pre>



## Google Voice Hat

### Setup audio output

1. Enable overlay:

Add `dtoverlay=googlevoicehat-soundcard` to `/boot/config.txt`

Optional: Disable own rpi sound card adding `dtparam=audio=off`

2. Set hat as default device

List cards with `cat /proc/asound/cards`

Write `/etc/asound.conf` similar to this:
```
pcm.!default {
  type plug
  slave {
    pcm "hw:sndrpigooglevoi,0"
  }
}

ctl.!default {
    type hw
    card sndrpigooglevoi
}
```

3. Test

Use `aplay test.wav`

### AIY board

sudo apt-get install y \
	git \
	ipython \
	libjpeg-dev \
	python3-ipdb \
	python3-ipython \
	python3-pip \
	python3-setuptools

python3 \
	-m pip install \
	'git+https://github.com/google/aiyprojects-raspbian.git#egg=aiy-projects-python&subdirectory=src'


## Enable USB boot

_USB boot is available on the Raspberry Pi 3B, 3B+, 3A+ and Raspberry Pi 2B v1.2 models only._

1. Setup:  

`echo program_usb_boot_mode=1 | sudo tee -a /boot/config.txt`

1. Reboot

`sudo reboot`

1. Check  
 
```
$ vcgencmd otp_dump | grep 17:
17:3020000a
```

## Bluetooth

1. Add pi to bluetoothctl

`sudo adduser pi bluetoothctl`

See: `/etc/dbus-1/system.d/bluetooth.conf`

2. Reboot

`sudo reboot`

3. Check
```
pi@raspberrypi:~ $ bluetoothctl
[NEW] Controller B8:27:EB:DD:AC:B8 raspberrypi [default]
```

apt install bluealsa python3-gi python3-pydbus python-gobject python-dbus

https://github.com/nicokaiser/rpi-audio-receiver/blob/master/install-bluetooth.sh


## Rotate display

`echo display_rotate=1 | sudo tee -a /boot/config.txt`
