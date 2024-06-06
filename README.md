# ezshare-raspberry

Automatically download the pictures from your ez Share wifi SD card (or other USB-mounted storage) and upload them to Google Photos

## About

The LZeal wifi SD cards branded as "ez Share" are the only ones that are still in the market. They've doubled in price since all competition appearantly stopped production and they come with only very basic software.

Not really good value for your money, unless...

I have a Raspberry Pi at home that is always on, doing background jobs like taking back-ups from my PC's and now it's got a new responsability.

As soon as a camera with an ez Share SD card is broadcasting its SSID, the Pi will connect to it, download the images from the card and upload them to Google Photo's, using the script in this repository.

Because the wifi process is not working satisfyingly in all situations, there's also a script to process images when you mount an SD card as USB device.

## Prerequisites

- Network Manager; it wasn't installed on my Raspbian 10; check the internet for installation instructions for your distro [only needed for wifi cards]
  `sudo apt install network-manager`
- Python API for the Network Manager `nmcli` command [only needed for wifi cards]
  `sudo python3 -m pip install nmcli` or `sudo apt install python3-networkmanager` 
- ExifRead module for python [always needed] 
  `sudo python3 -m pip install exifread`
- usbmount package, to automatically mount USB storage devices. To make it work on my Raspberry Pi, I had to apply this fix: [usb - Raspberry 4 usbmount not working - Raspberry Pi Stack Exchange](https://raspberrypi.stackexchange.com/questions/100312/raspberry-4-usbmount-not-working/107449#107449). [only needed for usb cards]
- gphotos-uploader-cli; see next section

## Install gphotos-uploader-cli

`git clone https://github.com/gphotosuploader/gphotos-uploader-cli`

And in that directory: `make build`.

Moved the executable to somewhere in your PATH

Run `gphotos-uploader-cli init`

Edit `~/.gphotos-uploader-cli/config.hjson`:

```
{
    APIAppCredentials: {
        ClientID: "YOUR_CLIENT_ID"
        ClientSecret: "YOUR_CLIENT_SECRET"
    }
    Account: "YOUR_EMAIL_LOGIN_FOR_GOOGLE"
    SecretsBackendType: file
    Jobs: [
        {
        SourceFolder: "~/upload"
            Album: "template:%_directory%"
            DeleteAfterUpload: false
            IncludePatterns: []
            ExcludePatterns: []
        }
    ]
}
```

Run `gphotos-uploader-cli auth` browser logging in to google.

Add to `~/.profile`:

```
export GPHOTOS_CLI_TOKENSTORE_KEY=

```

## Initial setup

1. Install the prerequisites.
3. Clone this repository `git clone https://github.com/vicmortelmans/ezshare-raspberry.git` and `cd` into it
4. Run `./script/install-ezschare` or `./script/install-usbdcim` to install and activate this script as a service.
5. Check the status with `sudo systemctl ezshare-raspberry status` or `sudo systemctl usbdcim-raspberry status` 
6. For using the wifi downloading, configure your ezShare wifi SD card with following settings:
  - SSID. The cards are preconfigured as `ez Share`. Just add a space and your camera name, e.g. `ez Share X100S`. This is especially useful when you have multiple SD cards, because the camera name will be copied into the album name on Google Photos.
  - Wifi password. Change the wifi password of the card to `Rodinal9`. This wifi password is hardcoded in the script. You can change it in code, if you're afraid that someone would find out and steal your pictures... Don't forget to re-run `./script/install` afterwards!
7. For using the USB downloading, add an empty file in the root directory of the card, with a name `ez Share X100S`. 'X100S' can be your camera name, this will be copied into the album name on Google Photos.

## Usage

Everything should work automatically. Typically you would keep the SD card in the camera at all times. Just power on the camera in the neighbourhood of the Raspberry Pi and after a couple of minutes (depending on the number of images) the images should start appearing on Google Photo's.

The pictures are organized in albums named as follows: `<YYYYMMDD> <camera name>`

The pictures are not removed from the SD card, so you regularly have to check if all images are uploaded and then delete all images from your SD card. 

For USB downloading, insert the card into an USB adapter and plug it into the Raspberry Pi. 

## Important remarks

- While connecting to the ezShare wifi SD card, the Raspberry Pi will be temporarily disconnected from the your home wifi network! This may disrupt the operation of other applications running on your Raspberry Pi. Depending on your camera, power to the SD card may stay up even if you turn off the camera, so your network will be interrupted every minute or so, while the script is checking if the camera has new images.
- The script may work on other linux devices as well, but note that the service is configured to run as user `pi` (group `pi`). If you want this to be another user, modify `ezshare-raspberry.service`. 
- The smoothness of the operation may vary depending on your camera. It must keep the SD card powered for the wifi to work. On my Fujifilm X100S, the SD card is always powered when the camera is on, and it remains powered a couple of minutes after you switch it off; that's ideal. On my Sony A850, the SD card seems only to be powered intermittently and for successfully transferring images you have to configure power saving to at least 5 minutes and open the menu for a while. On my Epson R-D1, the wifi card can't be used at all...

## Sound

Sound configuration problem reported in `/var/log/syslog`: `"Error opening PCM device. -- CODE: -16 -- MSG: Device or resource busy"` and not seen when running the script in a terminal, is solved by configuring `/etc/asound.conf`, adding:

```
defaults.pcm.card 0
defaults.ctl.card 0
```
