import os
import sys
import numpy as np
import librosa
from resemblyzer import VoiceEncoder, preprocess_wav
from pathlib import Path


def load_audio(path):
    """Hỗ trợ load nhiều định dạng bao gồm cả .ogg bằng librosa"""
    try:
        wav, sr = librosa.load(path, sr=16000)
        return preprocess_wav(wav)
    except Exception as e:
        print(f"  Lỗi khi load tệp {path}: {e}")
        return None


def run_analysis(encoder, source_embed, target_folder):
    """Quét thư mục và tính độ tương đồng với tệp gốc"""
    target_paths = [
        os.path.join(target_folder, f)
        for f in sorted(os.listdir(target_folder))
        if f.lower().endswith(('.ogg', '.wav', '.mp3'))
    ]

    if not target_paths:
        print("  Không tìm thấy tệp âm thanh nào trong thư mục.")
        return

    print(f"\n  Đang phân tích {len(target_paths)} tệp...")
    print("-" * 50)

    similarities = []
    for path in target_paths:
        target_wav = load_audio(path)
        if target_wav is None:
            continue

        target_embed = encoder.embed_utterance(target_wav)
        similarity = np.dot(source_embed, target_embed) / (
            np.linalg.norm(source_embed) * np.linalg.norm(target_embed)
        )
        similarities.append(similarity)
        print(f"  - {os.path.basename(path)}: {similarity:.4f}")

    if similarities:
        mean_score = np.mean(similarities)
        std_dev = np.std(similarities)

        print("-" * 50)
        print(f"  KẾT QUẢ TRUNG BÌNH : {mean_score:.4f}")
        print(f"  ĐỘ BIẾN THIÊN (STD) : {std_dev:.4f}")

        if mean_score > 0.85:
            print("  Đánh giá: Giọng cực kỳ khớp với bản gốc!")
        elif mean_score > 0.75:
            print("  Đánh giá: Độ tương đồng tốt.")
        else:
            print("  Đánh giá: Có sự khác biệt rõ rệt.")

    print("=" * 50)


def main():
    # Khởi tạo mô hình (chỉ load 1 lần để tiết kiệm tài nguyên)
    print("\n--- Đang khởi động mô hình Resemblyzer (AI Encoder)... ---")
    try:
        encoder = VoiceEncoder()
    except Exception as e:
        print(f"  Lỗi khởi tạo Encoder: {e}")
        input("\nNhấn Enter để thoát...")
        return

    print("=" * 50)
    print("  HỆ THỐNG ĐÁNH GIÁ ĐỘ TƯƠNG ĐỒNG GIỌNG NÓI (CLI)")
    print("=" * 50)

    # ── Nhập tệp gốc (chỉ hỏi 1 lần) ──────────────────────────────
    while True:
        source_path = input("\nNhập đường dẫn tệp GỐC (ogg/wav/mp3): ").strip().strip('"')
        if os.path.exists(source_path):
            break
        print("  Tệp gốc không tồn tại, vui lòng nhập lại.")

    source_wav = load_audio(source_path)
    if source_wav is None:
        input("\nNhấn Enter để thoát...")
        return
    source_embed = encoder.embed_utterance(source_wav)
    print(f"  ✔ Tệp gốc đã load: {os.path.basename(source_path)}")

    # ── Nhập thư mục chứa tệp AI (chỉ hỏi 1 lần) ──────────────────
    while True:
        target_folder = input("\nNhập đường dẫn THƯ MỤC chứa các tệp AI: ").strip().strip('"')
        if os.path.isdir(target_folder):
            break
        print("  Thư mục không tồn tại, vui lòng nhập lại.")

    print(f"  ✔ Thư mục mẫu  : {target_folder}")

    # ── Vòng lặp phân tích ─────────────────────────────────────────
    round_num = 1
    while True:
        print(f"\n{'='*50}")
        print(f"  LẦN ĐO THỨ {round_num}")
        print(f"{'='*50}")

        run_analysis(encoder, source_embed, target_folder)

        # Hỏi tiếp tục hay thoát
        choice = input(
            "\n  Nhấn ENTER để đo tiếp  |  Nhấn Q rồi Enter để thoát: "
        ).strip().lower()

        if choice == 'q':
            print("\n  Đã kết thúc. Tạm biệt!")
            break

        round_num += 1


if __name__ == "__main__":
    main()