import random
import threading
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
    from qiskit import QuantumCircuit, transpile
    from qiskit.visualization import plot_histogram
except ImportError:
    QiskitRuntimeService = None
    Sampler = None
    QuantumCircuit = None
    transpile = None
    plot_histogram = None

try:
    from qiskit_aer import Aer
except ImportError:
    Aer = None


class QuantumCoin:
    """
        Turn quantum measurements into a stream of 'coin flips'.

        Always attempt IBM hardware first; on failure/timeout we fall back to
        Qiskit Aer. Classical RNG is the final fallback if neither quantum path
        is available.
    """

    def __init__(
        self,
        backend_name: str = "ibm_torino",
        aer_backend_name: str = "aer_simulator",
        shots: int = 256,
        hardware_timeout: float = 15.0,
        prefill_async: bool = True,
        save_histogram: bool = True,
        force_aer: bool = False,
        **kwargs,
    ):
        if "use_real_hardware" in kwargs:
            _ = kwargs["use_real_hardware"]

        self.use_hardware = (not force_aer) and (QiskitRuntimeService is not None)
        self.use_aer = (Aer is not None) and (QuantumCircuit is not None)
        self.backend_name = backend_name
        self.aer_backend_name = aer_backend_name
        self.shots = shots
        self.hardware_timeout = hardware_timeout
        self.prefill_async = prefill_async
        self.save_histogram = save_histogram
        self.force_aer = force_aer

        self.service = None
        self.backend = None
        self.sampler = None
        self.aer_backend = None

        self._buffer = []
        self._buffer_index = 0
        self._fetching = False

        if self.use_hardware:
            try:
                self.service = QiskitRuntimeService()
                self.backend = self.service.backend(self.backend_name)
                self.sampler = Sampler(self.backend)
                print(f"[QuantumCoin] Using hardware backend: {self.backend.name}")
            except Exception as exc:
                print(f"[QuantumCoin] Hardware init failed, will fall back to Aer: {exc}")
                self.use_hardware = False

        if self.use_aer:
            try:
                self.aer_backend = Aer.get_backend(self.aer_backend_name)
                if not self.use_hardware:
                    self.backend = self.aer_backend
                print(f"[QuantumCoin] Aer simulator available: {self.aer_backend.name}")
            except Exception as exc:
                print(f"[QuantumCoin] Aer init failed, will rely on hardware/classical: {exc}")
                self.use_aer = False

        if not self.use_hardware and not self.use_aer:
            print("[QuantumCoin] Using classical random bit (no quantum backend available).")

        if self.use_hardware or self.use_aer:
            if self.prefill_async:
                self._maybe_refill_async()
            else:
                self._refill_buffer()

    def _refill_buffer(self):
        """
        Run one quantum job with `self.shots` measurements, turn the
        measurement counts into a shuffled list of bits, and store in
        self._buffer.
        """
        if self._fetching:
            return
        self._fetching = True
        try:
            if QuantumCircuit is None or transpile is None:
                print("[QuantumCoin] _refill_buffer: missing Qiskit components.")
                self._buffer = []
                self._buffer_index = 0
                return

            qc = QuantumCircuit(1)
            qc.h(0)
            qc.measure_all()

            print("[QuantumCoin] Original circuit:")
            print(qc)

            target_backend = self.backend if (self.use_hardware and self.sampler is not None) else None
            qc_t = transpile(qc, target_backend) if target_backend is not None else qc

            counts = None

            if self.use_hardware and self.sampler is not None:
                try:
                    counts = self._run_hardware_counts(qc_t)
                except Exception as exc:
                    print(f"[QuantumCoin] Hardware sampling failed, trying Aer: {exc}")

            if counts is None and self.use_aer and self.aer_backend is not None:
                qc_aer = transpile(qc, self.aer_backend)
                try:
                    counts = self._run_aer_counts(qc_aer)
                except Exception as exc:
                    print(f"[QuantumCoin] Aer sampling failed, falling back to classical: {exc}")

            if counts is None:
                self._buffer = []
                self._buffer_index = 0
                print("[QuantumCoin] _refill_buffer: no quantum counts available, using classical fallback.")
                return

            if self.save_histogram and plot_histogram is not None:
                fig = plot_histogram(counts)
                fig.savefig("Q-histogram.png")
                plt.close(fig)
                print("[QuantumCoin] Saved histogram to Q-histogram.png")

            bit_list = []
            for bit_str, cnt in counts.items():
                b = int(bit_str)
                bit_list.extend([b] * cnt)

            random.shuffle(bit_list)

            self._buffer = bit_list
            self._buffer_index = 0
            print(f"[QuantumCoin] Buffered {len(self._buffer)} bits from quantum backend.")
        finally:
            self._fetching = False

    def _maybe_refill_async(self):
        if self._fetching:
            return
        t = threading.Thread(target=self._refill_buffer, daemon=True)
        t.start()

    def _run_hardware_counts(self, qc_t):
        """Submit to IBM hardware and return counts; may raise on timeout."""
        print(f"[QuantumCoin] Submitting hardware job with {self.shots} shots...")
        job = self.sampler.run([qc_t], shots=self.shots)
        print(f"[QuantumCoin] Submitted job ID: {job.job_id()}")
        try:
            result = job.result(timeout=self.hardware_timeout)
        except TypeError:
            raise RuntimeError("Hardware result() does not accept timeout; forcing fallback.")
        counts = result[0].data.meas.get_counts()
        print(f"[QuantumCoin] Raw hardware counts: {counts}")
        return counts

    def _run_aer_counts(self, qc_t):
        """Run the circuit on Aer and return counts."""
        print(f"[QuantumCoin] Running Aer simulation with {self.shots} shots...")
        job = self.aer_backend.run(qc_t, shots=self.shots)
        result = job.result()
        counts = result.get_counts()
        print(f"[QuantumCoin] Aer counts: {counts}")
        return counts

    def _next_bit(self) -> int:
        """Fetch next bit from buffer, refilling as needed; last resort is classical."""
        if self._buffer_index >= len(self._buffer):
            self._maybe_refill_async()

        if self._buffer_index >= len(self._buffer):
            bit = random.randint(0, 1)
            print(f"[QuantumCoin] Buffer empty, fallback classical bit: {bit}")
            return bit

        bit = self._buffer[self._buffer_index]
        self._buffer_index += 1
        remaining = len(self._buffer) - self._buffer_index
        print(f"[QuantumCoin] Quantum buffered bit: {bit} (remaining {remaining})")
        return bit

    def flip(self) -> int:
        """Public interface: return a single 0/1 coin flip."""
        return self._next_bit()
