# Building the i386 VM for spotify guest

Check this: https://github.com/Spotifyd/spotifyd/

Ports:
- 2222 VM ssh
- 5900 qemu-vnc
- 5910 Xvfb VNC server

Tip: You don't need to create the VM on the RPI.

1. Create a 5 Gb qcow2 image for the system

`qemu-img create -O qcow2 hda.qcow2 5G`

2. Get mini.iso from Debian

```
curl \
	-s -o "mini.iso" \
	'http://ftp.debian.org/debian/dists/stable/main/installer-i386/current/images/netboot/mini.iso'
```

3. Run qemu and install ()

Keep install as simple and minimal as possible but:
- the default user must be `spotify`
- hostname must be `spotify`
- Install ssh server package

```
qemu-system-i386 \
	-drive file=hda.qcow2,format=qcow2,aio=native,cache.direct=on \
	-cdrom mini.iso \
	-nic user,hostfwd=tcp::2222-:22 \
	-soundhw ac97 \
	-m 256M \
	-boot order=cd \
	-display vnc=:0
```


```
qemu-system-i386 \
	-drive file=hda.qcow2,format=qcow2,aio=native,cache.direct=on \
	-cdrom mini.iso \
	-nic user,hostfwd=tcp::2222-:22,hostfwd=tcp::5910-:5910 \
	-soundhw ac97 \
	-m 256M \
	-boot order=cd \
	-display vnc=:0
```

4. Configure ssh server

```
ssh-keygen -f vm-sshkey
ssh-copy-id -i vm-sshkey.pub -p 2222 spotify@localhost
```

Use `ssh -i vm-sshkey -p 2222 spotify@localhost` to connect to the VM

4. Disable GRUB delay

[TBD]

5. Install additional packages (on the VM)

```
sudo apt-get install dirmngr
sudo apt-key adv \
	--keyserver hkp://keyserver.ubuntu.com:80 \
	--recv-keys 931FF8E79F0876134EDDBDCCA87FF9DF48BF1C90
echo deb http://repository.spotify.com stable non-free | \
	sudo tee /etc/apt/sources.list.d/spotify.list
sudo apt-get update
sudo apt-get \
	install --no-install-recommends \
	xvfb x11vnc spotify-client dbus-x11
```

5. Setup spotify

```
Xvfb; spotify; x11vnc -display :0 -rfbport 5910
```

5. Install some resources:

- systemd unit filestw

6. Other

Use `-display none` for qemu in production


7. Run the VM from the rpi:

qemu-system-i386 -drive file=hda.qcow2,format=qcow2,aio=native,cache.direct=on -net user,hostfwd=tcp::2222-:22,hostfwd=tcp::5910-:5910 -soundhw ac97 -m 512M -boot order=cd -display vnc=:0 -net nic
