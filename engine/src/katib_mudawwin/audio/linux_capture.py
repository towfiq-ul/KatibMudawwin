from __future__ import annotations

import json
import logging
import subprocess
import threading
from typing import Optional

import numpy as np
import sounddevice as sd

from katib_mudawwin.audio.base import AudioSource

logger = logging.getLogger(__name__)


class ZoomLoopbackSource(AudioSource):
    """Captures Zoom's own output via a dedicated PulseAudio/PipeWire null
    sink + parec, so only Zoom's audio is captured (not unrelated system
    sounds).

    Creating the null sink doesn't make Zoom play into it -- Zoom keeps
    streaming to whatever sink was already its default. We have to actively
    move Zoom's sink-input(s) onto our null sink with `pactl
    move-sink-input`, both once at start (in case Zoom is already playing)
    and on an ongoing poll (Zoom can (re)create its output stream after we
    start capturing, e.g. once the call's audio actually connects).

    On PipeWire, `pactl move-sink-input` can fail outright (EINVAL) for
    streams that pin their own routing target -- confirmed against a real
    Zoom snap build, whose output stream sets `target.object` plus
    `node.dont-reconnect=true`, which silently blocks both the pulse-compat
    move and a plain metadata-based reroute. `_link_pipewire_ports` works
    around that by linking the stream's ports directly with `pw-link`,
    which -- unlike the pulse-compat move -- isn't blocked by the pin. That
    fan-out link is additive (it doesn't disturb Zoom's existing connection
    to your actual output device), so unlike a real `move-sink-input`,
    nothing here ever silences what you'd normally hear -- there's
    deliberately no loopback-back-to-default-sink to "restore" audio,
    since one isn't needed and would just play a second, duplicate copy
    through whatever PulseAudio considers the default sink (confirmed
    against a real call: that's not reliably the device Zoom's audio is
    actually going to, e.g. a Bluetooth headset that isn't the system
    default sink -- the duplicate copy played through the laptop speaker
    at the same time).
    """

    def __init__(self, sink_name: str, sample_rate: int = 16000, process_hint: str = "zoom"):
        self.sink_name = sink_name
        self.sample_rate = sample_rate
        self.process_hint = process_hint.lower()
        self._null_sink_module_id: Optional[str] = None
        self._proc: Optional[subprocess.Popen] = None
        self._buffer = bytearray()
        self._lock = threading.Lock()
        self._reader_thread: Optional[threading.Thread] = None
        self._mover_thread: Optional[threading.Thread] = None
        self._stopped = threading.Event()
        self._routed_indices: set = set()

    def _pactl(self, *args: str) -> str:
        result = subprocess.run(["pactl", *args], capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def start(self) -> None:
        self._stopped.clear()
        self._null_sink_module_id = self._pactl(
            "load-module",
            "module-null-sink",
            f"sink_name={self.sink_name}",
            "channel_map=mono",
        )
        self._proc = subprocess.Popen(
            [
                "parec",
                f"--device={self.sink_name}.monitor",
                f"--rate={self.sample_rate}",
                "--channels=1",
                "--format=s16le",
            ],
            stdout=subprocess.PIPE,
        )
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()

        self._move_zoom_sink_inputs()
        self._mover_thread = threading.Thread(target=self._mover_loop, daemon=True)
        self._mover_thread.start()

    def _move_zoom_sink_inputs(self) -> None:
        try:
            result = subprocess.run(
                ["pactl", "-f", "json", "list", "sink-inputs"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )
            entries = json.loads(result.stdout)
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
            json.JSONDecodeError,
        ):
            return
        for entry in entries:
            props = entry.get("properties", {}) or {}
            binary = (props.get("application.process.binary") or "").lower()
            name = (props.get("application.name") or "").lower()
            if self.process_hint not in binary and self.process_hint not in name:
                continue
            index = entry.get("index")
            if index is None:
                continue
            moved = (
                subprocess.run(
                    ["pactl", "move-sink-input", str(index), self.sink_name],
                    capture_output=True,
                    check=False,
                ).returncode
                == 0
            )
            if not moved:
                node_name = props.get("node.name") or props.get("application.name")
                node_id = props.get("object.id")
                moved = bool(node_name) and self._link_pipewire_ports(node_name, node_id)

            if moved:
                if index not in self._routed_indices:
                    self._routed_indices.add(index)
                    logger.info(
                        "Routed Zoom audio stream (sink-input %s) into %s", index, self.sink_name
                    )
            elif index not in self._routed_indices:
                self._routed_indices.add(index)
                logger.warning(
                    "Could not route Zoom audio stream (sink-input %s) into %s -- "
                    "Zoom audio may not be captured",
                    index,
                    self.sink_name,
                )

    def _link_pipewire_ports(self, node_name: str, node_id: Optional[object]) -> bool:
        """Directly wires a PipeWire stream's ports to our null sink's ports
        with `pw-link`, bypassing whatever routing target the stream itself
        is pinned to. PipeWire ports fan out, so this doesn't disturb
        wherever the stream is already connected (e.g. the user's speakers).

        Zoom runs its mic-capture stream and its speaker-output stream as
        two distinct PipeWire nodes that share the exact same `node.name`
        ("ZOOM VoiceEngine" on the build this was confirmed against) --
        confirmed against a real Zoom snap build in a live call. Matching
        ports by name prefix alone (via `pw-link -o`) can't tell them apart
        and picks up the mic-capture node's `monitor_*` port (a tap of your
        own voice) alongside the real output port, leaking your own mic
        into the "Others" capture stream. Scoping the port lookup to the
        specific PipeWire node id of the sink-input we're moving (from
        pactl's `object.id` property) avoids that ambiguity.
        """
        try:
            dump = subprocess.run(
                ["pw-dump"], capture_output=True, text=True, timeout=5, check=True
            ).stdout
            objects = json.loads(dump)
            in_ports = subprocess.run(
                ["pw-link", "-i"], capture_output=True, text=True, timeout=5, check=True
            ).stdout.splitlines()
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
            json.JSONDecodeError,
        ):
            return False

        src_ports = []
        for obj in objects:
            if obj.get("type") != "PipeWire:Interface:Port":
                continue
            props = (obj.get("info") or {}).get("props") or {}
            if node_id is not None and str(props.get("node.id")) != str(node_id):
                continue
            if props.get("port.direction") != "out":
                continue
            port_name = props.get("port.name")
            if port_name:
                src_ports.append(f"{node_name}:{port_name}")
        src_ports.sort()
        dst_ports = sorted(p for p in in_ports if p.startswith(f"{self.sink_name}:"))
        if not src_ports or not dst_ports:
            return False

        all_linked = True
        for src, dst in zip(src_ports, dst_ports):
            result = subprocess.run(["pw-link", src, dst], capture_output=True, text=True, check=False)
            if result.returncode != 0 and "File exists" not in result.stderr:
                all_linked = False
        return all_linked

    def _mover_loop(self) -> None:
        while not self._stopped.wait(1.0):
            self._move_zoom_sink_inputs()

    def _read_loop(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        while not self._stopped.is_set():
            chunk = self._proc.stdout.read(4096)
            if not chunk:
                break
            with self._lock:
                self._buffer.extend(chunk)

    def read_chunk(self, num_frames: int) -> np.ndarray:
        num_bytes = num_frames * 2  # s16le = 2 bytes/frame
        with self._lock:
            data = bytes(self._buffer[:num_bytes])
            del self._buffer[:num_bytes]
        if len(data) % 2:
            # A trailing odd byte can happen if parec dies mid-write; drop it
            # rather than let frombuffer raise on a non-multiple-of-2 buffer.
            data = data[:-1]
        return np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

    def stop(self) -> None:
        self._stopped.set()
        if self._proc is not None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("parec did not terminate in time; killing it")
                self._proc.kill()
                self._proc.wait(timeout=5)
        if self._reader_thread is not None:
            self._reader_thread.join(timeout=2)
        if self._mover_thread is not None:
            self._mover_thread.join(timeout=2)
        if self._null_sink_module_id:
            subprocess.run(["pactl", "unload-module", self._null_sink_module_id], check=False)


class MicSource(AudioSource):
    """Captures the user's microphone via sounddevice."""

    def __init__(self, device: Optional[str], sample_rate: int = 16000):
        self.device = device
        self.sample_rate = sample_rate
        self._stream: Optional[sd.InputStream] = None
        self._buffer = bytearray()
        self._lock = threading.Lock()

    def _callback(self, indata, frames, time_info, status) -> None:
        with self._lock:
            self._buffer.extend(indata.tobytes())

    def start(self) -> None:
        self._stream = sd.InputStream(
            device=self.device,
            channels=1,
            samplerate=self.sample_rate,
            dtype="int16",
            callback=self._callback,
        )
        self._stream.start()

    def read_chunk(self, num_frames: int) -> np.ndarray:
        num_bytes = num_frames * 2
        with self._lock:
            data = bytes(self._buffer[:num_bytes])
            del self._buffer[:num_bytes]
        if len(data) % 2:
            data = data[:-1]
        return np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
