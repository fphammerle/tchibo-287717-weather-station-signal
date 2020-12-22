# Tchibo 287717 Weather Station Signal Decoding

## Product Details

- **Name**: Tchibo Funk-Wetterstation
- **Model**: 287717
- **Frequency** (indicated): 434MHz
- Powered by two 1.5V AAA batteries
- Contains thermometer and hygrometer

## Signal

Sensor transmits an [OOK-modulated](https://en.wikipedia.org/wiki/On%E2%80%93off_keying)
1-second-long signal approximately once every 5 minutes.

Recorded with [gqrx](https://gqrx.dk/) via RTL2832U/R820T (433.79MHz, AM):
![image](docs/img/gqrx_20201217_135504_433790000.silences-shortened-0.1s.wav/entire-signal.svg)
![image](docs/img/gqrx_20201217_135504_433790000.silences-shortened-0.1s.wav/message-signal.svg)

After conversion to binary signal:
![image](docs/img/gqrx_20201217_135504_433790000.silences-shortened-0.1s.wav/entire-signal-digitalized.svg)

## Decoding

Signal has a [pulse distance encoding](https://www.mikrocontroller.net/articles/IRMP_-_english#Pulse_Distance).

Each transmission contains 6 repeats of the same message.

Each messages consists of 42 bits.

Low-bits have a length of 2ms, high-bits 4ms:
![bit length](docs/img/20201222T114639+0100_1800000Hz.cf32/inspectrum/short.png)
![bit length](docs/img/20201222T114639+0100_1800000Hz.cf32/inspectrum/long.png)

We recorded a few transmissions (`recordings/*.wav`)
and compared the received data with the values indicated on the display (`displayed-values.yml`).

| bit range | carried information                                    |
|-----------|--------------------------------------------------------|
| 0-9       | constant, maybe sensor address?                        |
| 10-13     | unknown                                                |
| 14-25     | temperature                                            |
| 26-33     | relative humidity                                      |
| 34-42     | probably checksum                                      |

### Humidity

| bit index | 26 | 27 | 28 | 29 | 30  | 31 | 32 | 33 |
|-----------|----|----|----|----|-----|----|----|----|
| bit value | 8  | 4  | 2  | 1  | 128 | 64 | 32 | 16 |

Provides the relative humidity in percent.

### Temperature

| bit index | 14 | 15 | 16 | 17 | 18  | 19 | 20 | 21 |  22  |  23  | 24  | 25  |
|-----------|----|----|----|----|-----|----|----|----|------|------|-----|-----|
| bit value | 8  | 4  | 2  | 1  | 128 | 64 | 32 | 16 | 2048 | 1024 | 512 | 256 |

Linear regression model estimates
`temperature_celsius = temperature_index * 0.055601938800118336 - 67.83753671810342`.
