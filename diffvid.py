import os
import subprocess
import re

LOG_FILE = "videolog.txt"

def get_base_name(path_str):
    """Xóa bỏ dấu ngoặc, lấy tên file và loại bỏ ĐUÔI FILE (extension)"""
    clean_path = path_str.strip().strip('"').strip("'")
    base_name = os.path.splitext(os.path.basename(clean_path))[0]
    return base_name

def parse_log():
    """Đọc file log và trả về dictionary: {tên_file_khong_duoi: (vmaf, ssim, psnr)}"""
    log_data = {}
    if not os.path.exists(LOG_FILE):
        return log_data
    
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            parts = line.strip().split('|')
            if len(parts) >= 4:
                filename = parts[0].strip()
                vmaf = float(parts[1].strip())
                ssim = float(parts[2].strip())
                psnr_str = parts[3].strip().lower()
                psnr = float('inf') if 'inf' in psnr_str else float(psnr_str)
                log_data[filename] = (vmaf, ssim, psnr)
    return log_data

def save_to_log(filename, vmaf, ssim, psnr):
    """Lưu kết quả mới vào log"""
    psnr_val = "inf" if psnr == float('inf') else f"{psnr:.2f}"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{filename} | {vmaf:.2f} | {ssim:.4f} | {psnr_val}\n")

def calculate_metrics(original_path, compressed_path):
    """ĐO CHẤT LƯỢNG THẬT BẰNG FFMPEG"""
    
    filter_complex = (
        "[0:v]split=3[dist1][dist2][dist3]; "
        "[1:v]split=3[ref1][ref2][ref3]; "
        "[dist1][ref1]psnr; "
        "[dist2][ref2]ssim; "
        "[dist3][ref3]libvmaf"
    )
    
    cmd = [
        'ffmpeg', 
        '-i', compressed_path, 
        '-i', original_path,
        '-lavfi', filter_complex,
        '-f', 'null', '-'
    ]
    
    try:
        process = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding='utf-8')
        output = process.stderr
        
        vmaf, ssim, psnr = 0.0, 0.0, 0.0
        
        vmaf_match = re.search(r'VMAF score: ([0-9.]+)', output)
        if vmaf_match:
            vmaf = float(vmaf_match.group(1))
            
        ssim_match = re.search(r'SSIM.*All:([0-9.]+)', output)
        if ssim_match:
            ssim = float(ssim_match.group(1)) * 100
            
        psnr_match = re.search(r'PSNR.*average:(inf|[0-9.]+)', output)
        if psnr_match:
            psnr_str = psnr_match.group(1)
            psnr = float('inf') if 'inf' in psnr_str.lower() else float(psnr_str)
            
        return vmaf, ssim, psnr

    except FileNotFoundError:
        print("\n[LỖI]: Không tìm thấy ứng dụng FFmpeg. Vui lòng đảm bảo FFmpeg đã được cài và thêm vào biến môi trường PATH của máy tính.")
        return 0.0, 0.0, 0.0
    except Exception as e:
        print(f"\n[LỖI KHI ĐO VIDEO]: {e}")
        return 0.0, 0.0, 0.0

def role_1_calculate():
    print("\n=== VAI TRÒ 1: NHẬP VÀ TÍNH ĐIỂM ===")
    orig_input = input("1. Kéo thả file video GỐC vào đây: ")
    orig_path = orig_input.strip().strip('"').strip("'")
    
    if not os.path.exists(orig_path):
        print("Lỗi: Không tìm thấy file gốc!")
        return

    comp_paths = []
    print("\n2. Kéo thả lần lượt các file video NÉN vào đây.")
    print("   (Nhập phím 'P' hoặc 'p' và nhấn Enter để BẮT ĐẦU TÍNH TOÁN)")
    
    while True:
        comp_input = input(f"   - File nén {len(comp_paths)+1} (hoặc 'P'): ")
        comp_path_clean = comp_input.strip().strip('"').strip("'")
        
        if comp_path_clean.lower() == 'p':
            break
            
        if os.path.exists(comp_path_clean):
            comp_paths.append(comp_path_clean)
        else:
            print("   -> Lỗi: Không tìm thấy file này, vui lòng nhập lại!")

    if not comp_paths:
        print("Không có file nén nào để tính toán. Trở về menu chính.")
        return

    existing_logs = parse_log()
    
    print("\n=== BẮT ĐẦU QUÁ TRÌNH TÍNH TOÁN ===")
    for path in comp_paths:
        basename = get_base_name(path)
        
        if basename in existing_logs:
            print(f"[-] Bỏ qua '{basename}': Đã có dữ liệu trong videolog.txt")
            continue
            
        print(f"[Đang tính toán] Đang chạy phân tích cho: {basename} ... (Vui lòng đợi vài phút)")
        vmaf, ssim, psnr = calculate_metrics(orig_path, path)
        
        save_to_log(basename, vmaf, ssim, psnr)
        print(f"[Hoàn thành] Đã lưu kết quả cho: {basename}")
    
    print("\n=> Đã hoàn thành tính toán tất cả video!")

def show_table(log_data, sort_by_index, metric_name):
    """Hàm in bảng dựa theo tiêu chí sắp xếp"""
    sorted_items = sorted(
        log_data.items(), 
        key=lambda item: item[1][sort_by_index], 
        reverse=True
    )

    print(f"\n=== BẢNG XẾP HẠNG (ƯU TIÊN: {metric_name}) ===")
    print(f"{'HẠNG':<5} | {'TÊN FILE CLIP':<35} | {'VMAF':<8} | {'SSIM':<8} | {'PSNR':<8}")
    print("-" * 75)
    
    for rank, (basename, (vmaf, ssim, psnr)) in enumerate(sorted_items, start=1):
        display_name = f"{basename}*" if psnr == float('inf') else basename
        psnr_str = "inf" if psnr == float('inf') else f"{psnr:.2f}"
        
        print(f"#{rank:<3} | {display_name:<35} | {vmaf:<8.2f} | {ssim:<8.4f} | {psnr_str:<8}")
    
    print("-" * 75)
    print("Ghi chú: Dấu (*) biểu thị video y hệt gốc (Lossless / PSNR = inf)\n")

def role_2_leaderboard():
    log_data = parse_log()
    if not log_data:
        print("\nFile log trống. Chưa có video nào được đánh giá.")
        return

    while True:
        print("\n=== TÙY CHỌN BẢNG XẾP HẠNG ===")
        print("1. Xếp bảng so sánh theo VMAF")
        print("2. Xếp bảng so sánh theo SSIM")
        print("3. Xếp bảng so sánh theo PSNR")
        print("4. Quay về menu chính")
        
        choice = input("Nhập lựa chọn của bạn (1/2/3/4): ").strip()
        
        if choice == '1':
            show_table(log_data, sort_by_index=0, metric_name="VMAF")
        elif choice == '2':
            show_table(log_data, sort_by_index=1, metric_name="SSIM")
        elif choice == '3':
            show_table(log_data, sort_by_index=2, metric_name="PSNR")
        elif choice == '4':
            break
        else:
            print("Lựa chọn không hợp lệ!")

def role_4_download():
    """Tải video từ YouTube/web bằng yt-dlp ở chất lượng 1080p tốt nhất"""
    print("\n=== VAI TRÒ 4: TẢI VIDEO BẰNG YT-DLP ===")
    print("Định dạng: 1080p tốt nhất, ghép thành file .mkv")
    print("(Nhập 'Q' hoặc 'q' để quay về menu chính)\n")

    # Xác định đường dẫn yt-dlp: ưu tiên file .exe cùng thư mục, fallback sang PATH
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ytdlp_local = os.path.join(script_dir, "yt-dlp.exe")
    ytdlp_cmd = ytdlp_local if os.path.exists(ytdlp_local) else "yt-dlp"

    while True:
        url_input = input("Nhập URL video (hoặc 'Q' để quay về): ").strip()

        if url_input.lower() == 'q':
            print("Quay về menu chính.")
            break

        if not url_input:
            print("   -> URL không được để trống, vui lòng nhập lại!")
            continue

        cmd = [
            ytdlp_cmd,
            "-f", "bestvideo+bestaudio/best",
            "--merge-output-format", "mkv",
            "--postprocessor-args", "ffmpeg:-c:v copy -c:a aac",  # giữ nguyên video, chỉ đổi audio
            "-o", "%(title)s [%(id)s].%(ext)s",
            url_input
        ]

        print(f"\n[Đang tải] Bắt đầu tải: {url_input}")
        print("(Tiến trình tải sẽ hiển thị bên dưới — vui lòng đợi...)\n")

        try:
            # Chạy yt-dlp và in output trực tiếp ra màn hình theo thời gian thực
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
            for line in process.stdout:
                print(line, end='')
            process.wait()

            if process.returncode == 0:
                print("\n[Hoàn thành] Tải video thành công!")
            else:
                print(f"\n[LỖI] yt-dlp kết thúc với mã lỗi: {process.returncode}")

        except FileNotFoundError:
            print(f"\n[LỖI]: Không tìm thấy yt-dlp.")
            print(f"  - Đặt file 'yt-dlp.exe' vào cùng thư mục với script này: {script_dir}")
            print(f"  - Hoặc thêm yt-dlp vào biến môi trường PATH của hệ thống.")
        except Exception as e:
            print(f"\n[LỖI KHI TẢI]: {e}")

        print()

def main():
    while True:
        print("\n" + "="*40)
        print("   CÔNG CỤ SO SÁNH CHẤT LƯỢNG VIDEO")
        print("="*40)
        print("1. Vai trò 1: Nhập clip và tính điểm")
        print("2. Vai trò 2: Xem bảng xếp hạng (Tốt -> Kém)")
        print("3. Thoát chương trình")
        print("4. Vai trò 4: Tải video bằng yt-dlp (1080p)")
        
        choice = input("\nNhập lựa chọn của bạn (1/2/3/4): ").strip()
        
        if choice == '1':
            role_1_calculate()
        elif choice == '2':
            role_2_leaderboard()
        elif choice == '3':
            print("Đã thoát chương trình.")
            break
        elif choice == '4':
            role_4_download()
        else:
            print("Lựa chọn không hợp lệ. Vui lòng nhập lại.")

if __name__ == "__main__":
    main()