"""文档转换脚本：将 .doc/.docx/.xls 转为 .txt"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DOCS_DIR, TXT_DIR

import xlrd


def convert_doc_docx(filepath: Path, output_dir: Path) -> Path | None:
    """用 macOS textutil 转换 doc/docx"""
    out_name = filepath.stem.strip() + ".txt"
    out_path = output_dir / out_name
    try:
        subprocess.run(
            ["textutil", "-convert", "txt", "-output", str(out_path), str(filepath)],
            check=True,
            capture_output=True,
        )
        print(f"  [OK] {filepath.name} -> {out_name}")
        return out_path
    except subprocess.CalledProcessError as e:
        print(f"  [FAIL] {filepath.name}: {e.stderr.decode()}")
        return None


def convert_xls(filepath: Path, output_dir: Path) -> Path | None:
    """用 xlrd 读取 xls 转为文本"""
    out_name = filepath.stem.strip() + ".txt"
    out_path = output_dir / out_name
    try:
        workbook = xlrd.open_workbook(str(filepath))
        lines = []
        for sheet in workbook.sheets():
            lines.append(f"=== {sheet.name} ===")
            for row_idx in range(sheet.nrows):
                cells = [str(sheet.cell_value(row_idx, col_idx)).strip()
                         for col_idx in range(sheet.ncols)]
                lines.append("\t".join(cells))
        out_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"  [OK] {filepath.name} -> {out_name}")
        return out_path
    except Exception as e:
        print(f"  [FAIL] {filepath.name}: {e}")
        return None


def main():
    TXT_DIR.mkdir(parents=True, exist_ok=True)
    docs = list(DOCS_DIR.iterdir())
    print(f"共发现 {len(docs)} 个文件，开始转换...\n")

    converted = 0
    for f in sorted(docs):
        if f.name.startswith("."):
            continue
        ext = f.suffix.lower()
        if ext in (".doc", ".docx"):
            if convert_doc_docx(f, TXT_DIR):
                converted += 1
        elif ext == ".xls":
            if convert_xls(f, TXT_DIR):
                converted += 1
        else:
            print(f"  [SKIP] {f.name} (不支持的格式)")

    print(f"\n转换完成: {converted}/{len(docs)} 个文件")


if __name__ == "__main__":
    main()
