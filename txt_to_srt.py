"""
txt_to_srt.py
-------------
Gộp nhiều part transcript (định dạng [MM:SS] text) thành một file .srt duy nhất.

Cách dùng:
    python txt_to_srt.py input.txt output.srt

Khi chạy, script sẽ hỏi cut-points từ ffmpeg (ví dụ: 00:36:15).
Nhấn Enter không nhập = đây là part cuối (kéo đến hết clip).

Quy tắc tách part:
    - Dòng có 3+ dấu gạch ngang liên tiếp (---) → part mới
    - Hoặc timeline bị reset về [00:00] so với dòng trước → part mới
"""

import re
import sys
from pathlib import Path


# ─── Helpers ──────────────────────────────────────────────────────────────────

def parse_timestamp(ts: str) -> int:
    """'MM:SS' hoặc 'HH:MM:SS' → tổng số giây (int)."""
    parts = ts.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    raise ValueError(f"Timestamp không hợp lệ: {ts}")


def seconds_to_srt(secs: float) -> str:
    """Tổng giây → 'HH:MM:SS,mmm' (SRT format, milliseconds = 000)."""
    secs = int(secs)
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    return f"{h:02}:{m:02}:{s:02},000"


def is_separator(line: str) -> bool:
    """Dòng có từ 3 dấu gạch ngang trở lên → True."""
    stripped = line.strip()
    return bool(re.match(r"^-{3,}$", stripped))


ENTRY_RE = re.compile(r"^\[(\d{1,2}:\d{2})\]\s*(.*)")


def is_entry(line: str):
    """Trả về (timestamp_str, text) nếu là entry, ngược lại None."""
    m = ENTRY_RE.match(line.strip())
    if m:
        return m.group(1), m.group(2).strip()
    return None


# ─── Đọc & tách part ──────────────────────────────────────────────────────────

def split_into_parts(raw_text: str):
    """
    Trả về list of list-of-(mm_ss_seconds, text).
    Tách part dựa trên:
      1. Dòng separator (---+)
      2. Timeline reset về 00:00 (giây = 0) sau khi đã có entry
    """
    parts = []
    current_part = []
    prev_secs = -1

    for line in raw_text.splitlines():
        if is_separator(line):
            if current_part:
                parts.append(current_part)
                current_part = []
            prev_secs = -1
            continue

        entry = is_entry(line)
        if entry:
            ts_str, text = entry
            secs = parse_timestamp(ts_str)

            # Detect reset: timeline về 0 sau khi đã có entry trong part hiện tại
            if secs == 0 and prev_secs > 0 and current_part:
                parts.append(current_part)
                current_part = []

            current_part.append((secs, text))
            prev_secs = secs
        # Bỏ qua dòng trắng hoặc dòng không phải entry

    if current_part:
        parts.append(current_part)

    return parts


# ─── Hỏi cut-points ───────────────────────────────────────────────────────────

def ask_cut_points(num_parts: int) -> list:
    """
    Hỏi người dùng nhập cut-point (HH:MM:SS) cho từng part.
    Part cuối → Enter trống → None (dùng +30s cho entry cuối).
    Trả về list độ dài num_parts, phần tử là giây (int) hoặc None.
    """
    print(f"\nĐã phát hiện {num_parts} part.\n")
    print("Nhập cut-point ffmpeg cho từng part (ví dụ: 00:36:15).")
    print("Với part cuối, nhấn Enter để tự động +30s cho entry cuối.\n")

    cuts = []
    for i in range(num_parts):
        while True:
            raw = input(f"  Cut-point kết thúc của Part {i+1}: ").strip()
            if raw == "":
                cuts.append(None)
                break
            try:
                cuts.append(parse_timestamp(raw))
                break
            except ValueError:
                print("  ⚠ Định dạng sai. Dùng MM:SS hoặc HH:MM:SS.")

    return cuts


# ─── Build SRT ────────────────────────────────────────────────────────────────

def build_srt(parts: list, cuts: list) -> str:
    """
    parts  : list of list-of-(offset_secs, text)
    cuts   : list of int-or-None, cùng độ dài với parts

    Mỗi part có offset = tổng cut-points của các part trước.
    Timeline cuối entry = timeline entry kế / cut-point / +30s.
    """
    lines = []
    entry_idx = 1        # số thứ tự SRT toàn cục
    global_offset = 0    # giây cộng dồn

    for part_i, (entries, cut) in enumerate(zip(parts, cuts)):
        for j, (rel_secs, text) in enumerate(entries):
            abs_start = global_offset + rel_secs

            # Xác định abs_end
            if j + 1 < len(entries):
                # Entry kế tiếp trong cùng part
                abs_end = global_offset + entries[j + 1][0]
            else:
                # Entry cuối của part
                if cut is not None:
                    # cut là timestamp tuyệt đối (đã parse từ HH:MM:SS của ffmpeg)
                    abs_end = cut
                    # Nếu cut <= abs_start (lạ), fallback +30s
                    if abs_end <= abs_start:
                        abs_end = abs_start + 30
                else:
                    abs_end = abs_start + 30

            lines.append(str(entry_idx))
            lines.append(f"{seconds_to_srt(abs_start)} --> {seconds_to_srt(abs_end)}")
            lines.append(text)
            lines.append("")
            entry_idx += 1

        # Cập nhật offset cho part tiếp theo
        if cut is not None:
            global_offset = cut   # cut đã là tuyệt đối
        elif entries:
            # Part cuối: offset tăng thêm timestamp cuối + 30s
            global_offset += entries[-1][0] + 30

    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print("Cách dùng: python txt_to_srt.py <input.txt> <output.srt>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        print(f"❌ Không tìm thấy file: {input_path}")
        sys.exit(1)

    raw_text = input_path.read_text(encoding="utf-8")
    parts = split_into_parts(raw_text)

    if not parts:
        print("❌ Không tìm thấy entry nào trong file. Kiểm tra định dạng [MM:SS].")
        sys.exit(1)

    cuts = ask_cut_points(len(parts))
    srt_content = build_srt(parts, cuts)

    output_path.write_text(srt_content, encoding="utf-8")
    print(f"\n✅ Đã xuất: {output_path}  ({entry_count(srt_content)} entries)")


def entry_count(srt: str) -> int:
    return sum(1 for l in srt.splitlines() if l.strip().isdigit())


if __name__ == "__main__":
    main()