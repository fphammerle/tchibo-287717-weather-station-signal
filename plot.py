#!/usr/bin/env python3

import argparse
import itertools
import json
import logging
import pathlib
import typing

from matplotlib import pyplot
import numpy
import scipy.io.wavfile
import scipy.ndimage
import yaml

_LOGGER = logging.getLogger(__name__)

_DISPLAYED_VALUES_INPUT_PATH = pathlib.Path(__file__).parent.joinpath(
    "displayed-values.yml"
)
_MESSAGES_OUTPUT_PATH = pathlib.Path(__file__).parent.joinpath("messages.json")

# https://git.hammerle.me/fphammerle/config-ipython/src/3dc22bb705f2c18179413a682f73ae95148634fe/profile_default/startup/init.py#L6
def trim_where(
    # https://docs.python.org/3.8/library/collections.abc.html#collections-abstract-base-classes
    sequence: typing.Sequence,
    condition: typing.Sequence[bool],
) -> typing.Sequence:
    start = 0
    for item_condition in condition:
        if item_condition:
            start += 1
        else:
            break
    stop = len(sequence)
    assert stop == len(condition)
    for item_condition in condition[::-1]:
        if item_condition:
            stop -= 1
        else:
            break
    return sequence[start:stop]


# https://git.hammerle.me/fphammerle/config-ipython/src/3dc22bb705f2c18179413a682f73ae95148634fe/profile_default/startup/init.py#L27
def wavfile_read_mono(path):
    # https://docs.scipy.org/doc/scipy/reference/generated/scipy.io.wavfile.read.html
    rate, data = scipy.io.wavfile.read(path)
    data_first_channel = data[:, 0]
    for channel_index in range(1, data.shape[1]):
        assert (data_first_channel == data[:, channel_index]).all()
    return rate, data_first_channel


def _read_recording(path: pathlib.Path) -> numpy.ndarray:
    rate, data = wavfile_read_mono(path)
    assert rate == 48000
    return trim_where(sequence=data, condition=data < 1000)


def _main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)s:%(funcName)s:%(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    logging.getLogger("matplotlib.font_manager").setLevel(logging.INFO)
    argparser = argparse.ArgumentParser()
    argparser.add_argument("recording_paths", type=pathlib.Path, nargs="+")
    argparser.add_argument("--plot-signal", action="store_true")
    argparser.add_argument("--plot-digitalized-signal", action="store_true")
    argparser.add_argument("--plot-length-histograms", action="store_true")
    args = argparser.parse_args()
    _LOGGER.debug("args=%r", args)
    displayed_values = yaml.safe_load(_DISPLAYED_VALUES_INPUT_PATH.read_text())
    bit_lengths = {False: [], True: []}
    try:
        recordings_message_data_bits = json.loads(_MESSAGES_OUTPUT_PATH.read_text())
    except FileNotFoundError:
        recordings_message_data_bits = {}
    for recording_path in args.recording_paths:
        signal = _read_recording(recording_path)
        if args.plot_signal:
            pyplot.plot(signal, label=recording_path.name)
        threshold = (signal.min() + signal.max()) / 2
        digitalized_signal = signal > threshold
        if args.plot_digitalized_signal:
            pyplot.plot(
                digitalized_signal * signal.max() / 2, label=recording_path.name
            )
        signal_bit_lengths = {False: [], True: []}
        for group_index, (bit, signal_group_iter) in enumerate(
            itertools.groupby(digitalized_signal)
        ):
            signal_group_length = sum(1 for _ in signal_group_iter)
            if group_index < 31:  # preamble
                if group_index % 2 == 1:
                    assert 15 <= signal_group_length <= 33, signal_group_length
                elif group_index != 0:
                    assert 362 <= signal_group_length <= 435, signal_group_length
            else:
                signal_bit_lengths[bit].append(signal_group_length)
                assert not bit or signal_group_length <= 36, signal_group_length
        assert min(signal_bit_lengths[False][:-1]) >= 85, min(signal_bit_lengths[False])
        for bit in bit_lengths.keys():
            bit_lengths[bit].extend(signal_bit_lengths[bit])
        assert len(signal_bit_lengths[False]) == 264
        messages_low_bit_lengths = numpy.reshape(
            numpy.array(signal_bit_lengths[False]), (6, 44)
        )
        assert (
            messages_low_bit_lengths.flatten()[:-1] >= 85
        ).all(), messages_low_bit_lengths.flatten()[:-1].min()
        assert (
            messages_low_bit_lengths[:, -2:].flatten()[:-1] >= 365
        ).all(), messages_low_bit_lengths[:, -2:].min()
        assert (
            messages_low_bit_lengths[:, :-2] <= 215
        ).all(), messages_low_bit_lengths[:, :-2].max()
        assert (
            (messages_low_bit_lengths[:, :-2] <= 118)
            | (messages_low_bit_lengths[:, :-2] >= 182)
        ).all(), messages_low_bit_lengths[:, :-2]
        messages_data_bits = messages_low_bit_lengths[:, :-2] > 150
        recordings_message_data_bits[recording_path.name] = list(
            map(int, messages_data_bits[0])
        )
        assert all(
            (messages_data_bits[0] == messages_data_bits[msg_idx]).all()
            for msg_idx in range(1, messages_data_bits.shape[0])
        )
        displayed_temperature_degrees_celsius = displayed_values.get(
            recording_path.name, {}
        ).get("temperature_degrees_celsius")
        displayed_relative_humidity = displayed_values.get(recording_path.name, {}).get(
            "relative_humidity"
        )
        temperature_index, = numpy.packbits(
            messages_data_bits[0, 22:26], bitorder="big"
        ) | (numpy.packbits(messages_data_bits[0, 18:22], bitorder="big") >> 4)
        temperature_index <<= 4
        temperature_index |= (
            numpy.packbits(messages_data_bits[0, 14:18], bitorder="big") >> 4
        )[0]
        temperature_degrees_celsius = (
            temperature_index * 0.055601938800118336 - 67.83753671810342
        )
        assert not displayed_temperature_degrees_celsius or (
            abs(temperature_degrees_celsius - displayed_temperature_degrees_celsius)
            < 0.049
        )
        relative_humidity_percent, = numpy.packbits(
            messages_data_bits[0, 30:34], bitorder="big"
        ) | (numpy.packbits(messages_data_bits[0, 26:30], bitorder="big") >> 4)
        assert (
            not displayed_relative_humidity
            or (int(displayed_relative_humidity * 100)) == relative_humidity_percent
        )
        print(
            recording_path.name.split(".", maxsplit=1)[0],
            "".join(map(str, map(int, messages_data_bits[0, :10]))),
            "".join(map(str, map(int, messages_data_bits[0, 10:14]))),
            "{:.1f}°C".format(temperature_degrees_celsius),
            "{:.0f}%".format(relative_humidity_percent).rjust(4),
            "".join(map(str, map(int, messages_data_bits[0, 30:]))),  # checksum?
            "{:.1f}°C".format(displayed_temperature_degrees_celsius).rjust(6)
            if displayed_temperature_degrees_celsius
            else None,
        )
    _MESSAGES_OUTPUT_PATH.write_text(json.dumps(recordings_message_data_bits))
    if args.plot_signal or args.plot_digitalized_signal:
        pyplot.legend()
    if args.plot_length_histograms:
        pyplot.figure()
        pyplot.hist(bit_lengths[True], bins=10)
        pyplot.figure()
        pyplot.hist(bit_lengths[False], bins=300)
    if args.plot_signal or args.plot_digitalized_signal or args.plot_length_histograms:
        pyplot.show()


if __name__ == "__main__":
    _main()
