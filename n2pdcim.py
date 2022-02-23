#!/usr/bin/python3
import datetime
import exifread
import glob
import logging
import nmcli
import os
import os.path
import requests
import shutil
import subprocess
import time
import traceback
import urllib.parse
from bs4 import BeautifulSoup


#this script is for downloading raw files from an USB drive with a card that is reserved
#for digitizing black and white negative images. This card should contain a file in root
#named "n2p", and NO root file name "ez Share *", because then the usbdcim.py script will
#run through usbdcim.py and unmount the drive prematurely.

#no history is maintained, cards should be emptied manually

#temporary workspace while downloaden/uploading files
_TEMP = "/tmp/n2pdcim_temporary_files"
os.makedirs(_TEMP, exist_ok=True)

#path where the find automounted usb drives
_USB = "/media"

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d %(funcName)s] %(message)s', datefmt='%Y-%m-%d:%H:%M:%S', level=logging.DEBUG)

def main():

    try:

        #endless polling loop
        while True: 

            #import pdb; pdb.set_trace()

            usb_name, usb_path = find_first_mounted_n2pdcim_usb_name()

            if usb_name:

                try:

                    filenames = get_list_of_filenames_on_camera(usb_path)
                    
                    for (path, filename) in filenames:

                        download_result = download(path, filename)
                        
                    unmount(usb_path)
                    upload_result = upload_to_photos(camera_name)

                    if upload_result:

                        delete_files()
                        logging.info("Success!")

                    else:

                        logging.warning("Failure!")

                    logging.debug("Sleeping")
                    time.sleep(10)  # wait an extra 10 seconds before polling again

                except Exception as e:

                    logging.error(f"There's a problem processing '{usb_path}': {e}")

            logging.debug("Sleeping")
            time.sleep(10)  # poll every 10 seconds for active cards
                

    #execute this code if CTRL + C is used to kill python script
    except KeyboardInterrupt:

        print("Bye!")

    except Exception as e:

        logging.error(traceback.format_exc())
        # Logs the error appropriately.


def find_first_mounted_ezshare_usb_name():

    files = glob.glob(f"{_USB}/*/ez Share*")
    if files:
        usb_name = files[0].split('/')[-1]
        usb_path = files[0].split(usb_name)[0]
        logging.info(f"'{usb_name}' is mounted!")
        return usb_name, usb_path
    else:
        return None, None


def get_camera_name(ssid):
    camera_name = ssid.split("ez Share", 1)[1].lstrip()
    if camera_name:
        logging.info(f"Camera name is: '{camera_name}'")
    else:
        camera_name = "usbdcim"
        logging.warning(f"No camera name, using default: '{camera_name}'")
    return camera_name


def get_list_of_filenames_on_camera(usb_path):
    # returning a list of tuples (path, filename)

    list_of_filenames = []
    files = glob.glob(f"{usb_path}/DCIM/*/*.ARW")

    for file in files:

        filename = file.split('/')[-1]
        path = file.split(filename)[0]
        logging.debug(f"File on card: {file}")
        list_of_filenames.append((path, filename))

    logging.info(f"Retrieved a list of {len(list_of_filenames)} files that are on the card")
    return list_of_filenames


def download(path, filename):
    # the file is downloaded, the date is fetched and the file is stored into
    # {_TEMP}/{date}/{filename}
    file = f"{path}/{filename}"
    directory = f"{_TEMP}"

    try:
        # download to {_TEMP}
        os.makedirs(_TEMP + "/tmp", exist_ok=True)
        filepath = f"{_TEMP}/tmp/{filename}"

        logging.info(f"Going to copy {file}")
        sleep = 1
        for attempt in range(10):
            try:
                logging.info(f"Copying {file}")
                shutil.copyfile(file, filepath)
            except Exception as e:
                time.sleep(sleep)  # pause hoping things will normalize
                logging.warning(f"Sleeping {sleep} seconds because of error trying to copy {file} ({e}).")
                sleep *= 2
            else:
                logging.info(f"Downloaded '{filepath}'")
                break  # no error caught
        else:
            logging.critical(f"Retried 10 times copying {file}")
        # fetch date
        date = datetime.datetime.now().strftime('%Y%m%d')
        # move to album
        album_directory = f"{_TEMP}/{date}"
        os.makedirs(album_directory, exist_ok=True)
        final_filepath = f"{album_directory}/{filename}"
        os.replace(filepath, final_filepath)
        logging.info(f"Moved '{filepath}' to '{final_filepath}'")
        return True
    except Exception as e:
        logging.error(f"Error downloading '{filename}': {e}")
        logging.error(traceback.format_exc())
        return False



def add_to_list_of_downloaded_files(camera_name, filename):
    history_filename = f"{_HISTORY}/{camera_name}.txt"
    try:
        file = open(history_filename, "a")
        file.write(f"{filename}\n")
        file.close()
        logging.info(f"Added '{filename}' to '{history_filename}'")
    except Exception as e:
        logging.error(f"Error adding '{filename}' to '{history_filename}': {e}")


def unmount(usb_path):
    os.system(f"pumount {usb_path}")
    logging.info(f"Unmounted {usb_path}")



def delete_files():
    dirs = glob.glob(_TEMP + "/*")
    for d in dirs:
        shutil.rmtree(d)
    logging.info(f"Deleted {len(dirs)} directories in {_TEMP}")


if __name__ == "__main__":
    main()
