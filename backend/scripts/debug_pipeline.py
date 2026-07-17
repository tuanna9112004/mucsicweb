"""Chạy toàn bộ pipeline phân tích trên một file audio và in kết quả ra console.

Dùng để kiểm tra thủ công (không phải test tự động):
    python scripts/debug_pipeline.py <audio_path> [--mode piano_accurate] [--target-bpm 138]
        [--quantize 1/8] [--out-dir debug_output]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.pipeline import ingestion  # noqa: E402
from app.pipeline.pipeline import run_pipeline  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio_path", type=Path)
    parser.add_argument("--mode", type=str, default="piano_accurate", choices=["piano_accurate", "melody_quick"])
    parser.add_argument("--target-bpm", type=float, default=138)
    parser.add_argument("--keep-original-bpm", action="store_true")
    parser.add_argument(
        "--quantize", type=str, default="1/8", choices=["none", "1/4", "1/8", "1/16", "1/8T", "1/16T"]
    )
    parser.add_argument("--out-dir", type=Path, default=Path("debug_output"))
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    probe = ingestion.probe_audio(args.audio_path)
    target_bpm = None if args.keep_original_bpm else args.target_bpm

    result = run_pipeline(
        source_path=args.audio_path,
        work_dir=args.out_dir,
        original_filename=args.audio_path.name,
        analysis_mode=args.mode,
        target_bpm=target_bpm,
        quantize_mode=args.quantize,
        source_sample_rate=probe.sample_rate,
        source_channels=probe.channels,
    )

    a = result.analysis
    print(f"Mode: {a.metadata.analysis_mode}")
    print(f"Detected BPM: {a.rhythm.detected_bpm:.2f}")
    print(f"BPM candidates: {[(c.bpm, c.score) for c in a.rhythm.bpm_candidates]}")
    print(f"Time signature: {a.rhythm.time_signature} (confidence={a.rhythm.confidence})")
    print(f"Target BPM: {a.metadata.target_bpm}")
    print(f"Quantization: {a.metadata.quantization}")
    print(f"Key: {a.harmony.key} (relative: {a.harmony.relative_key}, confidence={a.harmony.confidence})")
    print(f"Chords: {len(a.harmony.chords)} spans")
    for c in a.harmony.chords[:20]:
        print(f"  {c.start_time_seconds:6.2f}-{c.end_time_seconds:6.2f}: {c.chord} (conf={c.confidence:.2f})")
    print()
    print("Quality report:", a.quality_report)
    print()
    for track in a.tracks:
        print(f"Track '{track.track_type}': {track.note_count} notes")
    print()
    print("Output files:")
    for file_type, path in result.output_files.items():
        print(f"  {file_type}: {path}")


if __name__ == "__main__":
    main()
