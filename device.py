import requests
import json
from datetime import datetime
import time


class Device:
    def __init__(self, name, mac_address, begin_timestamp, measurements):
        self.name = name
        self.mac_address = mac_address
        self.begin_timestamp = begin_timestamp
        self.measurements = measurements
        self.values = {}

    def get_values(self, auth_code, nullify_begin_timestamp = False):
        if nullify_begin_timestamp:
            self.begin_timestamp = 'null'

        for measure in self.measurements:
            request_url = 'https://api.netatmo.com/api/getmeasure?'
            request_url += 'device_id={}'.format(self.mac_address)
            request_url += '&scale=30min'
            request_url += '&type={}'.format(measure)
            request_url += '&date_begin={}'.format(self.begin_timestamp)
            request_url += '&optimize=false&real_time=true'

            res = requests.get(
                request_url,
                headers={
                    'accept': 'application/json',
                    'Authorization': 'Bearer {auth_code}'.format(auth_code=auth_code)
                }
            )

            if res.status_code == 200:
                content = json.loads(res.content)
                for timestamp in content['body']:
                    key_timestamp = int(timestamp)
                    if key_timestamp not in self.values:
                        self.values[key_timestamp] = {
                            measure: 0
                            for measure
                            in self.measurements
                        }
                    self.values[key_timestamp][measure] = content['body'][timestamp][0]

            if res.status_code != 200:
                print('ERROR: unable to retrieve data for device {name}, status code {code}'.format(
                    name=self.name,
                    code=res.status_code
                ))
                return False

        if not self.values:
            print('ERROR: unable to retrive data for device {}'.format(self.name))
            return False

        result_string = 'INFO: data for device {} retrieved'.format(self.name)
        if nullify_begin_timestamp:
            result_string += ' without specifing a begin timestamp'
        print(result_string)
        return True

    def export_values(self):
        min_datetime = datetime.fromtimestamp(min(self.values.keys()))

        max_timestamp = max(self.values.keys())
        max_datetime = datetime.fromtimestamp(max_timestamp)

        output_filename = 'output'
        output_filename += '_{}'.format(self.name)
        output_filename += '_{y_start}{m_start:02d}{d_start:02d}{hh_start:02d}{mm_start:02d}{ss_start:02d}'.format(
            y_start=min_datetime.year,
            m_start=min_datetime.month,
            d_start=min_datetime.day,
            hh_start=min_datetime.hour,
            mm_start=min_datetime.minute,
            ss_start=min_datetime.second,
        )
        output_filename += '_{y_end}{m_end:02d}{d_end:02d}{hh_end:02d}{mm_end:02d}{ss_end:02d}.csv'.format(
            y_end=max_datetime.year,
            m_end=max_datetime.month,
            d_end=max_datetime.day,
            hh_end=max_datetime.hour,
            mm_end=max_datetime.minute,
            ss_end=max_datetime.second
        )

        output_file = open(output_filename, 'w')
        for key, values in self.values.items():
            file_string = time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime(key)) + ','
            for measure in self.measurements:
                file_string += str(values[measure]) + ','

            output_file.write(file_string[:-1] + '\n')

    def update_json(self, config):
        if self.values:
            max_timestamp = max(self.values.keys())
            config['devices'][self.name]['begin_timestamp'] = max_timestamp

    def get_values_and_export(self, auth_code, nullify_begin_timestamp = False):
        if self.get_values(auth_code, nullify_begin_timestamp):
            self.export_values()
            return True

        return False
