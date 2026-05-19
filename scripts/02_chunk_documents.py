"""文本分块脚本：按文档类型策略分块，输出 chunks.json"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import TXT_DIR, CHUNKS_FILE

# 文件名 -> (doc_type, country)
DOC_META = {
    "赴英国犬猫检疫要求": ("country_export_req", "英国"),
    "赴日本犬猫检疫要求": ("country_export_req", "日本"),
    "赴美国犬检疫要求": ("country_export_req", "美国"),
    "赴欧盟犬猫检疫要求": ("country_export_req", "欧盟"),
    "中华人民共和国携带宠物入境检疫要求": ("entry_regulation", ""),
    "海关总署公告2019年第5号（关于进一步规范携带宠物入境检疫监管工作的公告）": ("entry_regulation", ""),
    "海关总署公告2019年第64号（关于更新携带入境宠物狂犬病抗体检测结果采信实验室名单的公告）": ("reference_list", ""),
    "海关总署采信狂犬病抗体检测结果的实验室名单": ("reference_list", ""),
    "具备进境宠物隔离检疫条件的口岸名单": ("reference_list", ""),
    "进境宠物隔离场地名单": ("reference_list", ""),
    "中华人民共和国海关进出境行李物品监管办法": ("legal_text", ""),
    "携带入境宠物（犬、猫）信息登记表": ("form_template", ""),
    "海关暂不予放行旅客行李物品暂存凭单": ("form_template", ""),
    "“携带出境宠物检疫”功能模块操作手册-申报端": ("operation_manual", ""),
}

MAX_LEN = 1500
MIN_LEN = 50


def get_doc_meta(filename: str) -> tuple[str, str]:
    """根据文件名匹配 doc_type 和 country"""
    name = filename.removesuffix(".txt").strip()
    for key, (doc_type, country) in DOC_META.items():
        if name.startswith(key) or key.startswith(name):
            return doc_type, country
    print(f"  [WARN] 未匹配文档类型: {name}")
    return "unknown", ""


def clean_text(text: str) -> str:
    """清理多余空白"""
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_by_paragraphs(text: str, doc_name: str, doc_type: str, country: str) -> list[dict]:
    """通用分块：按段落分割，过短的合并"""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""
    idx = 0

    for para in paragraphs:
        if len(current) + len(para) + 2 > MAX_LEN and len(current) >= MIN_LEN:
            chunks.append(make_chunk(current, doc_name, doc_type, country, idx))
            idx += 1
            current = para
        else:
            current = current + "\n\n" + para if current else para

    if current and len(current) >= MIN_LEN:
        chunks.append(make_chunk(current, doc_name, doc_type, country, idx))
    elif current and chunks:
        chunks[-1]["text"] += "\n\n" + current
    return chunks


def make_chunk(text: str, doc_name: str, doc_type: str, country: str, idx: int, section_title: str = "") -> dict:
    return {
        "text": clean_text(text),
        "doc_name": doc_name,
        "doc_type": doc_type,
        "country": country,
        "chunk_index": idx,
        "section_title": section_title,
    }


def chunk_country_export(text: str, doc_name: str, doc_type: str, country: str) -> list[dict]:
    """出境检疫要求：按条目分块（芯片/疫苗/血清等）"""
    lines = text.split("\n")
    # 找到第一个 • 开头的行
    start = 0
    header_lines = []
    for i, line in enumerate(lines):
        if line.strip().startswith("•") and not line.strip().startswith("•\t"):
            # 顶级条目（非子条目）
            if start == 0:
                start = i
        if start == 0:
            header_lines.append(line)

    header = "\n".join(header_lines).strip()

    # 按顶级条目分组
    sections = []
    current_title = ""
    current_lines = []

    for line in lines[start:]:
        stripped = line.strip()
        # 顶级条目：以 • 开头但不是 tab 缩进的子条目
        if stripped.startswith("•") and "\t" not in line.split("•")[0]:
            if current_lines:
                sections.append((current_title, current_lines))
            current_title = stripped.lstrip("•").strip()
            current_lines = [header, line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, current_lines))

    chunks = []
    for idx, (title, sec_lines) in enumerate(sections):
        chunk_text = "\n".join(sec_lines).strip()
        if len(chunk_text) < MIN_LEN and chunks:
            chunks[-1]["text"] += "\n\n" + chunk_text
        else:
            chunks.append(make_chunk(chunk_text, doc_name, doc_type, country, idx, title))
    return chunks


def chunk_entry_regulation(text: str, doc_name: str, doc_type: str, country: str) -> list[dict]:
    """入境法规：按中文序号分块（一、二、三 / （一）（二））"""
    # 按大节分割（一、二、三、四、五）
    sections = re.split(r"\n(?=[一二三四五六七八九十]+、)", text)

    chunks = []
    idx = 0
    for section in sections:
        section = section.strip()
        if not section:
            continue
        # 提取大节标题
        title_match = re.match(r"([一二三四五六七八九十]+、.+?)(?:\n|$)", section)
        section_title = title_match.group(1).strip() if title_match else ""

        # 如果大节过长，按小节分割（（一）（二）...）
        if len(section) > MAX_LEN:
            sub_sections = re.split(r"\n(?=（[一二三四五六七八九十]+）)", section)
            for sub in sub_sections:
                sub = sub.strip()
                if not sub:
                    continue
                sub_match = re.match(r"（[一二三四五六七八九十]+）", sub)
                sub_title = f"{section_title} {sub_match.group()}" if sub_match else section_title
                if len(sub) < MIN_LEN and chunks:
                    chunks[-1]["text"] += "\n\n" + sub
                else:
                    chunks.append(make_chunk(sub, doc_name, doc_type, country, idx, sub_title))
                    idx += 1
        else:
            chunks.append(make_chunk(section, doc_name, doc_type, country, idx, section_title))
            idx += 1
    return chunks


def chunk_reference_list_lab64(text: str, doc_name: str, doc_type: str, country: str) -> list[dict]:
    """64号公告实验室名单：按序号分组（每行是一个字段，需要重组）"""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    # 跳过开头标题行
    start = 0
    for i, line in enumerate(lines):
        if re.match(r"^\d+$", line):
            start = i
            break

    entries = []
    current_entry_lines = []
    for line in lines[start:]:
        if re.match(r"^\d+$", line) or line.startswith("Page"):
            if current_entry_lines:
                entries.append(current_entry_lines)
            current_entry_lines = []
        else:
            current_entry_lines.append(line)
    if current_entry_lines:
        entries.append(current_entry_lines)

    chunks = []
    for idx, entry_lines in enumerate(entries):
        # 格式：序号已经隐含，entry_lines[0]=国家, [1:]=实验室名称+地址
        if len(entry_lines) < 2:
            continue
        lab_country = entry_lines[0]
        rest = ", ".join(entry_lines[1:])
        chunk_text = f"{doc_name} - 第{idx + 1}条: 国家={lab_country}, 实验室={rest}"
        chunks.append(make_chunk(chunk_text, doc_name, doc_type, country, idx, f"第{idx + 1}条"))
    return chunks


def chunk_reference_list_designated(text: str, doc_name: str, doc_type: str, country: str) -> list[dict]:
    """采信实验室名单：类似64号公告但结构不同（10条，每条4个字段分行）"""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    # 跳过标题行，找到第一个序号
    start = 0
    for i, line in enumerate(lines):
        if re.match(r"^\d+$", line):
            start = i
            break

    entries = []
    current_lines = []
    for line in lines[start:]:
        if re.match(r"^\d+$", line) or line.startswith("Page"):
            if current_lines:
                entries.append(current_lines)
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        entries.append(current_lines)

    chunks = []
    for idx, entry_lines in enumerate(entries):
        if len(entry_lines) < 2:
            continue
        lab_country = entry_lines[0]
        rest = ", ".join(entry_lines[1:])
        chunk_text = f"{doc_name} - 第{idx + 1}条: 国家={lab_country}, 实验室={rest}"
        chunks.append(make_chunk(chunk_text, doc_name, doc_type, country, idx, f"第{idx + 1}条"))
    return chunks


def chunk_reference_list_port(text: str, doc_name: str, doc_type: str, country: str) -> list[dict]:
    """口岸名单：每两行为一条（口岸名称/机构名称）"""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    # 跳过标题
    start = 0
    for i, line in enumerate(lines):
        if "北京" in line or "上海" in line:
            start = i
            break

    chunks = []
    idx = 0
    i = start
    while i < len(lines):
        port_name = lines[i]
        org_name = lines[i + 1] if i + 1 < len(lines) else ""
        chunk_text = f"{doc_name} - 口岸: {port_name}, 海关机构: {org_name}"
        chunks.append(make_chunk(chunk_text, doc_name, doc_type, country, idx, port_name))
        idx += 1
        i += 2
    return chunks


def chunk_reference_list_isolation(text: str, doc_name: str, doc_type: str, country: str) -> list[dict]:
    """隔离场地名单：xls转换的tab分隔格式"""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    # 跳过标题行（Sheet1, 附件, 进境宠物隔离场地名单, 表头）
    chunks = []
    idx = 0
    for line in lines:
        if line.startswith("===") or "附件" in line or "进境宠物隔离场地名单" in line:
            continue
        if "序号" in line and "直属海关" in line:
            continue
        # 数据行：tab分隔
        fields = line.split("\t")
        if len(fields) >= 6:
            chunk_text = f"{doc_name} - 序号{fields[0]}: 直属海关={fields[1]}, 场地名称={fields[2]}, 地址={fields[3]}, 经营单位={fields[4]}, 进境口岸={fields[5]}, 宠物种类={fields[6] if len(fields) > 6 else ''}"
            chunks.append(make_chunk(chunk_text, doc_name, doc_type, country, idx, fields[2]))
            idx += 1
    return chunks


def chunk_legal_text(text: str, doc_name: str, doc_type: str, country: str) -> list[dict]:
    """法律法规：按条文分块（第X条），相关条文合并"""
    # 按章分割
    chapters = re.split(r"\n(?=第[一二三四五六七八九十]+章)", text)
    chunks = []
    idx = 0

    for chapter in chapters:
        chapter = chapter.strip()
        if not chapter:
            continue
        ch_match = re.match(r"(第[一二三四五六七八九十]+章\s+\S+)", chapter)
        ch_title = ch_match.group(1) if ch_match else ""

        # 按条分割
        articles = re.split(r"\n(?=第[一二三四五六七八九十百]+条\s)", chapter)
        current = ""
        for article in articles:
            article = article.strip()
            if not article:
                continue
            if len(current) + len(article) + 2 > MAX_LEN and len(current) >= MIN_LEN:
                chunks.append(make_chunk(current, doc_name, doc_type, country, idx, ch_title))
                idx += 1
                current = article
            else:
                current = current + "\n\n" + article if current else article
        if current and len(current) >= MIN_LEN:
            chunks.append(make_chunk(current, doc_name, doc_type, country, idx, ch_title))
            idx += 1
        elif current and chunks:
            chunks[-1]["text"] += "\n\n" + current
    return chunks


def chunk_form_template(text: str, doc_name: str, doc_type: str, country: str) -> list[dict]:
    """表单模板：分为表单字段描述和注意事项"""
    # 按区域分割
    sections = re.split(r"\n{2,}", text)
    chunks = []
    idx = 0
    current = ""
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
        if len(current) + len(sec) + 2 > MAX_LEN and len(current) >= MIN_LEN:
            chunks.append(make_chunk(current, doc_name, doc_type, country, idx))
            idx += 1
            current = sec
        else:
            current = current + "\n\n" + sec if current else sec
    if current and len(current) >= MIN_LEN:
        chunks.append(make_chunk(current, doc_name, doc_type, country, idx))
    elif current and chunks:
        chunks[-1]["text"] += "\n\n" + current
    return chunks


def chunk_operation_manual(text: str, doc_name: str, doc_type: str, country: str) -> list[dict]:
    """操作手册：按章节分块"""
    # 按篇/章节分割
    sections = re.split(r"\n(?=第[一二三四五六七八九十]+篇)", text)
    chunks = []
    idx = 0

    for section in sections:
        section = section.strip()
        if not section:
            continue
        # 进一步按小节分割
        sub_sections = re.split(r"\n(?=\d+\.\d+)", section)
        current = ""
        current_title = ""
        for sub in sub_sections:
            sub = sub.strip()
            if not sub:
                continue
            sub_match = re.match(r"(\d+\.\d+\s*.+?)(?:\n|$)", sub)
            sub_title = sub_match.group(1).strip() if sub_match else ""

            if len(current) + len(sub) + 2 > MAX_LEN and len(current) >= MIN_LEN:
                chunks.append(make_chunk(current, doc_name, doc_type, country, idx, current_title))
                idx += 1
                current = sub
                current_title = sub_title
            else:
                if not current_title:
                    current_title = sub_title
                current = current + "\n\n" + sub if current else sub

        if current and len(current) >= MIN_LEN:
            chunks.append(make_chunk(current, doc_name, doc_type, country, idx, current_title))
            idx += 1
        elif current and chunks:
            chunks[-1]["text"] += "\n\n" + current
    return chunks


def chunk_file(filepath: Path) -> list[dict]:
    """根据文档类型选择分块策略"""
    doc_name = filepath.stem.strip()
    doc_type, country = get_doc_meta(doc_name + ".txt")
    text = filepath.read_text(encoding="utf-8")
    text = clean_text(text)

    if doc_type == "country_export_req":
        return chunk_country_export(text, doc_name, doc_type, country)
    elif doc_type == "entry_regulation":
        return chunk_entry_regulation(text, doc_name, doc_type, country)
    elif doc_type == "reference_list":
        if "64号" in doc_name:
            return chunk_reference_list_lab64(text, doc_name, doc_type, country)
        elif "采信" in doc_name:
            return chunk_reference_list_designated(text, doc_name, doc_type, country)
        elif "口岸" in doc_name:
            return chunk_reference_list_port(text, doc_name, doc_type, country)
        elif "隔离场地" in doc_name:
            return chunk_reference_list_isolation(text, doc_name, doc_type, country)
        else:
            return chunk_by_paragraphs(text, doc_name, doc_type, country)
    elif doc_type == "legal_text":
        return chunk_legal_text(text, doc_name, doc_type, country)
    elif doc_type == "form_template":
        return chunk_form_template(text, doc_name, doc_type, country)
    elif doc_type == "operation_manual":
        return chunk_operation_manual(text, doc_name, doc_type, country)
    else:
        return chunk_by_paragraphs(text, doc_name, doc_type, country)


def main():
    txt_files = sorted(TXT_DIR.glob("*.txt"))
    print(f"共发现 {len(txt_files)} 个文本文件，开始分块...\n")

    all_chunks = []
    for f in txt_files:
        chunks = chunk_file(f)
        print(f"  {f.stem.strip()}: {len(chunks)} 个分块 ({get_doc_meta(f.name)[0]})")
        all_chunks.extend(chunks)

    CHUNKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHUNKS_FILE, "w", encoding="utf-8") as fp:
        json.dump(all_chunks, fp, ensure_ascii=False, indent=2)

    print(f"\n分块完成: 共 {len(all_chunks)} 个分块，已保存到 {CHUNKS_FILE}")

    # 统计
    type_counts = {}
    for c in all_chunks:
        t = c["doc_type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    print("\n各类型统计:")
    for t, count in sorted(type_counts.items()):
        print(f"  {t}: {count}")


if __name__ == "__main__":
    main()
