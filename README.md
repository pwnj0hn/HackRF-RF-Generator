# HackRF RF Generator
A lightweight GUI-based RF signal generator for HackRF One using GNU Radio.
The application provides a simple and oscilloscope-friendly interface for generating common RF modulation types directly from a PC using a HackRF One.
Designed for RF experimentation, receiver testing, oscilloscope work, amateur radio testing, and general RF bench use.
---
## Features
- CW carrier generation
- AM modulation
- Narrowband FM (NBFM)
- Wideband FM (WBFM)
- USB and LSB single-sideband test tones
- Real-time signal preview
- Simple presets
- Clean and minimal GUI
- Built with Python + GNU Radio
---
## Installation
### Debian / Ubuntu / Linux Mint
```bash
sudo apt update
sudo apt install gnuradio gr-osmosdr hackrf python3-tk python3-numpy python3-matplotlib

⸻

Usage

Start the application:

python3 hackrf_rf_generator.py

⸻

Example Uses

CW

Useful for:

* Oscilloscope testing
* Frequency counter testing
* RF filter testing
* Receiver alignment

AM

Useful for:

* Modulation demonstrations
* Envelope visualization on analog oscilloscopes
* RF learning and experimentation

NBFM

Useful for:

* Amateur radio receiver testing
* Narrowband FM experiments

WBFM

Useful for:

* SDR testing
* FM radio experiments

USB / LSB

Useful for:

* SSB receiver testing
* Sideband demonstrations
* RF experimentation

⸻

Notes

* HackRF is not a calibrated laboratory signal generator.
* Output amplitude and spectral purity are limited.
* Use attenuators, dummy loads, or shielded setups where appropriate.
* Only transmit where legally permitted.

⸻

Tested With

* HackRF One
* GNU Radio
* Analog oscilloscopes
* SDR receivers
* Amateur radios
* Frequency counters

⸻

Future Ideas

Possible future additions:

* Audio/microphone input
* Frequency sweep mode
* Signal recording/playback
* Waterfall/spectrum display
* External frequency counter integration
* Additional modulation types

⸻

License

MIT License

:::
