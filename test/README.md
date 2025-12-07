# usage


**API Tests**
testing grok test APIs
```
python -m test.text
```
testing grok audio APIs and system audio input and output devices
```
python -m test.audio
```

**test online**

testing online interview

0. test your audio by using `pyhon -m test.audio` in your project directory. It will dump the available audio input and output devices.
```
=== Available Audio Devices ===
  0 DELL U4025QW, Core Audio (0 in, 2 out)
  1 Hao’s iPhone Microphone, Core Audio (1 in, 0 out)
  2 BlackHole 2ch, Core Audio (2 in, 2 out)
> 3 MacBook Pro Microphone, Core Audio (1 in, 0 out)
< 4 MacBook Pro Speakers, Core Audio (0 in, 2 out)
  5 Multi-Output Device, Core Audio (0 in, 2 out)
===============================
```

here, the device ID 3 is the audio input device (microphone) and device ID 4 is the audio output device (speakers).

1. for `backend/src/online/strategies.py`, set `INTERVIEWER_DEVICE_ID` and `CANDIDATE_DEVICE_ID` according to your system audio input and output devices. (In the previous example, for testing, set `INTERVIEWER_DEVICE_ID = 3` and `CANDIDATE_DEVICE_ID = 3`)


2. run the online interview test by 
```
python -m test.strategies
```