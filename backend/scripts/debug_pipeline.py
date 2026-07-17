"""Chạy toàn bộ pipeline phân tích trên một file audio và in kết quả ra console.

Dùng để kiểm tra thủ công (không phải test tự động):
    python scripts/debug_pipeline.py <audio_path> [--target-bpm 138] [--quantize 1/8] [--out-dir debug_output]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.pipeline.pipeline import run_pipeline  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio_path", type=Path)
    parser.add_argument("--target-bpm", type=int, default=138)
    parser.add_argument("--quantize", type=str, default="1/8", choices=["none", "1/4", "1/8", "1/16"])
    parser.add_argument("--out-dir", type=Path, default=Path("debug_output"))
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    result = run_pipeline(
        source_path=args.audio_path,
        work_dir=args.out_dir,
        original_filename=args.audio_path.name,
        target_bpm=args.target_bpm,
        quantize_mode=args.quantize,
    )

    print(f"Detected BPM: {result.analysis.detected_bpm:.2f}")
    print(f"Target BPM: {result.analysis.target_bpm}")
    print(f"Quantization: {result.analysis.quantization}")
    print(f"Note count: {result.analysis.note_count}")
    print(f"MIDI written to: {result.midi_path}")
    print(f"JSON written to: {result.json_path}")
    print()
    for note in result.analysis.notes:
        print(
            f"  {note.note:>4} (midi={note.midi_number:3d}) "
            f"start={note.start_time_seconds:6.2f}s dur={note.duration_seconds:5.2f}s "
            f"beat={note.start_beat:5.2f} conf={note.confidence:.2f}"
        )


if __name__ == "__main__":
    main()
