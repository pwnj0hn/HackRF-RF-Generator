#!/usr/bin/env python3
"""
HackRF RF Signal Generator

A small GUI-based RF generator for HackRF using GNU Radio.
"""

import math
import sys
import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
from gnuradio import analog, blocks, gr
import osmosdr

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


SAMPLE_RATE = 2_000_000
BASE_AMPLITUDE = 0.65

TX_GAIN = 20
IF_GAIN = 30
BB_GAIN = 30

OFFSET_HZ = 100_000

MODES = ["CW", "AM", "NBFM", "WBFM", "USB", "LSB"]


class HackRFGenerator(gr.top_block):
    def __init__(
        self,
        carrier_mhz,
        mode,
        tone_hz,
        am_depth,
        nbfm_deviation_hz,
        wbfm_deviation_hz,
    ):
        super().__init__("HackRF RF Signal Generator")

        carrier_hz = carrier_mhz * 1_000_000.0
        mode = mode.upper()

        self.sink = osmosdr.sink(args="hackrf=0")
        self.sink.set_sample_rate(SAMPLE_RATE)
        self.sink.set_gain(TX_GAIN)
        self.sink.set_if_gain(IF_GAIN)
        self.sink.set_bb_gain(BB_GAIN)
        self.sink.set_bandwidth(0)

        if mode == "CW":
            self.sink.set_center_freq(carrier_hz)
            self._build_cw()
        else:
            self.sink.set_center_freq(carrier_hz - OFFSET_HZ)

            if mode == "AM":
                self._build_am(tone_hz, am_depth)
            elif mode == "NBFM":
                self._build_fm(tone_hz, nbfm_deviation_hz)
            elif mode == "WBFM":
                self._build_fm(tone_hz, wbfm_deviation_hz)
            elif mode == "USB":
                self._build_ssb(tone_hz, upper=True)
            elif mode == "LSB":
                self._build_ssb(tone_hz, upper=False)
            else:
                raise ValueError(f"Unsupported mode: {mode}")

    def _build_cw(self):
        src = analog.sig_source_c(
            SAMPLE_RATE,
            analog.GR_CONST_WAVE,
            0,
            BASE_AMPLITUDE,
            0,
        )
        self.connect(src, self.sink)

    def _build_am(self, tone_hz, am_depth):
        tone = analog.sig_source_f(
            SAMPLE_RATE,
            analog.GR_SIN_WAVE,
            tone_hz,
            am_depth,
            0,
        )

        add_one = blocks.add_const_ff(1.0)
        scale = blocks.multiply_const_ff(BASE_AMPLITUDE)
        to_complex = blocks.float_to_complex()

        zero_q = analog.sig_source_f(
            SAMPLE_RATE,
            analog.GR_CONST_WAVE,
            0,
            0,
            0,
        )

        offset_carrier = analog.sig_source_c(
            SAMPLE_RATE,
            analog.GR_COS_WAVE,
            OFFSET_HZ,
            1.0,
            0,
        )

        mixer = blocks.multiply_cc()

        self.connect(tone, add_one)
        self.connect(add_one, scale)
        self.connect(scale, (to_complex, 0))
        self.connect(zero_q, (to_complex, 1))
        self.connect(to_complex, (mixer, 0))
        self.connect(offset_carrier, (mixer, 1))
        self.connect(mixer, self.sink)

    def _build_fm(self, tone_hz, deviation_hz):
        tone = analog.sig_source_f(
            SAMPLE_RATE,
            analog.GR_SIN_WAVE,
            tone_hz,
            0.8,
            0,
        )

        sensitivity = 2.0 * math.pi * deviation_hz / SAMPLE_RATE
        fm = analog.frequency_modulator_fc(sensitivity)

        offset_carrier = analog.sig_source_c(
            SAMPLE_RATE,
            analog.GR_COS_WAVE,
            OFFSET_HZ,
            BASE_AMPLITUDE,
            0,
        )

        mixer = blocks.multiply_cc()

        self.connect(tone, fm)
        self.connect(fm, (mixer, 0))
        self.connect(offset_carrier, (mixer, 1))
        self.connect(mixer, self.sink)

    def _build_ssb(self, tone_hz, upper):
        ssb_offset = OFFSET_HZ + tone_hz if upper else OFFSET_HZ - tone_hz

        src = analog.sig_source_c(
            SAMPLE_RATE,
            analog.GR_COS_WAVE,
            ssb_offset,
            BASE_AMPLITUDE,
            0,
        )

        self.connect(src, self.sink)


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("HackRF RF Signal Generator")
        self.root.geometry("980x700")

        self.tb = None

        self.carrier_mhz = tk.DoubleVar(value=10.0)
        self.mode = tk.StringVar(value="CW")
        self.tone_hz = tk.DoubleVar(value=1000.0)
        self.am_depth_percent = tk.DoubleVar(value=70.0)
        self.nbfm_deviation_hz = tk.DoubleVar(value=2500.0)
        self.wbfm_deviation_hz = tk.DoubleVar(value=75000.0)
        self.status = tk.StringVar(value="Stopped")

        self.rows = {}

        self._build_ui()
        self._on_mode_changed()
        self._update_plot()

    def _build_ui(self):
        root_frame = ttk.Frame(self.root, padding=12)
        root_frame.pack(fill="both", expand=True)

        top = ttk.Frame(root_frame)
        top.pack(fill="x")

        signal_box = ttk.LabelFrame(top, text="Signal", padding=10)
        signal_box.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self._add_entry(signal_box, "carrier", 0, "Carrier frequency (MHz)", self.carrier_mhz)
        self._add_combo(signal_box, "mode", 1, "Mode", self.mode, MODES)
        self._add_entry(signal_box, "tone", 2, "Tone frequency (Hz)", self.tone_hz)
        self._add_entry(signal_box, "am", 3, "AM depth (%)", self.am_depth_percent)
        self._add_entry(signal_box, "nbfm", 4, "NBFM deviation (Hz)", self.nbfm_deviation_hz)
        self._add_entry(signal_box, "wbfm", 5, "WBFM deviation (Hz)", self.wbfm_deviation_hz)

        preset_box = ttk.LabelFrame(top, text="Presets", padding=10)
        preset_box.pack(side="right", fill="y")

        ttk.Button(preset_box, text="10 MHz CW", command=self._preset_cw).pack(fill="x", pady=2)
        ttk.Button(preset_box, text="10 MHz AM", command=self._preset_am).pack(fill="x", pady=2)
        ttk.Button(preset_box, text="10 MHz NBFM", command=self._preset_nbfm).pack(fill="x", pady=2)
        ttk.Button(preset_box, text="10 MHz WBFM", command=self._preset_wbfm).pack(fill="x", pady=2)
        ttk.Button(preset_box, text="10 MHz USB", command=self._preset_usb).pack(fill="x", pady=2)
        ttk.Button(preset_box, text="10 MHz LSB", command=self._preset_lsb).pack(fill="x", pady=2)

        button_bar = ttk.Frame(root_frame)
        button_bar.pack(fill="x", pady=(10, 4))

        ttk.Button(button_bar, text="Start", command=self.start).pack(side="left", padx=(0, 8))
        ttk.Button(button_bar, text="Stop", command=self.stop).pack(side="left")
        ttk.Label(button_bar, textvariable=self.status).pack(side="left", padx=16)

        self.fig = Figure(figsize=(9, 4.8), dpi=100)
        self.ax_rf = self.fig.add_subplot(211)
        self.ax_mod = self.fig.add_subplot(212)

        self.canvas = FigureCanvasTkAgg(self.fig, master=root_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, pady=(8, 8))

        notes = (
            "Notes:\n"
            "• CW is a pure RF carrier. Useful for checking scopes, counters, receivers, filters and cables.\n"
            "• AM is easiest to see on an oscilloscope. Use a slower timebase, for example 0.1 ms/div.\n"
            "• NBFM is for normal narrow FM receivers. Try 2.5 kHz or 5 kHz deviation.\n"
            "• WBFM is broadcast-style wide FM. Try with a WFM receiver, not normal NFM.\n"
            "• USB/LSB here generates a simple single-sideband test tone, not microphone speech.\n"
            "• HackRF amplitude is not calibrated output voltage. Use attenuation/dummy load where appropriate."
        )
        ttk.Label(root_frame, text=notes, justify="left").pack(anchor="w")

        for var in [
            self.carrier_mhz,
            self.mode,
            self.tone_hz,
            self.am_depth_percent,
            self.nbfm_deviation_hz,
            self.wbfm_deviation_hz,
        ]:
            var.trace_add("write", lambda *_: self._update_plot())

        self.mode.trace_add("write", lambda *_: self._on_mode_changed())

    def _add_entry(self, parent, key, row, label, var):
        label_widget = ttk.Label(parent, text=label)
        entry_widget = ttk.Entry(parent, textvariable=var, width=18)
        label_widget.grid(row=row, column=0, sticky="w", pady=3, padx=(0, 8))
        entry_widget.grid(row=row, column=1, sticky="w", pady=3)
        self.rows[key] = (label_widget, entry_widget)

    def _add_combo(self, parent, key, row, label, var, values):
        label_widget = ttk.Label(parent, text=label)
        combo_widget = ttk.Combobox(parent, textvariable=var, values=values, state="readonly", width=16)
        label_widget.grid(row=row, column=0, sticky="w", pady=3, padx=(0, 8))
        combo_widget.grid(row=row, column=1, sticky="w", pady=3)
        self.rows[key] = (label_widget, combo_widget)

    def _show_row(self, key, show=True):
        label, widget = self.rows[key]
        if show:
            label.grid()
            widget.grid()
        else:
            label.grid_remove()
            widget.grid_remove()

    def _on_mode_changed(self):
        mode = self.mode.get()
        self._show_row("tone", mode in ["AM", "NBFM", "WBFM", "USB", "LSB"])
        self._show_row("am", mode == "AM")
        self._show_row("nbfm", mode == "NBFM")
        self._show_row("wbfm", mode == "WBFM")

    def _set_common_10mhz(self, mode):
        self.carrier_mhz.set(10.0)
        self.mode.set(mode)
        self.tone_hz.set(1000.0)
        self.am_depth_percent.set(70.0)
        self.nbfm_deviation_hz.set(2500.0)
        self.wbfm_deviation_hz.set(75000.0)

    def _preset_cw(self):
        self._set_common_10mhz("CW")

    def _preset_am(self):
        self._set_common_10mhz("AM")

    def _preset_nbfm(self):
        self._set_common_10mhz("NBFM")

    def _preset_wbfm(self):
        self._set_common_10mhz("WBFM")

    def _preset_usb(self):
        self._set_common_10mhz("USB")

    def _preset_lsb(self):
        self._set_common_10mhz("LSB")

    def _update_plot(self):
        try:
            mode = self.mode.get()
            tone_hz = float(self.tone_hz.get())
            am_depth = float(self.am_depth_percent.get()) / 100.0
            nbfm_dev = float(self.nbfm_deviation_hz.get())
            wbfm_dev = float(self.wbfm_deviation_hz.get())
        except Exception:
            return

        self.ax_rf.clear()
        self.ax_mod.clear()

        t = np.linspace(0, 0.004, 5000)
        preview_carrier = 10_000.0
        tone = np.sin(2.0 * np.pi * tone_hz * t)
        carrier = np.sin(2.0 * np.pi * preview_carrier * t)

        if mode == "CW":
            rf = carrier
            self.ax_rf.set_title("CW preview: pure carrier")
            self.ax_mod.plot(t * 1000.0, np.zeros_like(t))
            self.ax_mod.set_title("No modulation")

        elif mode == "AM":
            envelope = 1.0 + am_depth * tone
            rf = envelope * carrier
            self.ax_rf.plot(t * 1000.0, envelope, linestyle="--", label="Envelope")
            self.ax_rf.plot(t * 1000.0, -envelope, linestyle="--")
            self.ax_rf.set_title(f"AM preview: {am_depth * 100:.0f}% depth")
            self.ax_mod.plot(t * 1000.0, tone)
            self.ax_mod.set_title("Sine tone modulation")

        elif mode in ["NBFM", "WBFM"]:
            deviation = nbfm_dev if mode == "NBFM" else wbfm_dev
            inst_freq = preview_carrier + (deviation / 20.0) * tone
            phase = 2.0 * np.pi * np.cumsum(inst_freq) / len(t)
            rf = np.sin(phase)
            self.ax_rf.set_title(f"{mode} preview: deviation {deviation:.0f} Hz")
            self.ax_mod.plot(t * 1000.0, tone)
            self.ax_mod.set_title("Sine tone frequency modulation")

        elif mode in ["USB", "LSB"]:
            side = 1 if mode == "USB" else -1
            rf = np.sin(2.0 * np.pi * (preview_carrier + side * tone_hz) * t)
            self.ax_rf.set_title(f"{mode} preview: single sideband test tone")
            self.ax_mod.plot(t * 1000.0, tone)
            self.ax_mod.set_title("Sine tone sideband")

        else:
            rf = np.zeros_like(t)

        self.ax_rf.plot(t * 1000.0, rf, label="RF preview")
        self.ax_rf.set_xlabel("Time (ms)")
        self.ax_rf.set_ylabel("RF amplitude")
        self.ax_rf.grid(True)
        self.ax_rf.legend(loc="upper right")

        self.ax_mod.set_xlabel("Time (ms)")
        self.ax_mod.set_ylabel("Tone")
        self.ax_mod.grid(True)

        self.fig.tight_layout()
        self.canvas.draw_idle()

    def _validate(self):
        carrier = float(self.carrier_mhz.get())
        tone_hz = float(self.tone_hz.get())
        am_depth = float(self.am_depth_percent.get()) / 100.0
        nbfm_dev = float(self.nbfm_deviation_hz.get())
        wbfm_dev = float(self.wbfm_deviation_hz.get())

        if not 1.0 <= carrier <= 6000.0:
            raise ValueError("Carrier frequency must be between 1 and 6000 MHz.")
        if tone_hz <= 0:
            raise ValueError("Tone frequency must be greater than 0 Hz.")
        if not 0.0 <= am_depth <= 1.0:
            raise ValueError("AM depth must be between 0 and 100 percent.")
        if nbfm_dev <= 0:
            raise ValueError("NBFM deviation must be greater than 0 Hz.")
        if wbfm_dev <= 0:
            raise ValueError("WBFM deviation must be greater than 0 Hz.")
        if nbfm_dev > 25_000:
            raise ValueError("For NBFM, keep deviation at or below 25000 Hz.")
        if wbfm_dev > 250_000:
            raise ValueError("For WBFM, keep deviation at or below 250000 Hz.")

        return carrier, tone_hz, am_depth, nbfm_dev, wbfm_dev

    def start(self):
        self.stop()
        try:
            carrier, tone_hz, am_depth, nbfm_dev, wbfm_dev = self._validate()

            self.tb = HackRFGenerator(
                carrier_mhz=carrier,
                mode=self.mode.get(),
                tone_hz=tone_hz,
                am_depth=am_depth,
                nbfm_deviation_hz=nbfm_dev,
                wbfm_deviation_hz=wbfm_dev,
            )
            self.tb.start()
            self.status.set(f"Running {self.mode.get()} at {carrier:.6f} MHz")

        except Exception as exc:
            self.tb = None
            self.status.set("Stopped")
            messagebox.showerror("Error", str(exc))

    def stop(self):
        if self.tb is not None:
            try:
                self.tb.stop()
                self.tb.wait()
            finally:
                self.tb = None
        self.status.set("Stopped")


def main():
    root = tk.Tk()
    app = App(root)

    def close():
        app.stop()
        root.destroy()
        sys.exit(0)

    root.protocol("WM_DELETE_WINDOW", close)
    root.mainloop()


if __name__ == "__main__":
    main()
