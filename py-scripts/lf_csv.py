#!/usr/bin/env python3
'''
NAME: lf_csv.py

PURPOSE:
Common Library for generating csv for LANforge output
KPI - Key Performance Indicators

SETUP:
/lanforge/html-reports directory needs to be present or output generated in local file

EXAMPLE:
see: /py-scripts/lf_report_test.py for example

COPYRIGHT:
    Copyright 2021 Candela Technologies Inc
    License: Free to distribute and modify. LANforge systems must be licensed.

INCLUDE_IN_README
'''

import pandas as pd
from pandas import *        # noqa: F403
from csv import reader
import csv
import argparse


class lf_csv:
    def __init__(self,
                 _columns=['Stations', 'bk', 'be', 'vi', 'vo'],
                 _rows=[['sta0001', 'sta0002', 'sta0003', 'sta0004', 'sta0005'],
                        [1, 2, 3, 4, 5],
                        [11, 22, 33, 44, 55],
                        [6, 7, 8, 9, 10],
                        [66, 77, 88, 99, 100]],
                 _filename='test.csv'):
        self.rows = _rows
        self.columns = _columns
        self.filename = _filename

    def generate_csv(self):
        df = {}
        if self.rows != []:
            for i in range(len(self.columns)):
                df[self.columns[i]] = self.rows[i]
        else:
            for i in range(len(self.columns)):
                df[self.columns[i]] = []
        csv_df = pd.DataFrame(df)
        print(csv_df)
        csv_df.to_csv(self.filename, index=False, encoding='utf-8', na_rep='NA', float_format='%.2f')

    def read_csv(self, file_name, column=None):
        data = read_csv(str(file_name))        # noqa: F405
        value = data[str(column)].tolist()
        print("value of column", value)
        return value

    def read_csv_row(self, file_name):
        lst = []
        with open(str(file_name), 'r') as read_obj:
            # pass the file object to reader() to get the reader object
            csv_reader = reader(read_obj)
            # Iterate over each row in the csv using reader object
            for row in csv_reader:
                # row variable is a list that represents a row in csv
                print(row)
                lst.append(row)
                print("list", lst)
        return lst

    def open_csv_append(self, fields, name):
        # fields = ['first', 'second', 'third']
        with open(str(name), 'a') as f:
            writer = csv.writer(f)
            writer.writerow(fields)


def main():
    help_summary = '''\
     This script is designed to generate the csv file with the test report data of lanforge tests, any file which runs
     the tests can import this file to generate the csv file with the test report data. The file name is test.csv and
     the file will the stored in the same directory of this file (pyscripts) while creating the object of this lf_csv
     file, the data can be passed while creating the object and the report can be generated by calling the method
     generate_csv()
     Note this is not the kpi csv format.  Use lf_kpi_csv.py for the kpi csv format.
    '''
    parser = argparse.ArgumentParser(
        prog='lf_mixed_traffic.py',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''\
                The lf_csv is used to generate csv report of the lanforge test results
                ''',
        description='''
NAME: lf_csv.py

PURPOSE:
        The purpose of this test is to create a csv file for the lanforge output of a test
        This file should should be imported by the file running the test and data can be passed while creating the object

EXAMPLE:
        # CLI To run the lf_csv to generate the csv file
        python3 lf_csv.py
    ''')
    parser.add_argument('--help_summary', help='Show summary of what this script does', default=None,
                        action="store_true")

    args = parser.parse_args()

    # help summary
    if args.help_summary:
        print(help_summary)
        exit(0)
    test = lf_csv()
    test.generate_csv()


if __name__ == "__main__":
    main()
