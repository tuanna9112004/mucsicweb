"""Sinh file WAV giai điệu tổng hợp để dùng làm fixture test (ground truth đã biết trước).

Chạy trực tiếp để (tái) tạo tests/fixtures/synth_melody_120bpm.wav:
    python tests/fixtures/generate_fixture.py
"""

from pathlib import Path

import numpy as np
import soundfile as sf

SAMPLE_RATE = 22050
BPM = 120
BEAT_DURATION_SECONDS = 60.0 / BPM  # 0.5s

# Envelope tạo attack rõ ràng (giống piano/guitar pluck) để librosa.beat.beat_track
# nhận diện được onset — một fade tuyến tính đơn thuần không tạo đủ transient.
ATTACK_SECONDS = 0.005
DECAY_SECONDS = 0.06
RELEASE_SECONDS = 0.04
SUSTAIN_LEVEL = 0.6
GAP_SECONDS = 0.02  # khoảng lặng ngắn cuối mỗi nốt để onset nốt kế tiếp rõ ràng

# (midi_number, start_beat, duration_beats) — thang âm lên rồi xuống, mỗi nốt 1 phách (quarter note)
NOTES = [
    (60, 0.0, 1.0),  # C4
    (62, 1.0, 1.0),  # D4
    (64, 2.0, 1.0),  # E4
    (65, 3.0, 1.0),  # F4
    (67, 4.0, 1.0),  # G4
    (65, 5.0, 1.0),  # F4
    (64, 6.0, 1.0),  # E4
    (62, 7.0, 1.0),  # D4
]

TOTAL_DURATION_SECONDS = 8 * BEAT_DURATION_SECONDS + 0.5


def midi_to_freq(midi_number: int) -> float:
    return 440.0 * (2.0 ** ((midi_number - 69) / 12.0))


def synth_note(freq: float, duration_seconds: float, sr: int = SAMPLE_RATE) -> np.ndarray:
    n_total = int(duration_seconds * sr)
    gap_n = int(GAP_SECONDS * sr)
    n_sound = max(n_total - gap_n, int(0.05 * sr))

    t = np.arange(n_sound) / sr
    wave = (
        np.sin(2 * np.pi * freq * t)
        + 0.3 * np.sin(2 * np.pi * freq * 2 * t)
        + 0.15 * np.sin(2 * np.pi * freq * 3 * t)
    )
    peak = np.max(np.abs(wave))
    if peak > 0:
        wave = wave / peak

    envelope = np.full(n_sound, SUSTAIN_LEVEL, dtype=np.float64)
    attack_n = min(int(ATTACK_SECONDS * sr), n_sound)
    envelope[:attack_n] = np.linspace(0, 1, attack_n)

    decay_n = min(int(DECAY_SECONDS * sr), n_sound - attack_n)
    if decay_n > 0:
        envelope[attack_n : attack_n + decay_n] = np.linspace(1, SUSTAIN_LEVEL, decay_n)

    release_n = min(int(RELEASE_SECONDS * sr), n_sound - attack_n - decay_n)
    if release_n > 0:
        envelope[-release_n:] = np.linspace(SUSTAIN_LEVEL, 0, release_n)

    wave *= envelope

    full = np.zeros(n_total, dtype=np.float32)
    full[:n_sound] = wave.astype(np.float32)
    return full


def generate() -> np.ndarray:
    total_samples = int(TOTAL_DURATION_SECONDS * SAMPLE_RATE)
    buffer = np.zeros(total_samples, dtype=np.float32)

    for midi_number, start_beat, duration_beats in NOTES:
        start_seconds = start_beat * BEAT_DURATION_SECONDS
        duration_seconds = duration_beats * BEAT_DURATION_SECONDS
        note_wave = synth_note(midi_to_freq(midi_number), duration_seconds)
        start_idx = int(start_seconds * SAMPLE_RATE)
        end_idx = start_idx + len(note_wave)
        buffer[start_idx:end_idx] += note_wave * 0.8

    peak = np.max(np.abs(buffer))
    if peak > 0:
        buffer = buffer / peak * 0.9

    # Một tín hiệu tổng hợp hoàn toàn "sạch" (không nhiễu) có onset-strength envelope
    # quá đều đặn, khiến thuật toán dynamic-programming của librosa.beat.beat_track bị
    # suy biến (không tìm được beat nào) — đã xác minh thực nghiệm. Thêm noise floor rất
    # nhỏ (mô phỏng noise nền của một bản thu thật) để tránh suy biến này.
    rng = np.random.default_rng(42)
    buffer = buffer + rng.normal(0, 0.005, size=buffer.shape).astype(np.float32)
    buffer = np.clip(buffer, -1.0, 1.0)

    return buffer


def main() -> None:
    out_path = Path(__file__).parent / "synth_melody_120bpm.wav"
    audio = generate()
    sf.write(str(out_path), audio, SAMPLE_RATE, subtype="PCM_16")
    print(f"Wrote {out_path} ({len(audio) / SAMPLE_RATE:.2f}s)")


if __name__ == "__main__":
    main()
