# ezshare-raspberry

Automatically download the pictures from your ez Share wifi SD card and upload them to Google Photos

# About

The LZeal wifi SD cards branded as "ez Share" are the only ones that are still in the market. They've doubled in price since all competition appearantly stopped production and they come with only very basic software.

Not really good value for your money, unless...

I have a Raspberry Pi at home that is always on, doing background jobs like taking back-ups from my PC's and now it's got a new responsability.

As soon as a camera with an ez Share SD card is broadcasting its SSID, the Pi will connect to it, download the images from the card and upload them to Google Photo's, using the script in this repository.

## Prerequisites

- Network Manager; it wasn't installed on my Raspbian 10; check the internet for installation instructions for your distro  
  `sudo apt install network-manager`
- Python API for the Network Manager `nmcli` command  
  `sudo python3 -m pip install nmcli`
- ExifRead module for python  
  `sudo python3 -m pip install exifread`
- [Jiotty Photos Uploader](https://github.com/ylexus/jiotty-photos-uploader) is a very handy tool when you have to upload multiple folders of pictures to Google Photos and for the purpose at hand it also features a CLI. For raspberry pi, download from [Releases](https://github.com/ylexus/jiotty-photos-uploader/releases) the release that ends with `_armhf.deb`. I've run it on a model 3, and that's about as low as you can get, I'm afraid.

## Initial setup

1. Install the prerequisites.
2. Run `jiotty` for an initial setup. For the advanced user, [using your own Google API Client Secret](https://github.com/ylexus/jiotty-photos-uploader/wiki#using-your-own-google-api-client-secret) will give a performance boost! You can try to upload some pictures from the GUI to check if everything is working. 
3. Clone this repository `git clone https://github.com/vicmortelmans/ezshare-raspberry.git` and `cd` into it
4. Run `./script/install` to install and activate this script as a service.
5. Configure your ezShare wifi SD card with following settings:
  - SSID. The cards are preconfigured as `ez Share`. Just add a space and your camera name, e.g. `ez Share X100S`. This is especially useful when you have multiple SD cards, because the camera name will be copied into the album name on Google Photos.
  - Wifi password. Change the wifi password of the card to `Rodinal9`. This wifi password is hardcoded in the script. You can change it in code, if you're afraid that someone would find out and steal your pictures... Don't forget to re-run `./script/install` afterwards!

## Usage

Everything should work automatically. Typically you would keep the SD card in the camera at all times. Just power on the camera in the neighbourhood of the Raspberry Pi and after a couple of minutes (depending on the number of images) the images should start appearing on Google Photo's.

The pictures are organized in albums named as follows: `<YYYYMMDD> <camera name>`

The pictures are not removed from the SD card, so you regularly have to check if all images are uploaded and then delete all images from your SD card. 

## Important remarks

- While connecting to the ezShare wifi SD card, the Raspberry Pi will be temporarily disconnected from the your home wifi network! This may disrupt the operation of other applications running on your Raspberry Pi. Depending on your camera, power to the SD card may stay up even if you turn off the camera, so your network will be interrupted every minute or so, while the script is checking if the camera has new images.
- The script may work on other linux devices as well, but note that the service is configured to run as user `pi` (group `pi`). If you want this to be another user, modify `ezshare-raspberry.service`. 



