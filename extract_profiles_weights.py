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
    inv_proportion = None
    gamma_shape = None

    for idx, line in enumerate(lines):
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
                profile_match = re.search(r'\+F(.+)', component)
                if profile_match:
                    profile = profile_match.group(1)
                    fmix_entries.append(f"{profile}:1.0:{weight}")

        if line.startswith("Proportion of invariable sites:"):
            inv_match = re.search(r'Proportion of invariable sites:\s*([\d.]+)', line)
            if inv_match:
                inv_proportion = inv_match.group(1)

        if line.startswith("Gamma shape alpha:"):
            gamma_match = re.search(r'Gamma shape alpha:\s*([\d.]+)', line)
            if gamma_match:
                gamma_shape = gamma_match.group(1)

        if line.startswith("Model of rate heterogeneity:"):
            if "FreeRate" in line:
                match_r = re.search(r'FreeRate with (\d+) categories', line)
                if match_r:
                    r_num = match_r.group(1)
                    rate_model = f"R{r_num}"

        if line.startswith("Site proportion and rates:"):
            numbers = re.findall(r"[\d.]+", line)
            rate_values = numbers

    fmix_part = "FMIX{" + ",".join(fmix_entries) + "}" if fmix_entries else ""
    i_part = f"I{{{inv_proportion}}}" if inv_proportion else ""
    r_part = f"{rate_model}{{{','.join(rate_values)}}}" if rate_model and rate_values else ""
    g4_part = f"G4{{{gamma_shape}}}" if gamma_shape else ""

    return fmix_part, i_part, r_part, g4_part


def extract_prefix(iqtree_filename):
    match = re.match(r"([A-Za-z0-9]+)[_-]", iqtree_filename)
    return match.group(1) if match else "Model"


def parse_profiles_from_fmix(fmix_string):
    match = re.search(r'FMIX\{(.+?)\}', fmix_string)
    if not match:
        return []
    entries = match.group(1).split(',')
    profiles = [entry.split(':')[0] for entry in entries]
    return profiles


def read_frequency_lines(freq_file, profile_list):
    with open(freq_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    freq_lines = []
    for profile in profile_list:
        for line in lines:
            if re.match(rf'\s*frequency\s+{re.escape(profile)}\s*=', line):
                freq_lines.append(line.strip())
                break
    return freq_lines


def extract_model_block(freq_file, model_name):
    with open(freq_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    model_block = []
    capture = False
    for line in lines:
        if not capture:
            if re.match(rf'\s*model\s+{re.escape(model_name)}\s*=', line):
                capture = True
                model_block.append(line.rstrip())
        elif capture:
            model_block.append(line.rstrip())
            if ";" in line:
                break

    return model_block


def extract_main_model(fmix_string):
    match = re.match(r'([A-Za-z0-9]+)\+', fmix_string)
    return match.group(1) if match else None


def main():
    if len(sys.argv) not in [2, 3]:
        print("Usage:\n  python extract_profiles_weights.py <input_directory>\n"
              "  or\n  python extract_profiles_weights.py <input_directory> <nex_file_with_frequencies>")
        sys.exit(1)

    input_dir = sys.argv[1]
    extra_nex_path = sys.argv[2] if len(sys.argv) == 3 else None

    if not os.path.isdir(input_dir):
        print(f"Error: {input_dir} is not a valid directory.")
        sys.exit(1)

    if extra_nex_path and not os.path.isfile(extra_nex_path):
        print(f"Error: {extra_nex_path} is not a valid .nex file.")
        sys.exit(1)

    iqtree_files = [f for f in os.listdir(input_dir) if f.endswith(".iqtree")]
    output_files = []

    for iqfile in iqtree_files:
        full_path = os.path.join(input_dir, iqfile)
        fmix_part, i_part, r_part, g4_part = extract_fmix_from_file(full_path)

        if fmix_part:
            file_prefix = os.path.splitext(iqfile)[0]
            model_prefix = extract_prefix(iqfile)

            content_parts = [f"{model_prefix}+{fmix_part}"]
            if i_part:
                content_parts.append(i_part)
            if r_part:
                content_parts.append(r_part)
            if g4_part:
                content_parts.append(g4_part)

            final_string = "+".join(content_parts)
            out_path = os.path.join(input_dir, f"{file_prefix}.nex")

            freq_lines = []
            model_block_lines = []

            if extra_nex_path:
                profile_list = parse_profiles_from_fmix(fmix_part)
                freq_lines = read_frequency_lines(extra_nex_path, profile_list)

                main_model_name = extract_main_model(final_string)
                if main_model_name:
                    model_block_lines = extract_model_block(extra_nex_path, main_model_name)

            with open(out_path, 'w', encoding='utf-8', newline='\r\n') as f_out:
                f_out.write("#nexus\n")
                f_out.write("begin models;\n\n")

                for line in model_block_lines:
                    f_out.write(line + "\n")
                f_out.write("\n")

                for line in freq_lines:
                    f_out.write(line + "\n")
                f_out.write("\n")

                f_out.write(f"model OPT = {final_string};\n\n")
                f_out.write("end;\n")

            output_files.append(out_path)

    print(f"Done. {len(output_files)} .nex profiles generated.")


if __name__ == "__main__":
    main()