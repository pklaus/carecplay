## CaRecPlay

### Prerequisits

    pip install --upgrade -r requirements.txt

### Recording

Start recording using:

    ./carec.py your_list_of_pv_names.txt

### Playback

    ./caplay.py --wrap your_recorded_data_file.pickle

### Tips'n'tricks

You can fix errors like

> Traceback (most recent call last):
>   File "\_ctypes/callbacks.c", line 234, in 'calling callback function'
>   File "/local/pyvenv/playground-3.6\_local/lib/python3.6/site-packages/epics/ca.py", line 542, in \_onMonitorEvent
>     kwds[attr] = BYTES2STR(getattr(tmpv, attr, None))
>   File "/local/pyvenv/playground-3.6\_local/lib/python3.6/site-packages/epics/utils3.py", line 25, in b2s
>     return str(st1, EPICS\_STR_ENCODING)
> UnicodeDecodeError: 'ascii' codec can't decode byte 0xb0 in position 0: ordinal not in range(128)

by setting the appropriate encoding:

    export PYTHONIOENCODING=latin1
