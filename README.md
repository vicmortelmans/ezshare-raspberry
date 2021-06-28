# ezshare-raspberry
Automatically download the pictures from your ez Share wifi SD card and upload them to Google Photos

The LZeal wifi SD cards branded as "ez Share" are the only ones that are still in the market. They've doubled in price since all competition appearantly stopped production and they come with only very basic software.

I have a Raspberry Pi at home that is always on, doing background jobs like taking back-ups from my PC's and now it's got a new responsability.

As soon as a camera with an ez Share SD card is broadcasting its SSID, the Pi will connect to it, download the images from the card and upload them to Google Photo's, using the script in this repository.

Prerequisites:

- Network Manager wasn't installed on my Raspbian 10; check the internet for installation instructions for your distro  
  `sudo apt install network-manager`
- Python API for the Network Manager `nmcli` command  
  `sudo python3 -m pip install nmcli`
- [Jiotty Photos Uploader](https://github.com/ylexus/jiotty-photos-uploader) is a very handy tool when you have to upload multiple folders of pictures to Google Photos and for the purpose at hand it also features a CLI  
  `wget 'https://adoptopenjdk.jfrog.io/adoptopenjdk/deb/pool/main/a/adoptopenjdk-14-hotspot/adoptopenjdk-14-hotspot_14.0.2+12-2_armhf.deb'`
  `sudo dpkg -i adoptopenjdk-14-hotspot_14.0.2+12-2_armhf.deb`
  `sudo apt install gradle`  
  `git clone https://github.com/ylexus/jiotty-photos-uploader.git`

