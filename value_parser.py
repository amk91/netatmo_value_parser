import requests
import json
import time
import sys
from datetime import datetime
from concurrent import futures

from device import Device


def get_auth_code():
    parameters = {
        'grant_type': 'password',
        'client_id': '',
        'client_secret': '',
        'username': '',
        'password': '',
        'scope': 'read_station'
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
    }

    res = requests.post(
        'https://api.netatmo.com/oauth2/token',
        data=parameters,
        headers=headers
    )
    content = json.loads(res.content)
    if res.status_code == 200:
        return content['access_token']
    else:
        print('ERROR: unable to retrieve access token\n')
        print('\t{}: {}'.format(
            content['error'], content['error_description']
        ))
        quit()


def dispatch_options(option, config):
    if option == 'help':
        pass
    elif option == 'add_device':
        print('ADDING NEW DEVICE')
        name = input('|| Enter new device name: ')
        if name in config['devices']:
            print('ERROR: device {} already exists in configuration file'.format(name))
            quit()
        else:
            mac_address = input('|| Enter new device mac address: ')

            begin_timestamp = input('|| Enter new device begin timestamp (blank for current timestamp): ')
            if not begin_timestamp:
                begin_timestamp = str(int(time.time()))

            measurements = [
                measure.strip()
                for measure
                in input('|| Enter new device measurements separated by commas (blank for default, i.e. temperature, co2, humidity, pressure, noise): ')
            ]
            if not measurements:
                measurements = ['temperature', 'co2',
                                'humidity', 'pressure', 'noise']

        config['devices'][name] = {
            'mac_address': mac_address,
            'begin_timestamp': begin_timestamp,
            'measurements': measurements
        }
    elif option == 'remove_device':
        print('REMOVING EXISTING DEVICE')
        name = input('|| Enter device name to delete: ')
        if name in config['devices']:
            del config['devices'][name]
        else:
            print('ERROR: device {} does not exist in the configuration file'.format(name))
            quit()
    elif option == 'update_device':
        print('UPDATING EXISTING DEVICE')
        name = input('|| Enter device name to update (blank input will not update the specified field): ')
        if name not in config['devices']:
            print('ERROR: device {} does not exist in the configuration file'.format(name))
            quit()
        else:
            new_name = input('|| Enter new name: ')
            if new_name:
                config['devices'][new_name] = config['devices'].pop(name)
                name = new_name

            new_mac_address = input('|| Enter new mac address: ')
            if new_mac_address:
                config['devices'][name]['mac_address'] = new_mac_address

            new_begin_timestamp = input('|| Enter new begin timestamp: ')
            if new_begin_timestamp:
                config['devices'][name]['begin_timestamp'] = new_begin_timestamp

            new_measurements = [
                measure.strip()
                for measure
                in input('|| Enter new measurements separated by commas: ')
            ]
            if new_measurements:
                config['devices'][name]['measurements'] = measurements

    with open('config.json', 'w') as config_file:
        json.dump(config, config_file, indent=4)
    quit()


if __name__ == '__main__':
    config = {}
    try:
        with open('config.json', 'r') as config_file:
            config = json.loads(config_file.read())
            if 'devices' not in config:
                print('ERROR: devices list missing from configuration file')
                quit()
    except FileNotFoundError:
        print('ERROR: Config file not found. Please provide a config.json file to read configuration data from')
        quit()

    auth_code = get_auth_code()
    if len(sys.argv) > 1:
        if sys.argv[1].startswith('--'):
            dispatch_options(sys.argv[1][2:], config)

    devices = []
    for device_name in config['devices']:
        devices.append(
            Device(
                device_name,
                config['devices'][device_name]['mac_address'],
                config['devices'][device_name]['begin_timestamp'],
                config['devices'][device_name]['measurements']
            )
        )

    with futures.ThreadPoolExecutor() as executor:
        futures_results = {}
        for device in devices:
            futures_results[device.name] = executor.submit(device.get_values_and_export, auth_code)

    failed_devices = []
    for device_name, future in futures_results.items():
        if not future.result():
            failed_devices.append(device_name)

    if failed_devices:
        print('ERROR: Failed retrieving the measurements for the following devices:')
        [print('- {}'.format(name)) for name in failed_devices]
        answer = input('\n|| Do you want to retrieve the information without specifying a begin timestamp for the above devices? ')
        if any(x in answer for x in ['yes', 'Yes', 'YES', 'y', 'Y']):
            with futures.ThreadPoolExecutor() as executor:
                for device in devices:
                    if device.name in failed_devices:
                        executor.submit(device.get_values_and_export, auth_code, True)

    for device in devices:
        device.update_json(config)

    with open('config.json', 'w') as config_file:
        json.dump(config, config_file, indent=4)
