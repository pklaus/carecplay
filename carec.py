#!/usr/bin/env python

import epics, logging, time, pickle, copy

logger = logging.getLogger(__name__)

PV_NAMES = []
PVS = {}
VALUE_UPDATES = []
LATEST_VALUE_UPDATE_BY_PV = {}
CONNECTION_CHANGES = []

def serializable_copy_value_update(pv_dict):
    pv_dict = copy.copy(pv_dict)
    del pv_dict['cb_info']
    return pv_dict

def cb_value_update(**kwargs):
    global VALUE_UPDATES, LATEST_VALUE_UPDATE_BY_PV
    kwargs = serializable_copy_value_update(kwargs)
    kwargs['ts'] = time.time()
    VALUE_UPDATES.append(kwargs)
    LATEST_VALUE_UPDATE_BY_PV[kwargs['pvname']] = kwargs
    logger.info("PV: {pvname:75s} new value: {char_value}".format(**kwargs))

def serializable_copy_connection_change(cc_dict):
    cc_dict = copy.copy(cc_dict)
    del cc_dict['pv']
    return cc_dict

def cb_connection_change(**kwargs):
    global CONNECTION_CHANGES
    kwargs = serializable_copy_connection_change(kwargs)
    kwargs['ts'] = time.time()
    CONNECTION_CHANGES.append(kwargs)
    logger.info("PV: {pvname:75s} conn: {conn}".format(**kwargs))

def register(pv_names):
    global PVS, PV_NAMES
    for pv_name in pv_names:
        PVS[pv_name] = epics.PV(pv_name, auto_monitor=True, form='ctrl', callback=cb_value_update, connection_callback=cb_connection_change)
        PV_NAMES.append(pv_name)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('pv_list', type=argparse.FileType('r', encoding='UTF-8'))
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    level = logging.DEBUG if args.debug else logging.WARNING
    logging.basicConfig(level=level)

    pv_list = args.pv_list.read().split('\n')
    pv_list = [pv_name.strip() for pv_name in pv_list] # strip off whitespace
    pv_list = [pv_name for pv_name in pv_list if pv_name] # clean out empty entries

    start = time.time()
    register(pv_list)

    try:
        print(f"Started the recording. It can be stopped with Ctrl-C.")
        while True:
            time.sleep(1.)
    except KeyboardInterrupt:
        print("Ctrl-C pressed. Stopping capture...")
        print("Proceeding to serialize the data...")
    finally:
        for pv_name in pv_list:
            PVS[pv_name].clear_auto_monitor()
            #PVS[pv_name].disconnect()
            del PVS[pv_name]
        end = time.time()
        print(f"Stopped capture after {end-start:.2f} s.")
        print(f"Registered {len(VALUE_UPDATES)} value updates.")
        print(f"Registered {len(CONNECTION_CHANGES)} connection changes.")

        print(f"Do you want to serialize (store) the registered data to the output file now?")
        answer = input("Y/n > ")
        if answer.strip().lower().endswith('n'):
            logger.warn("Closing without storing the data.")

        with open('data.pickle', 'wb') as f:
            data_to_serialize = {
              'value_updates': VALUE_UPDATES,
              'connection_changes': CONNECTION_CHANGES,
              'latest_value_update_by_pv': LATEST_VALUE_UPDATE_BY_PV,
              'pv_names': PV_NAMES,
            }
            pickle.dump(data_to_serialize, f, pickle.HIGHEST_PROTOCOL)

if __name__ == "__main__": main()
