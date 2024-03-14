#!/usr/bin/python3
#import beepy
import datetime
import exifread
import getpass
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


#all USB drives should contain a root file "ez Share X100S", where 'X100S' is variable and 
#identifies your camera; this string will be replicated in the album names
#(if the USB drive is actually an ez Share SD card, use the same name !!)

#for each camera a text file is stored that lists all ever downloaded filenames
_HISTORY = os.path.expanduser("~/.ezshare-raspberry-history")
os.makedirs(_HISTORY, exist_ok=True)

#temporary workspace while downloaden/uploading files
_TEMP = "/tmp/usbdcim_temporary_files"
os.makedirs(_TEMP, exist_ok=True)

#path where the find automounted usb drives
_USB = "/media"

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d %(funcName)s] %(message)s', datefmt='%Y-%m-%d:%H:%M:%S', level=logging.INFO)

def main():

    logging.info(f"Running as {getpass.getuser()}")

    try:

        #endless polling loop
        while True: 

            #import pdb; pdb.set_trace()

            usb_name, usb_path = find_first_mounted_ezshare_usb_name()

            if usb_name:

                #beepy.beep(sound="success")

                try:

                    camera_name = get_camera_name(usb_name)
                    downloaded_files = list_downloaded_files(camera_name)
                    filenames = get_list_of_filenames_on_camera(usb_path)
                    
                    count = 0
                    for (path, filename) in filenames:

                        count += 1
                        if filename not in downloaded_files:

                            logging.info(f"Progress {count} of {len(filenames)}")
                            download_result = download(camera_name, path, filename)
                            
                            #if download_result:
                                #beepy.beep(sound="ping")
                            #else:
                                #beepy.beep(sound="error")

                    unmount(usb_path)
                    #beepy.beep(sound="ready")
                    upload_result = upload_to_photos(camera_name)

                    if upload_result:

                        delete_files()
                        for (path, filename) in filenames:
                            add_to_list_of_downloaded_files(camera_name, filename)
                        logging.info("Success!")

                    else:

                        logging.warning("Failure!")

                    logging.info("Sleeping")
                    time.sleep(10)  # wait an extra 10 seconds before polling again

                except Exception as e:

                    logging.error(f"There's a problem processing '{usb_path}': {e}")

            logging.info("Sleeping")
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


def list_downloaded_files(camera_name):
    filename = f"{_HISTORY}/{camera_name}.txt"
    try:
        file = open(filename)
        lines = file.read().splitlines()
        file.close()
    except FileNotFoundError:
        file = open(filename, "w")
        logging.warning(f"Created empty file: '{filename}'")
        lines = []
        file.close()
    logging.info(f"Number of images ever downloaded from '{camera_name}': {str(len(lines))}")
    return lines


def get_list_of_filenames_on_camera(usb_path):
    # returning a list of tuples (path, filename)

    list_of_filenames = []
    files = glob.glob(f"{usb_path}/DCIM/*/*.JPG")

    for file in files:

        filename = file.split('/')[-1]
        path = file.split(filename)[0]
        logging.info(f"File on card: {file}")
        list_of_filenames.append((path, filename))

    logging.info(f"Retrieved a list of {len(list_of_filenames)} files that are on the card")
    return list_of_filenames


def download(camera_name, path, filename):
    # the file is downloaded, the date is fetched and the file is stored into
    # {_TEMP}/{date} {camera_name}/{filename}
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
        try:
            f = open(filepath, 'rb')
            tags = exifread.process_file(f)
            datetime_tag = tags['EXIF DateTimeOriginal']
            datetime_string = datetime_tag.values
            datetime_object = datetime.datetime.strptime(datetime_string, '%Y:%m:%d %H:%M:%S')
            date = datetime_object.strftime('%Y%m%d')
            logging.info(f"Fetched the date from exif: '{date}'")
        except Exception as e:
            date = datetime.datetime.now().strftime('%Y%m%d')
            logging.info(f"No date in exif, using today: '{date}'; because: {e}")
        # move to album
        album_directory = f"{_TEMP}/{date} {camera_name}"
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


def upload_to_photos(camera_name):

    def _upload_to_photos():
        logging.info("Launching Jiotty Photo Uploader...")
        out = subprocess.getoutput(f"/opt/jiotty-photos-uploader/bin/JiottyPhotosUploader -r {_TEMP}")
        out = out.split('\n')
        for i in out:
            if "All done without fatal errors" in i:
                logging.info("Pictures successfully uploaded to Google Photo's")
                return True  # Success
        else:
            logging.error("Error uploading pictures to Google Photo's; here's Jiotty's output:")
            for i in out:
                logging.error(i)
            return False  # Failure
        
    # check if there are files in the folder(s) for 'camera_name'
    # if so, do an upload (this will upload other folders as well)
    temp_dirs = os.listdir(_TEMP)
    for temp_dir in temp_dirs:
        if camera_name in temp_dir:
        # return immedialely: all images are uploaded
            return _upload_to_photos()
    else:
        logging.info("No pictures to upload")
        return True


def delete_files():
    dirs = glob.glob(_TEMP + "/*")
    for d in dirs:
        shutil.rmtree(d)
    logging.info(f"Deleted {len(dirs)} directories in {_TEMP}")


if __name__ == "__main__":
    main()
