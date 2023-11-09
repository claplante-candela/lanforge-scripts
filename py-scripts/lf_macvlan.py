#!/usr/bin/env python3
"""
NAME: lf_macvlan.py

PURPOSE: create and operate macvlan ports using the lanforge_api.

EXAMPLES:
=========
    Creating two macvlan ports with static IPs:
    -------------------------------------------
$ ./lf_macvlan.py --new_macvlan --qty 2 --parent_port 1.1.eth2 --ip DHCP --state up

$ ./lf_macvlan.py --new_macvlan --qty 2 --parent_port 1.1.eth2 --ip 192.168.1.9/24,gw=192.168.1.1 --state down

$ ./lf_macvlan.py --new_macvlan --qty 2 --mac_pattern 'xx:xx:xx:*:*:xx' --ip DHCP --state up

$ ./lf_macvlan.py --set_state down --port 1.1.eth2#0 1.1.eth2#1

$ ./lf_macvlan.py --set_state up --port 1.1.eth2#0 1.1.eth2#1

$ ./lf_macvlan.py --rm_macvlan --port 1.1.eth2#0 1.1.eth2#1

$ ./lf_macvlan.py --set_ip --port 1.1.eth2#0,DHCP 1.1.eth2#1,ip=192.168.1.9/24,gw=192.168.1.1

$ ./lf_macvlan.py --list --parent_port 1.1.eth2

STATUS: in development

NOTES:
======


LICENSE:
          Free to distribute and modify. LANforge systems must be licensed.
          Copyright 2023 Candela Technologies Inc

INCLUDE_IN_README: True

TO DO NOTES:

"""
import ipaddress
import logging
import os
import sys
import time

if sys.version_info[0] != 3:
    print("This script requires Python3")
    exit()

import importlib
import argparse
import pprint

# import ipaddress

sys.path.insert(1, "../")
# lanforge_client = importlib.import_module("lanforge_client")
lanforge_api = importlib.import_module("lanforge_client.lanforge_api")
from lanforge_client.lanforge_api import LFSession
from lanforge_client.lanforge_api import LFJsonCommand
from lanforge_client.lanforge_api import LFJsonQuery

NA: str = "NA"
DHCP: str = "DHCP"
NO_GATEWAY = "0.0.0.0"
MAC_VLAN = "MAC-VLAN"
logger = logging.getLogger(__name__)


class macvlan:
    ADD_MVLAN_FLAGS: dict = {
        "up": NA,
        "down": 1
    }
    DEFAULT_MAC_PATTERN: str = "xx:xx:xx:*:*:xx"
    PORT_TYPE: str = 'port type'
    PHANTOM: str = 'phantom'

    def __init__(self,
                 session: LFSession = None,
                 parent_port: str = None,
                 num_ports: int = None,
                 mac_pattern: str = None,
                 ip_addr: str = None,
                 debug: bool = False,
                 state: str = None):
        self.session: LFSession = session
        if not session.logger:
            session.logger = logging
        self.lfcommand: LFJsonCommand = session.get_command()
        self.lfquery: LFJsonQuery = session.get_query()

        self.SetPortCurrentFlags: LFJsonCommand.SetPortCurrentFlags = self.lfcommand.SetPortCurrentFlags
        self.SetPortInterest: LFJsonCommand.SetPortInterest = self.lfcommand.SetPortInterest

        self.parent_port: str = parent_port
        self.num_ports: int = num_ports
        self.mac_pattern: str = mac_pattern
        self.ip_addr: str = ip_addr
        self.state: str = state
        self.errors_warnings: list = []
        self.response_json_list: list = []
        self.debug: bool = debug
        self.port_columns: list = ["port",
                                   "parent+dev",
                                   "alias",
                                   "phantom",
                                   "down",
                                   "ip",
                                   "port+type"]

    def remove_vlans(self,
                     vlan_list: list = None,
                     force: bool = False) -> None:
        """

        :param vlan_list: list of string eids that will be filtered to see if
                            they are type macvlan
        :param force: remove ports that are listed, do not restrict to macvlans
        :return: nothing
        """
        existing_ports: list = self.list_ports()
        included_ports: list = []
        for item in existing_ports:
            eid: str = list(item.keys())[0]
            self.session.logger
            if eid not in vlan_list:
                continue

            pprint.pprint(item)
            port_dict: dict = item[eid]
            port_type: str = port_dict[self.PORT_TYPE]  # item.values[eid]['port_type']
            if port_type == MAC_VLAN:
                logger.warning(f"adding {eid}")
                included_ports.append(eid)
                continue
            if force:
                logger.warning(f"will remove non-macvlan port {eid}")
                included_ports.append(eid)
                continue
            if (port_dict[self.PHANTOM] == True) or (port_dict[self.PHANTOM] == "True"):
                logger.warning(f"will remove phantom port {eid}")
                included_ports.append(eid)
                continue
            logger.warning(f"ignoring non-macvlan port {eid}")
        for item in included_ports:
            hunks: list = item.split('.')
            logger.warning(f"removing {item}")
            self.lfcommand.post_rm_vlan(port=hunks[2],
                                        resource=hunks[1],
                                        shelf=hunks[0],
                                        response_json_list=self.response_json_list,
                                        errors_warnings=self.errors_warnings,
                                        debug=self.debug,
                                        suppress_related_commands=True)
            if len(self.errors_warnings):
                for err in self.errors_warnings:
                    logger.warning(err)
                self.errors_warnings.clear()

        # should be all done by here, but might want to wait

    def new_macvlan(self,
                    parent_port: str = None,
                    qty: int = None,
                    mac_pattern: str = None,
                    debug: bool = False):
        debug = self.debug or debug
        print(f"would create new macvlan debug:{debug}")
        if not parent_port:
            parent_port = self.parent_port
        if not qty:
            qty = int(self.num_ports)
        if not mac_pattern:
            mac_pattern = self.mac_pattern
        if not mac_pattern:
            mac_pattern = self.DEFAULT_MAC_PATTERN
        state = self.state
        if not state:
            state = "up"
        if not qty:
            raise ValueError("new_macvlan: no quantity provided")
        if not parent_port:
            raise ValueError("new_macvlan: no parent port provided")

        port_hunks: list = parent_port.split(".")
        if len(port_hunks) < 3:
            raise ValueError(f"new_macvlan: parent_port has insufficient decimals:{parent_port}")

        print("Finding existing macvlans on parent port...")
        existing_mvlans: list = self.list_ports(parent_port=parent_port)
        maximum_vlan_num: int = 0
        if existing_mvlans is None:
            logging.warning("* * existing vlans is None")
        elif len(existing_mvlans) < 1:
            logging.warning("* * existing vlans is empty")
        else:
            logging.debug(["matching-vlans:", pprint.pformat(existing_mvlans)])
            substr_start: int = len(parent_port) + 1
            for item in existing_mvlans:
                item_key = list(item.keys())[0]
                # print(f"ITEM KEY:{item_key}")
                if item_key == parent_port:
                    continue
                trailing_num: int = int(item_key[substr_start:])
                if trailing_num > maximum_vlan_num:
                    maximum_vlan_num = trailing_num
            print(f"MAX VLAN NUM: {maximum_vlan_num}")

        port_cmd_flags: str = NA
        port_current_flags: int = 0
        port_interest_flags: int = self.SetPortInterest.dhcp \
                                   | self.SetPortInterest.dhcpv6 \
                                   | self.SetPortInterest.ifdown
        if state == "down":
            port_current_flags |= self.SetPortCurrentFlags.if_down
        portnum: int = 0  # use as temp counter
        first_ip_str: str = None
        netmask_str: str = NA
        cidr_str: str = "/24"
        ip_addresses: list = []
        gateway: str = NA
        ip: ipaddress.IPv4Address = None
        prev_ip: ipaddress.IPv4Network = None
        comma_pos: int = self.ip_addr.find(',')
        slash_pos: int = self.ip_addr.find('/')

        if self.ip_addr == DHCP:
            port_current_flags |= self.SetPortCurrentFlags.use_dhcp
            portnum = int(maximum_vlan_num)
            while portnum < (int(maximum_vlan_num) + int(qty)):
                ip_addresses.insert(portnum, NA)
                portnum +=1
        else:
            port_interest_flags |= self.SetPortInterest.ip_Mask \
                                   | self.SetPortInterest.ip_gateway \
                                   | self.SetPortInterest.ip_address
            if comma_pos < 0:
                logger.warning(f"Using NO_GATEWAY for {self.ip_addr}")
                first_ip_str = self.ip_addr
            elif comma_pos < 8:
                raise ValueError(
                    f"Unusual network address: {self.ip_addr}, expecting something like: 10.0.0.2/24,10.0.0.1")
            elif comma_pos > 8:
                # print(f" !! !! comma:{comma_pos} slash:{slash_pos}")
                if slash_pos > 0:
                    gateway = self.ip_addr[comma_pos + 1:]
                    cidr_str = self.ip_addr[slash_pos:comma_pos]
                    first_ip_str = self.ip_addr[0:slash_pos]
                    print(f"* * gateway:{gateway} cidr:{cidr_str} first_ip_str: {first_ip_str}")
                else:
                    gateway = self.ip_addr[comma_pos + 1:]
                    # print(f"+ + gateway:{gateway} cidr:{cidr_str}")
                    if (slash_pos > 0) and (slash_pos < comma_pos):
                        first_ip_str = self.ip_addr[0:slash_pos]
                    else:
                        first_ip_str = self.ip_addr[0:comma_pos]
            # print(f" = => first_ip_str{first_ip_str}")
            ip = ipaddress.IPv4Address(first_ip_str)
            prev_ip = ipaddress.IPv4Address(str(ip))
            netmask_str = ipaddress.IPv4Network(f"{first_ip_str}{cidr_str}", strict=False).with_netmask
            netmask_str = netmask_str[netmask_str.find('/')+1:]
            portnum = maximum_vlan_num
            while portnum < (maximum_vlan_num + int(qty)):
                # print(f" ** ** portnum:{portnum} maxv:{maximum_vlan_num} q:{qty}")
                ip_addresses.insert(portnum, str(ip))
                prev_ip = ip
                ip = ipaddress.IPv4Address(prev_ip + 1)
                portnum += 1
        # pprint.pprint(["cidr", cidr_str, "netmask_str", netmask_str, "gateway", gateway, "ip_addresses", ip_addresses])

        if port_current_flags > 0:
            port_interest_flags |= self.SetPortInterest.current_flags

        ip_str = NA
        if self.ip_addr == DHCP:
            ip_str = NA
            ip_addresses.append(ip_str)

        parent_port_hunks: list = parent_port.split(".")

        for portnum in range(maximum_vlan_num, maximum_vlan_num + int(qty)):
            self.lfcommand.post_add_mvlan(flags=self.ADD_MVLAN_FLAGS[state],
                                          # ignore index, kernel assigns this usually
                                          mac=mac_pattern,
                                          port=port_hunks[2],
                                          resource=port_hunks[1],
                                          shelf=port_hunks[0],
                                          debug=debug,
                                          errors_warnings=self.errors_warnings,
                                          suppress_related_commands=True)

            self.lfcommand.post_set_port(shelf=1,
                                         resource=port_hunks[1],
                                         port=f"{parent_port_hunks[2]}#{portnum}",
                                         ip_addr=ip_addresses[portnum],
                                         netmask=netmask_str,
                                         gateway=gateway,
                                         cmd_flags=NA,
                                         current_flags=str(port_current_flags),
                                         current_flags_msk=str(port_current_flags),
                                         mac=mac_pattern,
                                         interest=int(port_interest_flags),
                                         dns_servers=NA,
                                         debug=True,
                                         suppress_related_commands=True)
            raise ValueError("UNFINISHED")

    def list_ports(self,
                   eid_list: list = None,
                   parent_port: str = None):
        if not eid_list:
            eid_list = ["list"]
        if not parent_port:
            if self.parent_port:
                parent_port = self.parent_port
        if not parent_port:
            response = self.lfquery.get_port(eid_list=eid_list,
                                             requested_col_names=self.port_columns,
                                             errors_warnings=self.errors_warnings,
                                             debug=self.debug)
        else:
            hunks = parent_port.split('.')
            resource = f"{hunks[0]}.{hunks[1]}"
            resource_list = f"{hunks[0]}.{hunks[1]}.list"
            response: list = self.lfquery.get_port(eid_list=[resource_list],
                                                   requested_col_names=self.port_columns,
                                                   errors_warnings=self.errors_warnings,
                                                   debug=self.debug)
            filtered_response: list = []
            for entry in response:
                # print(f"KEYS:{list(entry.keys())[0]}")
                eid: str = list(entry.keys())[0]
                if eid.startswith(parent_port):
                    # pprint.pprint(entry)
                    filtered_response.append(entry)
            response = filtered_response
        if not response:
            logging.error("no response")
        return response


# ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- #
#   M A I N
# ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ---- #
def main():
    help_summary = """Utility script for creating MAC vlans and setting them up and down.
    Can create multiple mac vlans.
    """
    parser = argparse.ArgumentParser(
        prog=__file__,
        formatter_class=argparse.RawTextHelpFormatter,
        description='tests creating raw command')
    parser.add_argument("--help_summary", action='store_true',
                        help="print out help summary")
    parser.add_argument("--host", "--mgr",
                        default='127.0.0.1',
                        help='specify the GUI to connect to, assumes port 8080')
    parser.add_argument("--parent_port",
                        help='parent port to base macvlans from')
    parser.add_argument("--new_macvlan",
                        action='store_true',
                        help="create a new macvlan on a parent port")
    parser.add_argument("--mac_pattern",
                        help="MAC address pattern, such as xx:xx:xx:*:*:xx where xx = keep parent, * = random")
    parser.add_argument("--qty",
                        help="number of macvlans to create")
    parser.add_argument("--ip",
                        help="specify the first IP address with 'ip=<CIDR>,gw=<gateway>' or 'DHCP'")
    parser.add_argument("--state",
                        help="specify if the port is admin 'up' or admin 'down'")
    parser.add_argument("--set_state",
                        action='store_true',
                        help="Do not create a macvlan but change the state. Specify if the port is admin 'up' or admin 'down'")
    parser.add_argument("--port",
                        nargs="+",
                        # action='append', NO DON'T
                        help="specify the EID of the port to change or remove (--port 1.1.eth2#1 --port 1.1.eth2#0)")
    parser.add_argument("--rm_macvlan", "--rm", "--del", "--remove",
                        action='store_true',
                        help="remove macvlans using --port <EID> arguments")
    parser.add_argument("--set_ip",
                        action='store_true',
                        help="Just set IP for a port with --port <EID>,DHCP or --port <EID>,ip=<CIDR>,gw=<IP> ")
    parser.add_argument("--list",
                        action='store_true',
                        help="prints a list of ports, or child ports from --parent_port <EID>")
    parser.add_argument("--debug",
                        action='store_true',
                        help="turn on debug output")
    parser.add_argument("--log_level",
                        help="specify logging level")
    args = parser.parse_args()
    if args.help_summary:
        print(help_summary)
        exit(0)

    if not (args.new_macvlan or args.set_state or args.rm_macvlan or args.set_ip or args.list):
        print("Please choose one action: --list, --new_macvlan, --set_state, --rm_macvlan, or --set_ip")
        exit(1)

    lfsession: LFSession = LFSession(lfclient_url=f"http://{args.host}:8080",
                                     debug=args.debug,
                                     stream_warnings=True,
                                     exit_on_error=True)

    if args.log_level:
        logger.setLevel(args.log_level)

    my_macvlan: macvlan = macvlan(session=lfsession,
                                  parent_port=args.parent_port,
                                  num_ports=args.qty,
                                  mac_pattern=args.mac_pattern,
                                  ip_addr=args.ip,
                                  state=args.state)
    if args.new_macvlan:
        logger.info("creating new macvlan")
        my_macvlan.new_macvlan(parent_port=args.parent_port,
                               qty=args.qty,
                               mac_pattern=args.mac_pattern,
                               debug=args.debug)
    elif args.set_state:
        logger.info("setting state on ports")

    elif args.rm_macvlan:
        logger.info("removing macvlan or port")
        if not args.port:
            logger.error("* * no mac-vlans specified for removal, use --list to see ports")
            exit(1)

        extended_list: list = []
        for item in args.port:
            pprint.pprint(["item", item])
            s_item: str = str(item)
            if s_item.find(',') >= 0:
                extended_list.extend(s_item.split(','))
            else:
                extended_list.append(s_item)
        pprint.pprint(["extended_list", extended_list])
        my_macvlan.remove_vlans(vlan_list=extended_list, force=False)
    elif args.set_ip:
        logger.info("setting IP on port")

    elif args.list:
        logger.info("List of ports:")
        list_of_ports: list = []
        if args.parent_port:
            list_of_ports = my_macvlan.list_ports(parent_port=args.parent_port)
        else:
            list_of_ports = my_macvlan.list_ports()
        pprint.pprint(list_of_ports)
    else:
        logger.error("* * Unable to determine action, bye.")
        exit(1)


if __name__ == "__main__":
    main()
