#!/usr/bin/python3
import datetime
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



#all SD cards should be configured with ssid "ez Share X100S", where 'X100S' is variable and 
#identifies your camera; this string will be replicated in the album names
#all SD cards should be configured with the same password:
_PASSWORD = "Rodinal9"

#for each camera a text file is stored that lists all ever downloaded filenames
_HISTORY = os.path.expanduser("~/.ezshare-raspberry-history")
os.makedirs(_HISTORY, exist_ok=True)

#temporary workspace while downloaden/uploading files
_TEMP = "/tmp/ezshare_temporary_files"
os.makedirs(_TEMP, exist_ok=True)


logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d %(funcName)s] %(message)s', datefmt='%Y-%m-%d:%H:%M:%S', level=logging.DEBUG)

def main():

    try:

        home_network = find_active_connection()

        #endless polling loop
        while True: 

            ez_ssid = find_first_active_ezshare_ssid()

            if ez_ssid:

                try:

                    camera_name = get_camera_name(ez_ssid)
                    history_files = get_history_files(camera_name)
                    home_network = find_active_connection()
                    connect_to_ezshare_ssid(ez_ssid)
                    filenames_and_dates = get_list_of_filenames_and_dates()
                    
                    for (directory, filename, date) in filenames_and_dates:

                        if filename not in history_files:

                            download(camera_name, directory, filename, date)

                    #import pdb; pdb.set_trace()

                            
                    connect_to_home_network(home_network)
                    upload_result = upload_to_photos(camera_name)

                    if upload_result:

                        add_temp_files_to_history(camera_name)
                        delete_files()
                        logging.info("Success!")

                    else:

                        logging.warning("Failure!")

                    logging.debug("Sleeping")
                    time.sleep(6)

                except Exception as e:

                    if home_network:
                        connect_to_home_network(home_network)
                    logging.error(f"There's a problem processing '{ez_ssid}': {e}")

            logging.debug("Sleeping")
            time.sleep(6)
                

    #execute this code if CTRL + C is used to kill python script
    except KeyboardInterrupt:

        if home_network:
            connect_to_home_network(home_network)
        print("Bye!")

    except Exception as e:

        if home_network:
            connect_to_home_network(home_network)
        logging.error(traceback.format_exc())
        # Logs the error appropriately.


def find_active_connection():
    connections = nmcli.connection()
    for connection in connections:
        if connection.device != "--":
            logging.info(f"'{connection.name}' is the current network connection")
            return connection.name
    else:
        logging.error("There seems to be no active network connection!")


def find_first_active_ezshare_ssid():

    devices = nmcli.device.wifi()
    for device in devices:
        if "ez Share" in device.ssid:
            logging.info(f"'{device.ssid}' is online!")
            return device.ssid


def get_camera_name(ssid):
    camera_name = ssid.split("ez Share", 1)[1].lstrip()
    if camera_name:
        logging.info(f"Camera name is: '{camera_name}'")
    else:
        camera_name = "ezshare"
        logging.warning(f"No camera name, using default: '{camera_name}'")
    return camera_name


def get_history_files(camera_name):
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



def connect_to_ezshare_ssid(ssid):
    try:
        nmcli.device.wifi_connect(ssid=ssid, password=_PASSWORD)
        logging.info(f"Connected to '{ssid}'")
    except Exception as e:
        logging.error(f"Error connecting to '{ssid}': {e}")
        raise e


def get_list_of_filenames_and_dates():
    url = "http://ezshare.card/mphoto"
    # in this html, <img> elements represent the pictures on the SD card and 
    # their @src attribute looks like this:
    # thumbnail?fname=DSCF3479.JPG&fdir=103_FUJI&ftype=0&time=1389464558
    # where the timestamp is seconds-based with a 234499962 offset compared to epoch
    # returning a tuple (dir, filename, date)
    _OFFSET = 234637072
    try:
        req = requests.get(url)
    except Exception as e:
        logging.error(f"Error downloading list of pictures from camera: {e}")
        raise e
    try:
        soup = BeautifulSoup(req.content, 'html.parser')
        list_of_filenames_and_dates = []
        for img in soup.select('img'):
            src = img.attrs['src']
            query = urllib.parse.urlparse(src)
            query_dict = urllib.parse.parse_qs(query.query)
            filename = query_dict["fname"][0]
            directory = query_dict["fdir"][0]
            epoch_time = int(query_dict["time"][0]) + _OFFSET
            date = datetime.datetime.utcfromtimestamp(epoch_time).strftime("%Y%m%d")
            logging.debug(f"File on card: {query.query} with calculated date '{date}'")
            list_of_filenames_and_dates.append((directory, filename, date))
        logging.info(f"Retrieved a list of {len(list_of_filenames_and_dates)} files that are on the card")
        return list_of_filenames_and_dates

    except Exception as e:
        logging.error(f"Error parsing list of picturs from camera: {e}")
        raise e


def download(camera_name, directory, filename, date):
    url = f"http://ezshare.card/DCIM/{directory}/{filename}"
    temp_directory = f"{_TEMP}/{date} {camera_name}"
    filepath = f"{temp_directory}/{filename}"

    # skip files that are already downloaded
    if not os.path.exists(filepath):
        os.makedirs(temp_directory, exist_ok=True)
        r = requests.get(url, allow_redirects=True)
        open(filepath, 'wb').write(r.content)
        logging.info(f"Downloaded {filepath}")
    else:
        logging.info(f"Skipping {filepath}, it's already downloaded")


def connect_to_home_network(name):
    try:
        nmcli.connection.up(name)
        logging.info(f"Reconnected to home network '{name}'")
    except Exception as e:
        logging.error(f"Error reconnecting to home network '{name}': {e}")
        raise e


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
    history_filename = f"{_HISTORY}/{camera_name}.txt"
    temp_dirs = os.listdir(_TEMP)
    for temp_dir in temp_dirs:
        if camera_name in temp_dir:
            return _upload_to_photos()
    else:
        logging.info("No pictures to upload")
        return True


def delete_files():
    dirs = glob.glob(_TEMP + "/*")
    for d in dirs:
        shutil.rmtree(d)
    logging.info(f"Deleted {len(dirs)} directories in {_TEMP}")


def add_temp_files_to_history(camera_name):
    history_filename = f"{_HISTORY}/{camera_name}.txt"
    temp_dirs = os.listdir(_TEMP)
    filenames = []
    for temp_dir in temp_dirs:
        if camera_name in temp_dir:
            filenames.extend(os.listdir(f"{_TEMP}/{temp_dir}"))

    try:
        file = open(history_filename, "a")
        for filename in filenames:
            file.write(f"{filename}\n")
        file.close()
        logging.info(f"Added {len(filenames)} lines to '{history_filename}'")
    except Exception as e:
        logging.error(f"Error adding {len(filenames)} lines to '{history_filename}'")

    

if __name__ == "__main__":
    main()
