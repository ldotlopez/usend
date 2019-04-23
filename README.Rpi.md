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


## Rotate display

`echo display_rotate=1 | sudo tee -a /boot/config.txt`
