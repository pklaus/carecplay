#!/usr/bin/env python

import os, sys, logging, pickle, time, itertools
from threading import Thread, Event, Lock
from pcaspy import Driver, SimpleServer

VALUE_UPDATES = None
CONNECTION_CHANGES = None
LATEST_VALUE_UPDATE_BY_PV = None
PV_NAMES = None

class myDriver(Driver):

    def __init__(self, pvdb, **kwargs):
        self.pvdb = pvdb
        self.offset = kwargs.get('offset', 0.0)
        self.wrap = kwargs.get('wrap', False)
        self.logger = logging.getLogger('PCASpy_Driver')
        super(myDriver, self).__init__()
        self.eid = Event()
        self.tid = Thread(target = self.runIOC) 
        self.tid.setDaemon(True)
        self.tid.start()
        self.updatePVs()


    def read(self, reason):
        self.logger.warning(reason)
        return super(myDriver, self).read(reason)

    def runIOC(self):

        idx = 0
        while True:

            vu = VALUE_UPDATES[idx]
            ts_next_update = vu['ts'] + self.offset
            ts_now = time.time()
            if ts_next_update > (ts_now + 0.05):
                self.logger.debug("Sleeping for {:.3f}".format(ts_next_update - ts_now))
                self.eid.wait(ts_next_update - ts_now)
            self.setParam(vu['pvname'], vu['value'])
            # may want to set setParamInfo(reason, info) here as well (if limits etc changed):
            # https://pcaspy.readthedocs.io/en/latest/api.html#pcaspy.Driver.setParamInfo
            self.logger.info("Setting PV {pvname} to {value}".format(**vu))
            self.updatePVs()
            idx += 1
            if idx == len(VALUE_UPDATES):
                if self.wrap:
                    idx = 0
                    self.offset = time.time() - VALUE_UPDATES[0]['ts']
                else:
                    return

def main():
    global VALUE_UPDATES, CONNECTION_CHANGES, LATEST_VALUE_UPDATE_BY_PV, PV_NAMES

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', default='')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--wrap', action='store_true')
    parser.add_argument('data_file')
    args = parser.parse_args()

    level = logging.DEBUG if args.debug else logging.INFO
    fmt = "%(asctime)s - %(funcName)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=level, format=fmt)

    with open(args.data_file, 'rb') as f:
        data = pickle.load(f)
        VALUE_UPDATES = data['value_updates']
        CONNECTION_CHANGES = data['connection_changes']
        LATEST_VALUE_UPDATE_BY_PV = data['latest_value_update_by_pv']
        PV_NAMES = data['pv_names']

    if not VALUE_UPDATES: parser.error("No value update contained in the recorded data set. Exiting.")

    VALUE_UPDATES.sort(key=lambda x: x['ts'])
    CONNECTION_CHANGES.sort(key=lambda x: x['ts'])

    offset = time.time() - VALUE_UPDATES[0]['ts']

    pvdb = {}

    for pv_name, vu in LATEST_VALUE_UPDATE_BY_PV.items():
        type_map = {'ctrl_double': 'float', 'time_string': 'string', 'ctrl_enum': 'enum'}
        pv_type = type_map[vu['type']]
        pv_entry = {'type': pv_type, 'value': vu['value'], 'unit': vu['units'], 'prec': vu['precision']}
        enum_strs = vu['enum_strs']

        limits_pyepics = map(lambda x: '_'.join(x), itertools.product(['lower', 'upper'], ['ctrl_limit', 'alarm_limit', 'warning_limit']))
        limits_pcaspy  = 'lolim', 'lolo', 'low', 'hilim', 'hihi', 'high'
        limits_map = dict(zip(limits_pyepics, limits_pcaspy))
        for limit in limits_map.keys():
            # PCASpy expects the default values to be 0:
            if vu[limit] is None: vu[limit] = 0.0
            pv_entry[limits_map[limit]] = vu[limit]

        if pv_type == 'enum' and enum_strs is not None:
            enum_strs = list(enum_strs)
            for i in range(len(enum_strs)):
                #enum_strs[i] = enum_strs[i].decode('ascii')
                try: enum_strs[i] = enum_strs[i].decode('ascii')
                except: pass
            pv_entry['enums'] = enum_strs
        pvdb[pv_name] = pv_entry

    server = SimpleServer()
    server.createPV(args.prefix, pvdb)

    driver = myDriver(pvdb, offset=offset, wrap=args.wrap)

    # process CA transactions
    while True:
        server.process(0.1)

if __name__ == '__main__': main()
