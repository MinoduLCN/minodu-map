# Minodu Map Hardware Tests



## Setup sound card

* install raspberry pi os lite

* `sudo apt-get update`

* `sudo apt install git`

* 
  ```shell
  git clone https://github.com/Seeed-Studio/seeed-linux-dtoverlays.git
  cd seeed-linux-dtoverlays/
  make overlays/rpi/respeaker-2mic-v1_0-overlay.dtbo
  sudo cp overlays/rpi/respeaker-2mic-v1_0-overlay.dtbo /boot/firmware/overlays/respeaker-2mic-v1_0.dtbo  
  echo "dtoverlay=respeaker-2mic-v1_0" | sudo tee -a /boot/firmware/config.txt  
  ```

* `sudo reboot`

* turn volume up with

  ```
  amixer -c seeed2micvoicec sset 'Left Output Mixer PCM' on
  amixer -c seeed2micvoicec sset 'Right Output Mixer PCM' on
  amixer -c seeed2micvoicec sset 'Headphone' 100%
  amixer -c seeed2micvoicec sset 'Speaker' 100%
  amixer -c seeed2micvoicec sset 'Playback' 100%
  speaker-test -D plughw:seeed2micvoicec -c 2 -r 48000 -t sine -l 1
  ```

* Download audio with `curl https://file-examples.com/storage/fe1a8a69786ac397598f5bb/2017/11/file_example_WAV_1MG.wav --output sound.wav`

* test with `aplay -D plughw:1,0 sound.wav`

* save alsamixer with `sudo alsactl store`



## Setup scripts

### Script for just the keys

* `sudo apt install python3-dev build-essential`

* ```
  sudo apt update
  sudo apt install python3-dev build-essential
  source ~/neokey/bin/activate
  pip install adafruit-blinka adafruit-circuitpython-neopixel
  pip install adafruit-circuitpython-seesaw
  ```

* `python keys.py`

### Script for keys + strip

* `sudo nano /boot/firmware/config.txt` add:

  ```
   dtparam=spi=on #uncomment at top
   
   # add ad bottom
   core_freq=250

* `sudo reboot`*

* install libraries

  ```
  source ~/neokey/bin/activate
  pip install adafruit-circuitpython-neopixel-spi
  ```

### Script for keys + strip + encoder

* `sudo raspi-config` → Interface Options → I2C → Enable → reboot.

### Create autostart service

Create the service file

`sudo nano /etc/systemd/system/keys-strip.service`

Paste this, replacing /home/pi with your path:

```
[Unit]
Description=NeoKey keys_strip script
After=multi-user.target

[Service]
Type=simple
ExecStart=/home/pi/neokey/bin/python /home/pi/map/keys_strip_encoder.py
WorkingDirectory=/home/pi/map
Restart=on-failure
RestartSec=5
User=root
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

3. Enable and start it

```
sudo systemctl daemon-reload
sudo systemctl enable keys-strip.service
sudo systemctl start keys-strip.service
```

  
