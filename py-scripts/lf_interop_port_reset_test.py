#!/usr/bin/env python3
"""
NAME: lf_interop_port_reset_test.py

PURPOSE:
         The LANforge interop port reset test enables users to use numerous real Wi-Fi stations and connect them to the
         Access Point (AP) being tested. It then randomly disconnects and reconnects a variable number of stations at
         different time intervals. This test helps evaluate how well the AP handles a dynamic and busy network environment
         with devices joining and leaving the network at random times.

EXAMPLE:
        # To run port-reset test on all active devices with specified number of WIFI resets.

            ./lf_interop_port_reset_test.py --host 192.168.200.83 --mgr_ip 192.168.200.156  --dut TestDut --ssid Netgear5g
            --passwd lanforge --encryp psk2 --reset 5 --time_int 5 --wait_time 5 --release 11

        # To run port-reset test on specified number of devices with specified number of WIFI resets.

            ./lf_interop_port_reset_test.py --host 192.168.200.83 --mgr_ip 192.168.200.156  --dut TestDut --ssid Netgear5g
            --passwd lanforge --encryp psk2 --reset 2 --time_int 5 --wait_time 5 --release 11 --clients 1

SCRIPT_CLASSIFICATION:  Toggling, Report Generation

SCRIPT_CATEGORIES: Interop Port-Reset Test

NOTES:
       The primary objective of this script is to automate the process of toggling WiFi on real devices with the
      InterOp Application, evaluating their performance with an access point. It achieves this by simulating multiple
      WiFi resets as specified by the user.

      * Currently the script will work for the android devices with version 11.

STATUS: Functional

VERIFIED_ON:   23-AUG-2023,
             GUI Version:  5.4.6
             Kernel Version: 5.19.17+

LICENSE:
          Free to distribute and modify. LANforge systems must be licensed.
          Copyright 2023 Candela Technologies Inc

INCLUDE_IN_README: False
"""
import json
import sys
import os
import importlib
import argparse
import time
import datetime
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import logging

if sys.version_info[0] != 3:
    print("This script requires Python3")
    exit()
sys.path.append(os.path.join(os.path.abspath(__file__ + "../../../")))
interop_modify = importlib.import_module("py-scripts.lf_interop_modify")
base = importlib.import_module('py-scripts.lf_base_interop_profile')
lf_csv = importlib.import_module("py-scripts.lf_csv")
realm = importlib.import_module("py-json.realm")
Realm = realm.Realm
lf_report_pdf = importlib.import_module("py-scripts.lf_report")
lf_graph = importlib.import_module("py-scripts.lf_graph")

logger = logging.getLogger(__name__)
lf_logger_config = importlib.import_module("py-scripts.lf_logger_config")


class InteropPortReset(Realm):
    def __init__(self, host,
                 port=8080,
                 dut=None,
                 ssid=None,
                 passwd=None,
                 encryp=None,
                 reset=None,
                 clients= None,
                 mgr_ip=None,
                 time_int=None,
                 wait_time=None,
                 suporrted_release=None
                 ):
        super().__init__(lfclient_host=host,
                         lfclient_port=8080)
        self.all_selected_devices = []
        self.all_laptops = []
        self.user_query = []
        self.available_device_list = []
        self.final_selected_android_list = []
        self.adb_device_list = []
        self.windows_list = []
        self.linux_list = []
        self.mac_list = []
        self.encrypt_value = 0
        self.host = host
        self.port = port
        self.phn_name = []
        self.dut_name = dut
        self.ssid = ssid
        self.passwd = passwd
        self.encryp = encryp
        # self.band = band
        # self.clients = clients
        self.mgr_ip = mgr_ip
        self.reset = reset
        self.time_int = time_int
        self.wait_time = wait_time
        self.supported_release = suporrted_release
        self.device_name = []
        self.lf_report = lf_report_pdf.lf_report(_path="", _results_dir_name="Interop_port_reset_test",
                                                 _output_html="port_reset_test.html",
                                                 _output_pdf="port_reset_test.pdf")
        self.report_path = self.lf_report.get_report_path()

        self.interop = base.BaseInteropWifi(manager_ip=self.host,
                                            port=self.port,
                                            ssid=self.ssid,
                                            passwd=self.passwd,
                                            encryption=self.encryp,
                                            release=self.supported_release,
                                            screen_size_prcnt = 0.4,
                                            _debug_on=False,
                                            _exit_on_error=False)
        self.base_interop_profile = base.RealDevice(manager_ip=self.host)

        self.utility = base.UtilityInteropWifi(host_ip=self.host)
        # logging.basicConfig(filename='overall_reset_test.log', filemode='w', level=logging.INFO, force=True)

    def selecting_devices_from_available(self):
        self.available_device_list = self.base_interop_profile.get_devices()
        self.user_query = self.base_interop_profile.query_user()
        logging.info("Available Devices List: {}".format(self.available_device_list))
        logging.info("Query Result: {}".format(self.user_query))
        android_list = self.base_interop_profile.android_list
        supported_dict = self.interop.supported_devices_resource_id
        self.final_selected_android_list = []
        for key in supported_dict.keys():
            if key != "":
                if any(key in item for item in android_list):
                    self.final_selected_android_list.append(supported_dict[key])
        logging.info(f"Final Android Serial Numbers List: {self.final_selected_android_list}")

        # return self.available_device_list, self.user_query

    def get_resources_data(self):
        # fetching all devices from Resource Manager tab
        response = self.json_get('/resource/all')
        resources = response['resources']
        resources_list = []
        for resource_data in resources:
            port, resource = list(resource_data.keys())[0], list(resource_data.values())[0]
            shelf, resource_id = port.split('.')
            # filtering LANforges from resources
            if resource['ct-kernel']:
                continue
            # filtering Androids from resources
            if resource['user'] != '':
                continue
            # filtering phantom resources
            if resource['phantom']:
                logging.info('The laptop on port {} is in phantom state.'.format(port))
                continue
            hw_version = resource['hw version']
            # fetching data for Windows
            if 'Win' in hw_version:
                resources_list.append({
                    'os': 'Win',
                    'shelf': shelf,
                    'resource': resource_id,
                    'sta_name': 'ad1',
                    'report_timer': 1500,
                    'interest': 8388610
                })
            # fetching data for Linux
            elif 'Lin' in hw_version:
                resources_list.append({
                    'os': 'Lin',
                    'shelf': shelf,
                    'resource': resource_id,
                    'sta_name': 'sta{}'.format(resource_id),
                    # 'sta_name': 'en0',
                    'current_flags': 2147483648,
                    'interest': 16384
                })
            # fetching data for Mac
            elif 'Apple' in hw_version:
                resources_list.append({
                    'os': 'Apple',
                    'shelf': shelf,
                    'resource': resource_id,
                    'sta_name': 'en0',
                    'current_flags': 2147483648,
                    'interest': 16384
                })
        return resources_list

    def rm_station(self, port_list=None):
        if port_list is None:
            port_list = []
        if not port_list:
            logging.info('rm_station() -> Port list is empty')
            return

        data_list = []
        for port_data in port_list:
            if 'Lin' == port_data['os']:
                shelf, resource, sta_name = port_data['shelf'], port_data['resource'], port_data['sta_name']
                data = {
                    'shelf': shelf,
                    'resource': resource,
                    'port': sta_name
                }
                data_list.append(data)

        for i in data_list:
            self.json_post("/cli-json/add_sta", i)

    # add station
    def add_station(self, port_list=None):
        if port_list is None:
            port_list = []
        if not port_list:
            logging.info('add_station() -> Port list is empty')
            return

        data_list = []

        for port_data in port_list:
            shelf = port_data['shelf']
            resource = port_data['resource']
            sta_name = port_data['sta_name']
            if self.encryp == 'open':
                self.encrypt_value = 0
                self.passwd = 'NA'
            elif self.encryp == 'wpa' or self.encryp == 'psk':
                self.encrypt_value = 16
            elif self.encryp == "wpa2" or self.encryp == 'psk2':
                self.encrypt_value = 1024
            elif self.encryp == "wpa3" or self.encryp == 'psk3':
                self.encrypt_value = 1099511627776
            data = {
                'shelf': shelf,
                'resource': resource,
                'radio': 'wiphy0',
                'sta_name': sta_name,
                'flags': self.encrypt_value,
                'ssid': self.ssid,
                'key': self.passwd,
                'mac': 'xx:xx:xx:*:*:xx'
            }
            data_list.append(data)

        for i in data_list:
            self.json_post("/cli-json/add_sta", i)

    # set port (enable DHCP)
    def set_port(self, port_list=None):
        if port_list is None:
            port_list = []
        if not port_list:
            logging.info('set_port() -> Port list is empty')
            return

        data_list = []
        for port_data in port_list:
            shelf = port_data['shelf']
            resource = port_data['resource']
            port = port_data['sta_name']
            interest = port_data['interest']

            os = port_data['os']
            if os in ['Apple', 'Lin']:
                current_flags = port_data['current_flags']
                data = {
                    'shelf': shelf,
                    'resource': resource,
                    'port': port,
                    'current_flags': current_flags,
                    'interest': interest,
                    'mac': 'xx:xx:xx:*:*:xx'
                }
            elif os == 'Win':
                report_timer = port_data['report_timer']
                data = {
                    'shelf': shelf,
                    'resource': resource,
                    'port': port,
                    'report_timer': report_timer,
                    'interest': interest
                }
            data_list.append(data)

        for i in data_list:
            self.json_post("/cli-json/set_port", i)

    def create_log_file(self, json_list, file_name="empty.json"):
        # Convert the list of JSON values to a JSON-formatted string
        json_string = json.dumps(json_list)
        new_folder = os.path.join(self.report_path, "Wifi_Messages")
        if os.path.exists(new_folder) and os.path.isdir(new_folder):
            pass
            # print(f"The folder 'Wifi_Messages' is already existed in '{self.report_path}' report folder.")
        else:
            # print(f"The folder 'Wifi_Messages' does not exist in '{self.report_path}' report folder.")
            os.makedirs(new_folder)

        file_path = f"{self.report_path}/Wifi_Messages/{file_name}"
        # print("log file saved in Wifi_Message directory path:", file_path)

        # Write the JSON-formatted string to the .json file
        with open(file_path, 'w') as file:
            file.write(json_string)

    def remove_files_with_duplicate_names(self, folder_path):
        file_names = {}
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_name = os.path.basename(file_path)
                if file_name in file_names:
                    # Removing the duplicate file
                    os.remove(file_path)
                    logging.info(f"Removed duplicate file: {file_path}")
                else:
                    # Adding the file name to the dictionary
                    file_names[file_name] = file_path

    def get_last_wifi_msg(self):
        a = self.json_get("/wifi-msgs/last/1", debug_=True)
        last = a['wifi-messages']['time-stamp']
        # logging.info(str(a))
        logging.info(f"Last WiFi Message Time Stamp: {last}")
        # logging.info(str(last))
        return last

    def get_count(self, value=None, keys_list=None, device=None, filter=None):
        count_ = []
        device = device.split(".")[2]
        for i, y in zip(keys_list, range(len(keys_list))):
            # print("Time stamp :-", i)
            wifi_msg_text = value[y][i]['text']
            if type(wifi_msg_text) == str:
                wifi_msg_text_keyword_list = value[y][i]['text'].split(" ")
                # print("#Wifi Message Text list:", wifi_msg_text_keyword_list)
                if device is None:
                    logging.info(f"Device name is {device} None device name not existed in wifi messages...")
                else:
                    # print("#Device", device)
                    if device in wifi_msg_text_keyword_list:
                        if filter in wifi_msg_text_keyword_list:
                            # logging.info(f"The filter {filter} is present in the wifi message for device '{device}'.")
                            count_.append("YES")
                    else:
                        pass
                        # print(f"The device {device} not present in wifi_msg, so Skipping",
                        #       wifi_msg_text_keyword_list)
            else:
                for item in wifi_msg_text:
                    wifi_msg_text_keyword_list = item.split(" ")
                    # print("$Wifi Message Text list:", wifi_msg_text_keyword_list)
                    if device is None:
                        pass
                        # logging.info(f"Device name is {device} None device name not existed in wifi messages... , ...")
                    else:
                        # print("$Device", device)
                        if device in wifi_msg_text_keyword_list:
                            if filter in wifi_msg_text_keyword_list:
                                # logging.info(f"The filter {filter} is present in the wifi message test list.")
                                count_.append("YES")
                        else:
                            pass
                            # print(f"The device {device} not present in wifi_msg, so Skipping",
                            #       wifi_msg_text_keyword_list)
        # print("Filter Present Count list:", count_)
        # logging.info(str(count_))
        counting = count_.count("YES")
        # print("Total Counting:", counting)
        # logging.info(str(counting))
        return counting

    def get_time_from_wifi_msgs(self, local_dict=None, phn_name=None, timee=None, file_name="dummy.json"):
        # print("Waiting for 20 sec to fetch the logs...")
        # time.sleep(20)
        a = self.json_get("/wifi-msgs/since=time/" + str(timee), debug_=True)
        values = a['wifi-messages']
        # print("Wifi msgs Response : ", values)
        logging.info(f"Counting the DISCONNECTIONS, SCANNING, ASSOC ATTEMPTS, ASSOC RECJECTIONS, CONNECTS for device {phn_name}")
        self.create_log_file(json_list=values, file_name=file_name)
        self.remove_files_with_duplicate_names(folder_path=f"{self.report_path}/Wifi_Messages/")
        # logging.info("values" + str(values))
        keys_list = []

        for i in range(len(values)):
            keys_list.append(list(values[i].keys())[0])
        # print("Key list", keys_list)

        # print("Before updating the disconnect count:", local_dict[phn_name])

        if "1.1." in phn_name:
            # disconnects
            adb_disconnect_count = self.get_count(value=values, keys_list=keys_list, device=phn_name,
                                                  filter="Terminating...")  #Todo: need to rename the method
            if adb_disconnect_count > 1 or adb_disconnect_count == 0:
                disconnection = self.utility.get_device_state(device=phn_name)
                if disconnection == 'COMPLETED':
                    logging.info("The Device %s is in connected state." % phn_name)
                    adb_disconnect_count = 0
                else:
                    logging.info("The Device %s is not in connected state." % phn_name)
                    adb_disconnect_count = 1
                logging.info(f"Disconnect Count For Android: {adb_disconnect_count}")
            # Updating the dict with disconnects for android
            logging.info("Final Disconnect count for %s: %s" % (phn_name, adb_disconnect_count))
            local_dict[phn_name]["Disconnected"] = adb_disconnect_count
            # scanning count
            adb_scan_count = self.get_count(value=values, keys_list=keys_list, device=phn_name, filter="SCAN_STARTED")
            logging.info("Final Scanning Count for %s: %s" % (phn_name, adb_scan_count))
            local_dict[str(phn_name)]["Scanning"] = adb_scan_count
            # association attempts
            adb_association_attempt = self.get_count(value=values, keys_list=keys_list, device=phn_name,
                                                     filter="ASSOCIATING")
            logging.info("Final Association Attempts Count for %s: %s" % (phn_name, adb_association_attempt))
            local_dict[str(phn_name)]["ConnectAttempt"] = adb_association_attempt
            # association rejections
            adb_association_rejection = self.get_count(value=values, keys_list=keys_list, device=phn_name,
                                                       filter="ASSOC_REJECT")
            logging.info("Final Association Rejection Count for %s: %s" % (phn_name, adb_association_rejection))
            local_dict[str(phn_name)]["Association Rejection"] = adb_association_rejection
            # connections
            adb_connected_count = self.get_count(value=values, keys_list=keys_list, device=phn_name,
                                                 filter="CTRL-EVENT-CONNECTED")
            if adb_connected_count > 1 or adb_connected_count == 0:
                ssid = self.utility.get_device_ssid(device=phn_name)
                if ssid == self.ssid:
                    logging.info("The Device %s is connected to expected ssid" % phn_name)
                    adb_connected_count = 1
                else:
                    logging.info("**** The Device is not connected to the expected ssid ****")
                    adb_connected_count = 0
                logging.info(f"Connected Count for Android: {adb_connected_count}")
            # Updating the dict with connects for android
            logging.info("Final Connected Count for %s: %s" % (phn_name, adb_connected_count))
            local_dict[str(phn_name)]["Connected"] = adb_connected_count
        else:
            if 'ad1' in phn_name:  # for windows
                win_disconnect_count = self.get_count(value=values, keys_list=keys_list, device=phn_name,
                                                      filter="Wireless security stopped")
                logging.info("Final Disconnect count for %s: %s" % (phn_name, win_disconnect_count))
                local_dict[phn_name]["Disconnected"] = win_disconnect_count
                win_scan_count = self.get_count(value=values, keys_list=keys_list, device=phn_name,
                                                filter="SCAN-STARTED")
                logging.info("Final Scanning Count for %s: %s" % (phn_name, win_scan_count))
                local_dict[str(phn_name)]["Scanning"] = win_scan_count
                win_association_attempt = self.get_count(value=values, keys_list=keys_list, device=phn_name,
                                                         filter="Trying to Associate")
                logging.info("Final Association Attempts Count for %s: %s" % (phn_name, win_association_attempt))
                local_dict[str(phn_name)]["ConnectAttempt"] = win_association_attempt
                win_association_rejection = self.get_count(value=values, keys_list=keys_list, device=phn_name,
                                                           filter="")
                logging.info("Final Association Rejection Count for %s: %s" % (phn_name, win_association_rejection))
                local_dict[str(phn_name)]["Association Rejection"] = win_association_rejection
                win_connected_count = self.get_count(value=values, keys_list=keys_list, device=phn_name,
                                                     filter="connected")
                logging.info("Final Connected Count for %s: %s" % (phn_name, win_connected_count))
                local_dict[str(phn_name)]["Connected"] = win_connected_count
            else:  # for linux, mac
                other_disconnect_count = self.get_count(value=values, keys_list=keys_list, device=phn_name,
                                                        filter="disconnected")
                logging.info("Final Disconnect count for %s: %s" % (phn_name, other_disconnect_count))
                local_dict[phn_name]["Disconnected"] = other_disconnect_count
                other_scan_count = self.get_count(value=values, keys_list=keys_list, device=phn_name,
                                                  filter="SCAN-STARTED")
                logging.info("Final Scanning Count for %s: %s" % (phn_name, other_scan_count))
                local_dict[str(phn_name)]["Scanning"] = other_scan_count
                other_association_attempt = self.get_count(value=values, keys_list=keys_list, device=phn_name,
                                                           filter="Trying to Associate")
                logging.info("Final Association Attempts Count for %s: %s" % (phn_name, other_association_attempt))
                local_dict[str(phn_name)]["ConnectAttempt"] = other_association_attempt
                other_association_rejection = self.get_count(value=values, keys_list=keys_list, device=phn_name,
                                                             filter="")
                logging.info("Final Association Rejection Count for %s: %s" % (phn_name, other_association_rejection))
                local_dict[str(phn_name)]["Association Rejection"] = other_association_rejection

                other_connected_count = self.get_count(value=values, keys_list=keys_list, device=phn_name,
                                                       filter="CTRL-EVENT-CONNECTED")
                logging.info("Final Connected Count for %s: %s" % (phn_name, other_connected_count))
                local_dict[str(phn_name)]["Connected"] = other_connected_count
        logging.info("local_dict " + str(local_dict))

        return local_dict

    # @property
    def run(self):
        try:
            # start timer
            present_time = datetime.now()
            test_start_time = present_time.strftime("%b %d %H:%M:%S")
            logging.info(f"Test Started at {present_time}")
            logging.info("Test started at " + str(present_time))
            # get the list of adb devices
            self.adb_device_list = self.interop.check_sdk_release(selected_android_devices=self.final_selected_android_list)
            self.windows_list = self.base_interop_profile.windows_list
            self.linux_list = self.base_interop_profile.linux_list
            self.mac_list = self.base_interop_profile.mac_list
            logging.info(f"Final Active Devices List (Android, Windows, Linux, Mac) Which support user specified release & not in phantom : {self.adb_device_list, self.base_interop_profile.windows_list, self.base_interop_profile.linux_list, self.base_interop_profile.mac_list}")
            self.all_selected_devices = self.adb_device_list + self.windows_list + self.linux_list + self.mac_list
            self.all_laptops = self.windows_list + self.linux_list + self.mac_list
            logging.info(f"All Selected Devices: {self.all_selected_devices}")
            logging.info(f"All Active Laptop Devices {self.all_laptops}")
            logging.info(f"The total number of available active & supported sdk release android devices are:  {len(self.adb_device_list)}")
            logging.info(f"The total number of available active windows devices are: {len(self.base_interop_profile.windows_list)}")
            logging.info(f"The total number of available active Linux devices are: {len(self.base_interop_profile.linux_list)}")
            logging.info(f"The total number of available active Mac devices are: {len(self.base_interop_profile.mac_list)}")

            # Checking and selecting the number of available clients are grater than or equal to given number of clients
            # if self.clients is not None:  #TODO: Need to remove the --client arg
            #     if len(self.adb_device_list) >= self.clients:
            #         logging.info("No of available clients is greater than or equal to provided clients")
            #         logging.info("No of available clients is greater than or equal to provided clients")
            #         logging.info("*** Now choosing no of clients provided from available list randomly ***")
            #         logging.info("now choosing no of clients provided from available list randomly")
            #         new_device = []
            #         for i, x in zip(self.adb_device_list, range(int(self.clients))):
            #             if x < self.clients:
            #                 new_device.append(i)
            #         logging.info(f"Selected Devices List: {new_device}")
            #         logging.info(new_device)
            #         self.adb_device_list = new_device
            #     else:
            #         logging.info("No of available clients is less than provided clients to be tested, Please check it.")
            #         logging.info("no of available clients is less then provided clients to be tested, Please check it.")
            #         exit(1)

            if self.adb_device_list:
                logging.info(f"Selected All Active Devices: {self.adb_device_list}")
            else:
                logging.info(f"No active adb devices list found: {self.adb_device_list}")
                # exit(1)
            # Fetching Name of the devices in a list if the active devices are available
            logging.info(f"Final selected device list, after chosen from available device list: {self.adb_device_list}")
            logging.info(f"Final selected device list, after chosen from available device list: {str(self.adb_device_list)}")

            #############
            if len(self.adb_device_list) == 0:
                logging.info("There is no active adb (Android) devices please check system")
                # exit(1)
            else:
                for i in range(len(self.adb_device_list)):
                    self.phn_name.append(self.adb_device_list[i].split(".")[2])
                logging.info(f"Separated device names from the full name: {self.phn_name}")
                logging.info("phn_name" + str(self.phn_name))

            ####################

            # check status of devices
            phantom = []
            for i in self.adb_device_list:
                phantom.append(self.interop.get_device_details(device=i, query="phantom"))
            # print("Device Phantom State List", phantom)
            # logging.info(phantom)
            state = None
            for i, j in zip(phantom, self.adb_device_list):
                if str(i) == "False":
                    logging.info("Device %s is in active state." % j)
                    logging.info("device are up")
                    state = "UP"
                else:
                    logging.info("Devices %s is in phantom state" % j)
                    logging.info("all devices are not up")
                    exit(1)
            # if state == "UP":
            if self.adb_device_list or self.windows_list or self.linux_list or self.mac_list:
                # setting / modify user name
                # self.interop.set_user_name(device=self.adb_device_list)
                for i in self.adb_device_list:
                    self.device_name.append(self.interop.get_device_details(device=i, query="user-name"))
                logging.info(f"ADB user-names for selected devices: {self.device_name}")
                logging.info("device name " + str(self.device_name))
                # print("waiting for 5 sec...")
                # time.sleep(5)

                logging.info("List out the network id's")
                for i in self.adb_device_list:
                    connected_network_info = self.utility.list_networks_info(device_name=i)
                    if connected_network_info == 'No networks':
                        logging.info("No exiting networks found for %s device" % i)
                    else:
                        # Forget already existing network base on the network id
                        logging.info("The %s device is already having %s saved networks" % (i, connected_network_info['SSID']))
                        logging.info(f"Existing and Saved Network ids : {connected_network_info['Network Id']}")
                        logging.info(f"Existing and Saved SSIDs : {connected_network_info['SSID']}")
                        logging.info(f"Existing and Saved Security Types: {connected_network_info['Security type']}")
                        logging.info("Forgetting all Saved networks for %s device..." % i)
                        logging.info("forget all previous connected networks")
                        self.utility.forget_netwrk(device=i, network_id=connected_network_info['Network Id'])
                        # print("Waiting for 2 sec")
                        # time.sleep(2)

                logging.info("Stopping the APP")
                for i in self.adb_device_list:
                    self.interop.stop(device=i)
                if self.adb_device_list:
                    logging.info("Apply SSID configuring using batch modify for android devices")
                    logging.info("apply ssid using batch modify")
                    # connecting the android devices to given ssid
                    self.interop.batch_modify_apply(device=self.adb_device_list, manager_ip=self.mgr_ip)
                # connecting the laptops to the given ssid
                resource_list = self.get_resources_data()
                logging.info(f"Resource List: {resource_list}")
                if self.linux_list:
                    self.rm_station(port_list=resource_list)
                self.add_station(port_list=resource_list)
                self.set_port(port_list=resource_list)
                logging.info("Check heath data")
                logging.info("check heath data")
                health = dict.fromkeys(self.adb_device_list)
                logging.info(f"Initial Health Data For Android Clients: {health}")
                # logging.info(str(health))
                health_for_laptops = dict.fromkeys(self.all_laptops)
                logging.info(f"Initial Health Data For Laptops Clients: {health_for_laptops}")

                # checking whether the adb device connected to given ssid or not
                for i in self.adb_device_list:
                    dev_state = self.utility.get_device_state(device=i)
                    # print("State of the Device:", dev_state)
                    # logging.info("device state" + dev_state)
                    if dev_state == "COMPLETED,":
                        logging.info("Phone %s is in connected state" % i)
                        logging.info("phone is in connected state")
                        ssid = self.utility.get_device_ssid(device=i)
                        if ssid == self.ssid:
                            logging.info("The Device %s is connected to expected ssid (%s)" % (i, ssid))
                            logging.info("device is connected to expected ssid")
                            health[i] = self.utility.get_wifi_health_monitor(device=i, ssid=self.ssid)
                        else:
                            logging.info("**** The Device is not connected to the expected ssid ****")
                    else:
                        logging.info(f"Waiting for {self.wait_time} sec & Checking again the status of the device")
                        logging.info(f"Waiting for {self.wait_time} & Checking again")
                        time.sleep(int(self.wait_time))
                        dev_state = self.utility.get_device_state(device=i)
                        logging.info(f"Device state {dev_state}")
                        logging.info("device state" + str(dev_state))
                        if dev_state == "COMPLETED,":
                            logging.info("Phone is in connected state")
                            logging.info("phone is in connected state")
                            ssid = self.utility.get_device_ssid(device=i)
                            if ssid == self.ssid:
                                logging.info("The Device %s is connected to expected ssid (%s)" % (i, ssid))
                                logging.info("device is connected to expected ssid")
                                health[i] = self.utility.get_wifi_health_monitor(device=i, ssid=self.ssid)
                        else:
                            logging.info(f"device state {dev_state}")
                            logging.info("device state" + str(dev_state))
                            health[i] = {'ConnectAttempt': '0', 'ConnectFailure': '0', 'AssocRej': '0', 'AssocTimeout': '0'}
                logging.info(f"Health Status for the Android Devices: {health}")
                logging.info("health" + str(health))

                # Querying the port mgr for checking, whether the laptop is connected to expected ssid or not
                resp = self.json_get('/ports/?fields=ssid')
                for i in resp['interfaces']:
                    key = list(i.keys())[0]
                    if key in self.all_laptops:
                        ssid = list(i.values())[0]
                        if ssid['ssid'] != '' and ssid['ssid'] == self.ssid:
                            logging.info(f"The device %s connected to expected ssid (%s) " % (key, ssid['ssid']))
                            health_for_laptops[key] = {'ConnectAttempt': None, 'ConnectFailure': None,
                                                       'AssocRej': None, 'AssocTimeout': None}
                        elif ssid['ssid'] == '':
                            logging.info("The device is not connected to any ssid.")
                        else:
                            logging.info(f"The device %s is not connected to expected ssid (%s)." % (key, ssid['ssid']))
                logging.info(f"Health Status for the Laptop Devices: {health_for_laptops}")

                # Resting Starts from here
                reset_list = []
                for i in range(self.reset):
                    reset_list.append(i)
                logging.info(f"Given No.of iterations for Reset : {len(reset_list)}")
                logging.info("reset list" + str(reset_list))
                reset_dict = dict.fromkeys(reset_list)
                for r, final in zip(range(self.reset), reset_dict):
                    logging.info("Waiting until given %s sec time intervel to finish..." % self.time_int)
                    time.sleep(int(self.time_int))  # sleeping until time interval finish
                    logging.info(f"Iteration :- {r}")
                    logging.info("Reset -" + str(r))
                    local_dict = dict.fromkeys(self.adb_device_list)
                    logging.info(f"local dict for android :{local_dict}")
                    laptop_local_dict = dict.fromkeys(self.all_laptops)
                    logging.info(f"local dict for laptops : {laptop_local_dict}")
                    local_dict.update(laptop_local_dict)

                    list_ = ["ConnectAttempt", "Disconnected", "Scanning", "Association Rejection", "Connected"]
                    sec_dict = dict.fromkeys(list_)
                    # print("sec_dict", sec_dict)

                    for i in self.adb_device_list:
                        local_dict[i] = sec_dict.copy()  # for android devices dict
                    for i in self.all_laptops:
                        laptop_local_dict[i] = sec_dict.copy()  # for laptop devices dict
                    logging.info(f"Final Outcome dict for android devices: {local_dict}")
                    logging.info(f"Final Outcome dict for laptop devices: {laptop_local_dict}")
                    logging.info(str(local_dict))

                    local_dict.update(laptop_local_dict)
                    logging.info(f"Final dict: {local_dict}")

                    # note last log time
                    timee = self.get_last_wifi_msg()  # Todo : need to rename the method

                    for i in self.adb_device_list:
                        self.interop.stop(device=i)
                    for i in self.all_laptops:  # laptop admin down
                        logging.info("**** Disable wifi for laptop %s" % i)
                        self.admin_down(port_eid=i)
                    for i in self.adb_device_list:
                        logging.info("**** Disable wifi for android %s" % i)
                        logging.info("disable wifi")
                        self.interop.enable_or_disable_wifi(device=i, wifi="disable")
                    for i in self.all_laptops:  # laptop admin up
                        logging.info("**** Enable wifi for laptop %s" % i)
                        self.admin_up(port_eid=i)
                    for i in self.adb_device_list:
                        logging.info("*** Enable wifi for laptop %s" % i)
                        logging.info("enable wifi")
                        self.interop.enable_or_disable_wifi(device=i, wifi="enable")
                    for i in self.adb_device_list:
                        logging.info("Starting APP for " % i)
                        self.interop.start(device=i)
                    logging.info("Waiting until given %s sec waiting time to finish..." % self.wait_time)
                    time.sleep(int(self.wait_time))
                    for i in self.all_selected_devices:
                        get_dicct = self.get_time_from_wifi_msgs(local_dict=local_dict, phn_name=i, timee=timee,
                                                                 file_name=f"reset_{r}_log.json")  #Todo : need to rename the method
                        reset_dict[r] = get_dicct
                logging.info(f"Final Reset Count Dictionary for all clients: {reset_dict}")
                logging.info("reset dict " + str(reset_dict))
                test_end = datetime.now()
                test_end_time = test_end.strftime("%b %d %H:%M:%S")
                logging.info(f"Test Ended at {test_end}")
                # logging.info("Test ended at " + test_end_time)
                s1 = test_start_time
                s2 = test_end_time
                FMT = '%b %d %H:%M:%S'
                test_duration = datetime.strptime(s2, FMT) - datetime.strptime(s1, FMT)
                logging.info(f"Total Test Duration: {test_duration}")
                logging.info(f"Name of the Report Folder : {self.report_path}")
                logging.info("Generating the Report...")
                return reset_dict, test_duration
        except Exception as e:
            print(e)

    def generate_overall_graph(self, reset_dict=None, figsize=(13, 5), _alignmen=None, remove_border=None,
                               bar_width=0.7, _legend_handles=None, _legend_loc="best", _legend_box=None, _legend_ncol=1,
                               _legend_fontsize=None, text_font=12, bar_text_rotation=45,
                               ):
        dict_ = ['Port Resets', 'Disconnected', 'Scans', 'Assoc Attempts', "Association Rejection", 'Connected']
        data = dict.fromkeys(dict_)
        data['Port Resets'] = self.reset

        conected_list, laptop_conected_list = [], []
        disconnected_list, laptop_disconnected_list = [], []
        scan_state, laptop_scan_state = [], []
        asso_attempt, laptop_asso_attempt = [], []
        asso_rej, laptop_asso_rej = [], []

        for j in self.adb_device_list:
            # print(j)
            local = []
            local_2, local_3, local_4, local_5, local_6 = [], [], [], [], []
            for i in reset_dict:
                # print(i)
                if j in list(reset_dict[i].keys()):
                    local.append(reset_dict[i][j]['Connected'])
                    local_2.append(reset_dict[i][j]['Disconnected'])
                    local_3.append(reset_dict[i][j]['Scanning'])
                    local_4.append(reset_dict[i][j]['ConnectAttempt'])
                    local_5.append(reset_dict[i][j]["Association Rejection"])

            conected_list.append(local)
            disconnected_list.append(local_2)
            scan_state.append(local_3)
            asso_attempt.append(local_4)
            asso_rej.append(local_5)

        # print("list ", conected_list, disconnected_list, scan_state, asso_attempt, asso_rej)
        for j in self.all_laptops:
            # print(j)
            local = []
            local_2, local_3, local_4, local_5, local_6 = [], [], [], [], []
            for i in reset_dict:
                # print(i)
                if j in list(reset_dict[i].keys()):
                    local.append(reset_dict[i][j]['Connected'])
                    local_2.append(reset_dict[i][j]['Disconnected'])
                    local_3.append(reset_dict[i][j]['Scanning'])
                    local_4.append(reset_dict[i][j]['ConnectAttempt'])
                    local_5.append(reset_dict[i][j]["Association Rejection"])

            conected_list.append(local)
            disconnected_list.append(local_2)
            scan_state.append(local_3)
            asso_attempt.append(local_4)
            asso_rej.append(local_5)
        conected_list = conected_list + laptop_conected_list
        disconnected_list = disconnected_list + laptop_disconnected_list
        scan_state = scan_state + laptop_scan_state
        asso_attempt = asso_attempt + laptop_asso_attempt
        asso_rej = asso_rej + laptop_asso_rej

        # count connects and disconnects
        scan, ass_atmpt = 0, 0
        for i, y in zip(range(len(scan_state)), range(len(asso_attempt))):
            for m in scan_state[i]:
                scan = scan + m
            for n in asso_attempt[i]:
                ass_atmpt = ass_atmpt + int(n)

        conects, disconnects = 0, 0
        for i, y in zip(range(len(conected_list)), range(len(disconnected_list))):
            for m in conected_list[i]:
                conects = conects + m
            for n in disconnected_list[i]:
                disconnects = disconnects + n

        assorej = 0
        for i in (range(len(asso_rej))):
            for m in asso_rej[i]:
                assorej = assorej + m

        # print("scan", scan)
        # print(ass_atmpt)
        # print(conects)
        # print(disconnects)
        # print(assorej)

        # print("Before count the dictionary data for overall data: ", data)
        data['Disconnected'] = disconnects
        data['Scans'] = scan
        data['Assoc Attempts'] = ass_atmpt
        data['Connected'] = conects
        data["Association Rejection"] = assorej
        # print("Final data for overall graph: ", data)

        # creating the dataset
        self.graph_image_name = "overall_graph"
        courses = list(data.keys())
        values = list(data.values())
        # print(courses)
        # print(values)

        # fig = plt.figure(figsize=(12, 4))

        fig_size, ax = plt.subplots(figsize=figsize, gridspec_kw=_alignmen)
        # to remove the borders
        if remove_border is not None:
            for border in remove_border:
                ax.spines[border].set_color(None)
                if 'left' in remove_border:  # to remove the y-axis labeling
                    yaxis_visable = False
                else:
                    yaxis_visable = True
                ax.yaxis.set_visible(yaxis_visable)

        # creating the bar plot
        colors = ('#f56122', '#00FF00', '#f5ea22', '#3D85C6', '#fa4d4d', "forestgreen")
        for bar_values, color, i in zip(values, colors, range(len(courses))):
            plt.bar(courses[i], bar_values, color=color, width=bar_width)
        for item, value in enumerate(values):
            plt.text(item, value, "{value}".format(value=value), ha='center', rotation=bar_text_rotation, fontsize=text_font)

        plt.xlabel("", fontweight='bold', fontsize=15)
        plt.ylabel("Count", fontweight='bold', fontsize=15)

        plt.xticks(color='white')
        plt.legend(
            ['Port Resets', 'Disconnects', 'Scans', 'Assoc Attempts', "Assoc Rejections", 'Connects'],
            loc=_legend_loc,
            bbox_to_anchor=_legend_box,
            ncol=_legend_ncol,
            fontsize=_legend_fontsize)
        plt.suptitle("Overall Graph for Port Reset Test", fontsize=16)
        plt.savefig("%s.png" % self.graph_image_name, dpi=96)
        return "%s.png" % self.graph_image_name

    def per_client_graph(self, data=None, name=None, figsize=(13, 5), _alignmen=None, remove_border=None, bar_width=0.5,
                         _legend_loc="best", _legend_box=None, _legend_fontsize=None, text_font=12, bar_text_rotation=45,
                         xaxis_name="", yaxis_name="", graph_title="Client %s Performance Port Reset Totals",
                         graph_title_size=16):
        self.graph_image_name = name
        courses = list(data.keys())
        values = list(data.values())

        # fig = plt.figure(figsize=(12, 4))
        fig_size, ax = plt.subplots(figsize=figsize, gridspec_kw=_alignmen)
        # to remove the borders
        if remove_border is not None:
            for border in remove_border:
                ax.spines[border].set_color(None)
                if 'left' in remove_border:  # to remove the y-axis labeling
                    yaxis_visable = False
                else:
                    yaxis_visable = True
                ax.yaxis.set_visible(yaxis_visable)

        # creating the bar plot
        colors = ('#f56122', '#00FF00', '#f5ea22', '#3D85C6', '#fa4d4d', "forestgreen")
        for bar_values, color, i in zip(values, colors, range(len(courses))):
            plt.bar(courses[i], bar_values, color=color, width=bar_width)
        for item, value in enumerate(values):
            plt.text(item, value, "{value}".format(value=value), ha='center', va='bottom', rotation=bar_text_rotation,
                     fontsize=text_font)

        plt.xlabel(xaxis_name, fontweight='bold', fontsize=15)
        plt.ylabel(yaxis_name, fontweight='bold', fontsize=15)
        plt.legend(
            ['Port Resets', 'Disconnects', 'Scans', 'Assoc Attempts', "Assoc Rejections", 'Connects'],
            loc=_legend_loc,
            bbox_to_anchor=_legend_box,
            frameon=False,
            fontsize=_legend_fontsize)
        plt.suptitle(graph_title, fontsize=graph_title_size)
        plt.savefig("%s.png" % self.graph_image_name, dpi=96)
        return "%s.png" % self.graph_image_name

    def individual_client_info(self, reset_dict, device_list):
        # per client table and graphs
        for y, z in zip(device_list, range(len(device_list))):
            reset_count_ = list(reset_dict.keys())
            reset_count = []
            for i in reset_count_:
                reset_count.append(int(i) + 1)
            asso_attempts, disconnected, scanning, connected, assorej = [], [], [], [], []

            for i in reset_dict:
                asso_attempts.append(reset_dict[i][y]["ConnectAttempt"])
                disconnected.append(reset_dict[i][y]["Disconnected"])
                scanning.append(reset_dict[i][y]["Scanning"])
                connected.append(reset_dict[i][y]["Connected"])
                assorej.append(reset_dict[i][y]["Association Rejection"])

            # graph calculation
            dict_ = ['Port Resets', 'Disconnects', 'Scans', 'Association Attempts', "Association Rejections",
                     'Connects']
            data = dict.fromkeys(dict_)
            data['Port Resets'] = self.reset

            dis = 0
            for i in disconnected:
                dis = dis + i
            data['Disconnects'] = dis

            scan = 0
            for i in scanning:
                scan = scan + i
            data['Scans'] = scan

            asso = 0
            for i in asso_attempts:
                asso = asso + i
            data['Association Attempts'] = asso

            asso_rej = 0
            for i in assorej:
                asso_rej = asso_rej + i
            data["Association Rejections"] = asso_rej

            con = 0
            for i in connected:
                con = con + i
            data['Connects'] = con

            # print(f"Final data for per client graph for {y}: {data}")

            if "1.1." in y:
                # setting the title for per client graph and table represent title.
                adb_user_name = self.interop.get_device_details(device=y, query="user-name")
                self.lf_report.set_obj_html(
                    "Port Resets for Client " + str(adb_user_name) + " (" + str(y.split(".")[2]) + ")",
                    "The below table & graph displays details of " + str(adb_user_name) + " device.")
                self.lf_report.build_objective()
            else:
                # setting the title for per client graph and table represent title.
                self.lf_report.set_obj_html(
                    "Port Resets for Client " + str(y) + ".",
                    "The below table & graph displays details of " + str(y) + " device.")
                self.lf_report.build_objective()

            # per client graph generation
            graph2 = self.per_client_graph(data=data, name="per_client_" + str(z), figsize=(13, 5),
                                           _alignmen={"left": 0.1}, remove_border=['top', 'right'],
                                           _legend_loc="upper left", _legend_fontsize=9, _legend_box=(1, 1),
                                           yaxis_name="COUNT",
                                           graph_title="Client " + str(y) + " Total Reset Performance Graph")
            # graph1 = self.generate_per_station_graph()
            self.lf_report.set_graph_image(graph2)
            self.lf_report.move_graph_image()
            self.lf_report.build_graph()

            # per client table data
            table_1 = {
                "Reset Count": reset_count,
                "Disconnected": disconnected,
                "Scanning": scanning,
                "Association attempts": asso_attempts,
                "Association Rejection": assorej,
                "Connected": connected,
            }
            test_setup = pd.DataFrame(table_1)
            self.lf_report.set_table_dataframe(test_setup)
            self.lf_report.build_table()


    def generate_report(self, reset_dict=None, test_dur=None):
        try:
            # print("reset dict", reset_dict)
            # print("Test Duration", test_dur)
            # logging.info("reset dict " + str(reset_dict))

            date = str(datetime.now()).split(",")[0].replace(" ", "-").split(".")[0]
            # self.lf_report.move_data(_file_name="overall_reset_test.log")
            # if self.clients is None:
            #     num_clients = len(self.adb_device_list)
            # else:
            #     num_clients = len(self.all_selected_devices)
            test_setup_info = {
                "DUT Name": self.dut_name,
                "LANforge ip": self.host,
                "SSID": self.ssid,
                "Total Reset Count": self.reset,
                "No of Clients": len(self.all_selected_devices),
                "Wait Time": str(self.wait_time) + " sec",
                "Time intervel between resets": str(self.time_int) + " sec",
                "Test Duration": test_dur,
            }
            self.lf_report.set_title("Port Reset Test")
            self.lf_report.set_date(date)
            self.lf_report.build_banner_cover()

            self.lf_report.set_obj_html("Objective",
                                        "The Port Reset Test simulates a scenario where multiple WiFi stations are created "
                                        "and connected to the Access Point (AP) under test. These stations are then randomly "
                                        "disconnected and reconnected at varying intervals, mimicking a busy enterprise or "
                                        "large public venue environment with frequent station arrivals and departures. "
                                        "The primary objective of this test is to thoroughly assess the core Access Point "
                                        "functions' control and management aspects under stress.<br><br>"
                                        )
            self.lf_report.build_objective()

            self.lf_report.set_table_title("Test Setup Information")
            self.lf_report.build_table_title()

            self.lf_report.test_setup_table(value="Basic Test Information", test_setup_data=test_setup_info)

            self.lf_report.set_obj_html("Overall Port Resets Graph",
                                        "The following graph presents an overview of different events during the test, "
                                        "including Port Resets, Disconnects, Scans, Association Attempts, Association Rejections and Connections. "
                                        "Each category represents the total count achieved by all clients.<br><br>"
                                        "1.  Port Resets: Total number of reset occurrences provided as test input.<br>"
                                        "2.  Disconnects: Total number of disconnects that happened for all clients during the test when WiFi was disabled.<br>"
                                        "3.  Scans: Total number of scanning states achieved by all clients during the test when the network is re-enabled.<br>"
                                        "4.  Association Attempts: Total number of association attempts (Associating state) made by all clients after WiFi is re-enabled in the full test.<br>"
                                        "4.  Association Rejections: Total number of association rejections made by all clients after WiFi is re-enabled in the full test.<br>"
                                        "6.  Connected: Total number of successful connections (Associated state) achieved by all clients during the test when WiFi is re-enabled.<br>"
                                        # " Here real clients used is "+ str(self.clients) + "and number of resets provided is " + str(self.reset)
                                        )
            self.lf_report.build_objective()
            graph1 = self.generate_overall_graph(reset_dict=reset_dict, figsize=(13, 5), _alignmen=None, bar_width=0.5,
                                                 _legend_loc="upper center", _legend_ncol=6, _legend_fontsize=10,
                                                 _legend_box=(0.5, -0.06), text_font=12)
            # graph1 = self.generate_per_station_graph()
            self.lf_report.set_graph_image(graph1)
            self.lf_report.move_graph_image()
            self.lf_report.build_graph()

            all_devices = self.adb_device_list + self.all_laptops
            self.individual_client_info(reset_dict=reset_dict, device_list=all_devices)

            self.lf_report.set_obj_html("Tested Clients Information:",
                                        "The table displays details of real clients which are involved in the test.")
            self.lf_report.build_objective()
            d_name, device_type, model, user_name, release = [], [], [], [], []

            for y in all_devices:
                # print(self.adb_device_list)
                # print("Device :", y)
                if "1.1." in y:
                    d_name.append(self.interop.get_device_details(device=y, query="name"))
                    device_type.append(self.interop.get_device_details(device=y, query="device-type"))
                    # model.append(self.interop.get_device_details(device=y, query="model"))
                    user_name.append(self.interop.get_device_details(device=y, query="user-name"))
                    # release.append(self.interop.get_device_details(device=y, query="release"))
                else:
                    d_name.append(y)
                    user_name.append(self.interop.get_laptop_devices_details(device=y, query="host_name"))
                    hw_version = self.interop.get_laptop_devices_details(device=y, query="hw_version")
                    if "Linux" in hw_version:
                        dev_type = "Linux"
                    elif "Win" in hw_version:
                        dev_type = "Windows"
                    elif "Mac" in hw_version:
                        dev_type = "Apple"
                    else:
                        dev_type = ""
                    device_type.append(dev_type)
                    # release.append("")


            s_no = []
            for i in range(len(d_name)):
                s_no.append(i + 1)

            # self.clients = len(self.adb_device_list)

            table_2 = {
                "S.No": s_no,
                "Name of the Devices": d_name,
                "Hardware Version": user_name,
                # "Model": model,
                # "SDK Release": release,
                "Device Type": device_type
            }
            test_setup = pd.DataFrame(table_2)
            self.lf_report.set_table_dataframe(test_setup)
            self.lf_report.build_table()

            self.lf_report.build_footer()
            self.lf_report.write_html()
            self.lf_report.write_pdf_with_timestamp(_page_size='A4', _orientation='Portrait')
        except Exception as e:
            print(str(e))
            logging.warning(str(e))


def main():
    parser = argparse.ArgumentParser(
        prog=__file__,
        formatter_class=argparse.RawTextHelpFormatter,
        description=
        '''
NAME: lf_interop_port_reset_test.py

PURPOSE:
         The LANforge interop port reset test enables users to use numerous real Wi-Fi stations and connect them to the 
         Access Point (AP) being tested. It then randomly disconnects and reconnects a variable number of stations at 
         different time intervals. This test helps evaluate how well the AP handles a dynamic and busy network environment 
         with devices joining and leaving the network at random times.

EXAMPLE:
        # To run port-reset test on all active devices with specified number of WIFI resets.

            ./lf_interop_port_reset_test.py --host 192.168.200.83 --mgr_ip 192.168.200.156  --dut TestDut --ssid Netgear5g
            --passwd lanforge --encryp psk2 --reset 5 --time_int 5 --wait_time 10 --release 11

        # To run port-reset test on specified number of devices with specified number of WIFI resets.

            ./lf_interop_port_reset_test.py --host 192.168.200.83 --mgr_ip 192.168.200.156  --dut TestDut --ssid Netgear5g
            --passwd lanforge --encryp psk2 --reset 2 --time_int 5 --wait_time 10 --release 11 12 --clients 1

SCRIPT_CLASSIFICATION:  Toggling, Report Generation

SCRIPT_CATEGORIES: Interop Port-Reset Test

NOTES:      
       The primary objective of this script is to automate the process of toggling WiFi on real devices with the
      InterOp Application, evaluating their performance with an access point. It achieves this by simulating multiple
      WiFi resets as specified by the user.
     
      * Currently the script will work for the android devices with version 11.
 
STATUS: Functional

VERIFIED_ON:   23-AUG-2023,
             GUI Version:  5.4.6
             Kernel Version: 5.19.17+

LICENSE:
          Free to distribute and modify. LANforge systems must be licensed.
          Copyright 2023 Candela Technologies Inc

INCLUDE_IN_README: False
''')

    parser.add_argument("--host", default='192.168.1.31',
                        help='Specify the GUI to connect to, assumes port 8080')

    parser.add_argument("--port", default='8080', help='Specify the manager port')

    parser.add_argument("--mgr_ip", default='192.168.1.31',
                        help='Specify the interop manager ip')

    parser.add_argument("--dut", default="TestDut",
                        help='Specify DUT name on which the test will be running.')

    parser.add_argument("--ssid", default="Netgear2g",
                        help='Specify ssid on which the test will be running.')

    parser.add_argument("--passwd", default="Password@123",
                        help='Specify encryption password  on which the test will be running.')

    parser.add_argument("--encryp", default="psk2",
                        help='Specify the encryption type  on which the test will be running eg :open|psk|psk2|sae|psk2jsae')

    # parser.add_argument("--band", default="5G",
    #                     help='specify the type of band you want to perform testing eg 5G|2G|Dual')

    # parser.add_argument("--clients", type=int, default=None,
    #                     help='Specify no of clients you want to perform test on.')

    parser.add_argument("--reset", type=int, default=2,
                        help='Specify the number of time you want to reset. eg: 2')

    parser.add_argument("--time_int", type=int, default=5,
                        help='Specify the time interval in seconds after which reset should happen.')

    parser.add_argument("--wait_time", type=int, default=10,
                        help='Specify the time interval or wait time in seconds after enabling WIFI.')

    parser.add_argument("--release", nargs='+', default=["12"],
                        help='Specify the SDK release version (Android Version) of real clients to be supported in test.'
                             'eg:- --release 11 12 13')
    # logging configuration:
    parser.add_argument('--log_level', default=None,
                        help='Set logging level: debug | info | warning | error | critical')

    parser.add_argument("--lf_logger_config_json",
                        help="--lf_logger_config_json <json file> , json configuration of logger")

    args = parser.parse_args()

    # set the logger level to debug
    logger_config = lf_logger_config.lf_logger_config()

    if args.log_level:
        logger_config.set_level(level=args.log_level)

    if args.lf_logger_config_json:
        # logger_config.lf_logger_config_json = "lf_logger_config.json"
        logger_config.lf_logger_config_json = args.lf_logger_config_json
        logger_config.load_lf_logger_config()

    obj = InteropPortReset(host=args.host,
                           port=args.port,
                           dut=args.dut,
                           ssid=args.ssid,
                           passwd=args.passwd,
                           encryp=args.encryp,
                           reset=args.reset,
                           # clients=args.clients,
                           time_int=args.time_int,
                           wait_time=args.wait_time,
                           suporrted_release=args.release,
                           mgr_ip=args.mgr_ip
                           )
    obj.selecting_devices_from_available()
    reset_dict, duration = obj.run()
    obj.generate_report(reset_dict=reset_dict, test_dur=duration)


if __name__ == '__main__':
    main()
