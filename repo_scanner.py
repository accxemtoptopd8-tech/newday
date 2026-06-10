import os
from datetime import datetime

def build_llm_persona():
    return """<SYSTEM_ROLE>
Bạn là AI Architect tối cao, trợ lý chiến lược của Giám đốc hệ thống AI Business OS.
Nhiệm vụ của bạn là bảo trì, nâng cấp và mở rộng hệ thống này với tư duy: Rẻ nhất, Lì lợm nhất, và Thông minh nhất.

[KỶ LUẬT LÕI CỦA HỆ THỐNG]:
1. KHÔNG LÀM VỠ LUỒNG OUTBOX: Mọi giao tiếp giữa các module phải đi qua MongoDB Outbox Events. Không gọi API trực tiếp giữa các module.
2. TỐI ƯU QUOTA: Worker T2 chạy trên Github Actions phải luôn có công tắc `RUN_ONCE` để tự ngắt khi hết việc.
3. ĐA NGUỒN API: Luôn giữ thiết kế Trạm Lọc Máu (verify_and_save.py) để thích ứng với mọi loại API Key (OpenAI, Gemini, OpenRouter, DeepSeek DS2API).
</SYSTEM_ROLE>

"""

def generate_mega_gist(output_file="ai_os_master_context.md"):
    ignore_dirs = {'.git', '__pycache__', 'data', 'node_modules', '.github'}
    ignore_files = {'.env', 'repo_scanner.py', 'ai_os_master_context.md', 'requirements.txt'}
    
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write(build_llm_persona())
        out.write(f"<TIMESTAMP>Bản quét kiến trúc đồng bộ lúc: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</TIMESTAMP>\n\n")
        
        out.write("<PROJECT_MANIFESTO>\n")
        if os.path.exists("README.md"):
            with open("README.md", "r", encoding="utf-8") as f:
                out.write(f.read())
        out.write("\n</PROJECT_MANIFESTO>\n\n")
        
        out.write("<DIRECTORY_STRUCTURE>\n")
        for root, dirs, files in os.walk('.'):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            level = root.replace('.', '').count(os.sep)
            indent = ' ' * 4 * level
            out.write(f"{indent}{os.path.basename(root)}/\n")
            for f in files:
                if f not in ignore_files and (f.endswith('.py') or f.endswith('.json') or f.endswith('.md')):
                    out.write(f"{' ' * 4 * (level + 1)}{f}\n")
        out.write("</DIRECTORY_STRUCTURE>\n\n")
        
        out.write("<SOURCE_CODES>\n")
        for root, dirs, files in os.walk('.'):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                if file not in ignore_files and file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    out.write(f"\n# {'='*50}\n# FILE: {file_path}\n# {'='*50}\n")
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            out.write(f.read() + "\n")
                    except Exception as e:
                        out.write(f"# <Lỗi đọc cấu trúc file: {e}>\n")
        out.write("\n</SOURCE_CODES>\n")

if __name__ == "__main__":
    generate_mega_gist()
    print("🧠 [MASTER-CONTEXT] Đã đúc thành công tệp bối cảnh sạch!")
