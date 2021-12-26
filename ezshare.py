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

                    #import pdb; pdb.set_trace()

                            
                    camera_name = get_camera_name(ez_ssid)
                    home_network = find_active_connection()
                    downloaded_files = list_downloaded_files(camera_name)
                    connect_to_ezshare_ssid(ez_ssid)
                    filenames = get_list_of_filenames_on_camera()
                    
                    for (directory, filename) in filenames:

                        if filename not in downloaded_files:

                            download_result = download(camera_name, directory, filename)
                            
                            if download_result:
                                add_to_list_of_downloaded_files(camera_name, filename)

                    connect_to_home_network(home_network)
                    upload_result = upload_to_photos(camera_name)

                    if upload_result:

                        delete_files()
                        logging.info("Success!")

                    else:

                        logging.warning("Failure!")

                    logging.debug("Sleeping")
                    time.sleep(10)  # wait an extra 10 seconds before polling again

                except Exception as e:

                    if home_network:
                        connect_to_home_network(home_network)
                    logging.error(f"There's a problem processing '{ez_ssid}': {e}")

            logging.debug("Sleeping")
            time.sleep(10)  # poll every 10 seconds for active cards
                

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


def connect_to_ezshare_ssid(ssid):
    try:
        logging.info(f"Going to connect to '{ssid}'")
        nmcli.device.wifi_connect(ssid=ssid, password=_PASSWORD)
        logging.info(f"Connected to '{ssid}'")
    except Exception as e:
        logging.error(f"Error connecting to '{ssid}': {e}")
        raise e


def get_list_of_filenames_on_camera():
    domain = "http://ezshare.card/"
    url = domain + "mphoto"
    # in this html, <img> elements represent the pictures on the SD card and 
    # their @src attribute looks like this:
    # thumbnail?fname=DSCF3479.JPG&fdir=103_FUJI&ftype=0&time=1389464558
    # where the timestamp is not usable
    # returning a list of tuples (dir, filename)

    list_of_filenames = []

    while True:
        
        try:
            logging.debug(f"Loading '{url}'")
            with requests.get(url) as req:
                html = req.content
        except Exception as e:
            logging.error(f"Error downloading list of pictures from camera: {e}")
            raise e
        try:
            soup = BeautifulSoup(html, 'html.parser')
            # parse image files
            for img in soup.select('img'):
                src = img.attrs['src']
                query = urllib.parse.urlparse(src)
                query_dict = urllib.parse.parse_qs(query.query)
                filename = query_dict["fname"][0]
                directory = query_dict["fdir"][0]
                logging.debug(f"File on card: {query.query}")
                list_of_filenames.append((directory, filename))
            # parse for next page
            next = soup.select('div#post a')
            if next:
                url = domain + next[0].attrs['href']
                logging.info(f"There's another page at '{url}'")
            else:
                logging.info("This was the last page")
                break
        except Exception as e:
            logging.error(f"Error parsing list of picturs from camera: {e}")
            raise e

    logging.info(f"Retrieved a list of {len(list_of_filenames)} files that are on the card")
    return list_of_filenames


def download(camera_name, directory, filename):
    # the file is downloaded, the date is fetched and the file is stored into
    # {_TEMP}/{date} {camera_name}/{filename}
    url = f"http://ezshare.card/DCIM/{directory}/{filename}"
    directory = f"{_TEMP}"

    try:
        # download to {_TEMP}
        filepath = f"{_TEMP}/{filename}"
        logging.info(f"Going to download {url}")
        sleep = 1
        for attempt in range(10):
            try:
                logging.info(f"Downloading {url}")
                with requests.get(url, allow_redirects=True, timeout=10.0) as req:
                    blob = req.content
                open(filepath, 'wb').write(blob)
            except Exception as e:
                time.sleep(sleep)  # pause hoping things will normalize
                logging.warning(f"Sleeping {sleep} seconds because of error trying to download {url} ({e}).")
                sleep *= 2
            else:
                logging.info(f"Downloaded '{filepath}'")
                break  # no error caught
        else:
            logging.critical(f"Retried 10 times downloading {url}")
        # fetch date
        f = open(filepath, 'rb')
        tags = exifread.process_file(f)
        datetime_tag = tags['EXIF DateTimeOriginal']
        datetime_string = datetime_tag.values
        if datetime_string == '0000:00:00 00:00:00':
            date = datetime.datetime.now().strftime('%Y%m%d')
        else:
            datetime_object = datetime.datetime.strptime(datetime_string, '%Y:%m:%d %H:%M:%S')
            date = datetime_object.strftime('%Y%m%d')
        logging.info(f"Fetched the date from exif: '{date}'")
        # move to album
        album_directory = f"{_TEMP}/{date} {camera_name}"
        os.makedirs(album_directory, exist_ok=True)
        final_filepath = f"{album_directory}/{filename}"
        os.replace(filepath, final_filepath)
        logging.info(f"Moved '{filepath}' to '{final_filepath}'")
        return True
    except Exception as e:
        logging.error(f"Error downloading '{filename}': {e}")
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


def connect_to_home_network(name):
    try:
        nmcli.connection.up(name)
        logging.info(f"Reconnected to home network '{name}'")
    except Exception as e:
        logging.error(f"Error reconnecting to home network '{name}': {e}")
        # don't propagate, this function is in other exception handlers
        # and that seems to cause problems


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
