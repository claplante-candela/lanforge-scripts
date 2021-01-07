#!/usr/bin/env python3

"""
    Script for creating a variable number of bridges.
"""

import sys
import os
import argparse

if sys.version_info[0] != 3:
    print("This script requires Python 3")
    exit(1)

if 'py-json' not in sys.path:
    sys.path.append(os.path.join(os.path.abspath('..'), 'py-json'))
import LANforge
from LANforge.lfcli_base import LFCliBase
from LANforge import LFUtils
import realm
import time
import pprint


class CreateBridge(LFCliBase):
    def __init__(self,sta_list,resource,target_device,radio,
                 _ssid=None,
                 _security=None,
                 _password=None,
                 _host=None,
                 _port=None,
                 _bridge_list=None,
                 _number_template="00000",
                 _resource=1,
                 _proxy_str=None,
                 _debug_on=False,
                 _exit_on_error=False,
                 _exit_on_fail=False):
        super().__init__(_host,
                         _port,
                         _proxy_str=_proxy_str,
                         _local_realm=realm.Realm(lfclient_host=_host,
                                                  lfclient_port=_port,
                                                  halt_on_error_=_exit_on_error,
                                                  _exit_on_error=_exit_on_error,
                                                  _exit_on_fail=_exit_on_fail,
                                                  _proxy_str=_proxy_str,
                                                  debug_=_debug_on),
                         _debug=_debug_on,
                         _halt_on_error=_exit_on_error,
                         _exit_on_fail=_exit_on_fail)
        self.host = _host
        self.port = _port
        self.ssid = _ssid
        self.security = _security
        self.password = _password
        self.bridge_list = _bridge_list
        self.radio = radio
        self.timeout = 120
        self.number_template = _number_template
        self.debug = _debug_on
        self.sta_list = sta_list
        self.resource = resource
        self.target_device = target_device
        if self.debug:
            print("----- bridge List ----- ----- ----- ----- ----- ----- \n")
            pprint.pprint(self.sta_list)
            print("---- ~bridge List ----- ----- ----- ----- ----- ----- \n")


    def build(self):
        # Build bridges

        data = {
            "shelf": 1,
            "resource": self.resource,
            "port": "br0",
            "network_devs": "eth1,%s" % self.target_device
        }
        self.local_realm.json_post("cli-json/add_br", data)

        bridge_set_port = {
            "shelf": 1,
            "resource": self.resource,
            "port": "br0",
            "current_flags": 0x80000000,
            "interest": 0x4000  # (0x2 + 0x4000 + 0x800000)  # current, dhcp, down
        }
        self.local_realm.json_post("cli-json/set_port", bridge_set_port)




def main():
    parser = LFCliBase.create_basic_argparse(
        prog='create_bridge.py',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''\
         Create bridges
            ''',

        description='''\
        create_bridge.py
--------------------
Command example:
./create_bridge.py
    --upstream_port eth1
    --radio wiphy0
    --num_bridges 3
    --target_device wlan0
    --security open
    --ssid netgear
    --passwd BLANK
    --debug
            ''')
    required = parser.add_argument_group('required arguments')
    required.add_argument('--target_device', help='Where the bridges should be connecting', required=True)
    #required.add_argument('--security', help='WiFi Security protocol: < open | wep | wpa | wpa2 | wpa3 >', required=True)

    optional = parser.add_argument_group('optional arguments')
    optional.add_argument('--num_bridges', help='Number of bridges to Create', required=False)
    args = parser.parse_args()
    #if args.debug:
    #    pprint.pprint(args)
    #    time.sleep(5)
    if (args.radio is None):
       raise ValueError("--radio required")

    num_bridge = 2
    if (args.num_bridges is not None) and (int(args.num_bridges) > 0):
        num_bridges_converted = int(args.num_bridges)
        num_bridge = num_bridges_converted

    bridge_list = LFUtils.port_name_series(prefix="bridge",
                           start_id=0,
                           end_id=num_bridge-1,
                           padding_number=10000,
                           radio=args.radio)

    create_bridge = CreateBridge(_host=args.mgr,
                       _port=args.mgr_port,
                       _ssid=args.ssid,
                       _password=args.passwd,
                       _security=args.security,
                       _bridge_list=bridge_list,
                       radio=args.radio,
                       _proxy_str=args.proxy,
                       _debug_on=args.debug,
                       sta_list=bridge_list,
                       resource=1,
                       target_device=args.target_device)

    create_bridge.build()

if __name__ == "__main__":
    main()
