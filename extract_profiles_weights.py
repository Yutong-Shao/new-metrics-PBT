import os
import re
import sys

def extract_fmix_from_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fmix_entries = []
    capture_fmix = False
    rate_model = ""
    rate_values = []

    for idx, line in enumerate(lines):
        # ----------- 提取 FMIX -------------
        if re.match(r"\s*No\s+Component\s+Rate\s+Weight\s+Parameters", line):
            capture_fmix = True
            continue
        if capture_fmix:
            if not line.strip() or not re.search(r'\d', line):
                capture_fmix = False
                continue
            parts = line.strip().split()
            if len(parts) >= 4:
                component = parts[1]
                weight = parts[3]
                profile_match = re.search(r'F(.+)', component)
                if profile_match:
                    profile = profile_match.group(1)
                    fmix_entries.append(f"{profile}:1.0:{weight}")

        # ----------- 提取 R 模型信息 -------------
        if line.startswith("Model of rate heterogeneity:"):
            if "FreeRate" in line:
                match_r = re.search(r'FreeRate with (\d+) categories', line)
                if match_r:
                    r_num = match_r.group(1)
                    rate_model = f"R{r_num}"
                    # 下一行通常是 rate 值，读取并解析
                    if idx + 1 < len(lines) and lines[idx + 1].startswith("Site proportion and rates:"):
                        rate_line = lines[idx + 1]
                        numbers = re.findall(r"[\d.]+", rate_line)
                        rate_values = numbers

    # 组合 FMIX 和 R 结果
    result_parts = []
    if fmix_entries:
        result_parts.append("FMIX{" + ",".join(fmix_entries) + "}")
    if rate_model and rate_values:
        result_parts.append(f"{rate_model}{{" + ",".join(rate_values) + "}}")

    return "+".join(result_parts) if result_parts else None

def main():
    if len(sys.argv) != 2:
        print("Usage: python extract_profiles_weights.py <input_directory>")
        sys.exit(1)

    input_dir = sys.argv[1]

    if not os.path.isdir(input_dir):
        print(f"Error: {input_dir} is not a valid directory.")
        sys.exit(1)

    iqtree_files = [f for f in os.listdir(input_dir) if f.endswith(".iqtree")]
    output_files = []

    for iqfile in iqtree_files:
        full_path = os.path.join(input_dir, iqfile)
        fmix_result = extract_fmix_from_file(full_path)
        if fmix_result:
            prefix = os.path.splitext(iqfile)[0]
            out_path = os.path.join(input_dir, f"{prefix}.txt")
            with open(out_path, 'w', encoding='utf-8') as f_out:
                f_out.write(fmix_result + "\n")
            output_files.append(out_path)

    print(f"Done. {len(output_files)} FMIX profiles extracted.")

if __name__ == "__main__":
    main()
