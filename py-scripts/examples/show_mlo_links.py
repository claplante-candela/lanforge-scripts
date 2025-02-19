#!/usr/bin/env python3
'''
NAME:      show_mlo_links.py

PURPOSE:   This script serves as an example for automating LANforge using the REST API 
           and as a minimal example to show general mlo links information. 

EXAMPLE:   # 

LICENSE:    Free to distribute and modify. LANforge systems must be licensed.
            Copyright 2024 Candela Technologies Inc.
'''

import argparse 
import logging
import requests
import pandas
import sys
from http import HTTPStatus

if sys.version_info[0] != 3:
    print("The script requires python3")

logger = logging.getLogger("mlo_links")
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s (%(name)s): %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

def show_links(mgr: str = "localhost", mgr_port: int = 8080) -> pandas.DataFrame:
   
    base_url = f"http://{mgr}:{mgr_port}"
    endpoint = "/mlo"
    url = base_url + endpoint

    logger.info(f"Querying LANforge mlo links information using URL \'{url}\'")
    response = requests.get(url=url)
    if response.status_code != HTTPStatus.OK:
        logger.error(f"Failed to query mlo links information at URL \'{url}\' with status code {response.status_code}")
        exit(1)

    json_data = response.json()

    tmp_mlo_data = {
        'MLO': [],
        'Port': [],
        'Alias': [],
        'Down': [],
        'Phantom': []
    }

    for key in json_data:

        if 'wiphy' not in key: 
            continue

        logger.debug(f"Found data for radio \'{key}\'")
        link_data = json_data[key]

        driver = link_data['driver'].split('Driver:', maxsplit=1)[1].split(maxsplit=1)[0]
        tmp_mlo_data['MLO'].append(mlo_data['mlo'])
        tmp_mlo_data['Port'].append(mlo_data['port'])
        tmp_mlo_data['Alias'].append(mlo_data['alias'])
        tmp_mlo_data['Down'].append(mlo_data['down'])
        tmp_mlo_data['Phantom'].append(mlo_data['phantom'])

        return pandas.DataFrame(tmp_mlo_data)


def parse_args():
    parser = argparse.ArgumentParser(
        prog="show_mlo_links.py",
        formatter_class=argparse.RawTextHelpFormatter,
        description='''
        Summary: 
            This script serves as an example for automating LANforge using the REST API 
            and as a minimal example to show general mlo links information. 

        Example:
            ./show_mlo_links.py --mgr 192.168.101.189 --mgr_port 8080
        '''
    )

    parser.add_argument("--mgr",
                        help="Manager LANforge GUI IP address",
                        type=str,
                        default='localhost')
    parser.add_argument("--mgr_port",
                        help="Manager LANforge GUI port (almost always 8080)",
                        type=int,
                        default=8080)
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    # The '**vars()' unpacks the 'args' into arguments to function.
    mlo_data = show_links(**vars(args))
    print(mlo_data)
