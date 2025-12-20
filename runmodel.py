import re
import subprocess
import argparse
from pathlib import Path


# =============================================================
# HELPER FUNCTIONS
# =============================================================

# Global variable to store log file path
LOG_FILE = None

def run_command(cmd, skip_if_output_exists=False, output_folder=None):
    """
    Run a command with optional check for existing output.
    
    Args:
        cmd: Command list to execute
        skip_if_output_exists: If True, skip command if output_folder exists and is not empty
        output_folder: Path to check for existing output (only used if skip_if_output_exists=True)
    """
    cmd = list(map(str, cmd))  # Prevent int / Path join issues
    cmd_str = " ".join(cmd)
    
    # Check if this is an alisim command and output already exists
    if skip_if_output_exists and output_folder:
        if output_folder.exists() and any(output_folder.iterdir()):
            skip_msg = f"SKIP: Output folder already exists and is not empty: {output_folder}"
            print(f"\n{'='*80}")
            print(skip_msg)
            print(f"{'='*80}\n")
            if LOG_FILE:
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(f"{skip_msg}\n")
                    f.write(f"Skipped command: {cmd_str}\n\n")
            return
    
    # Write to log file
    if LOG_FILE:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"RUN: {cmd_str}\n")
    
    print(f"\n{'='*80}")
    print(f"RUN: {cmd_str}")
    print(f"{'='*80}\n")
    
    try:
        # Run command with real-time output to terminal
        result = subprocess.run(cmd, check=True, text=True)
    except subprocess.CalledProcessError as e:
        # For commands with captured output, check for -redo error
        try:
            # Re-run to capture output for error checking
            result_check = subprocess.run(cmd, capture_output=True, text=True)
        except subprocess.CalledProcessError as e_check:
            error_output = e_check.stderr + e_check.stdout
            if "Use -redo" in error_output or "-redo" in error_output:
                warning_msg = f"WARNING: IQ-TREE returned 'Use -redo' error. Skipping this command."
                print(warning_msg)
                if LOG_FILE:
                    with open(LOG_FILE, "a", encoding="utf-8") as f:
                        f.write(f"{warning_msg}\n")
                        f.write(f"Error output (first 500 chars): {error_output[:500]}\n\n")
                return  # Skip this command and continue
            else:
                # For other errors, still raise the exception
                error_msg = f"ERROR: Command failed with error:\n{error_output}"
                print(error_msg)
                if LOG_FILE:
                    with open(LOG_FILE, "a", encoding="utf-8") as f:
                        f.write(f"{error_msg}\n\n")
                raise


def sanitize_hyphen(s):
    return s.replace("+", "-")


def sanitize_underscore(s):
    return s.replace("+", "_")


# =============================================================
# STEP 1 RUN MODELFINDER
# =============================================================

def run_model_finder(iqtree_path, alignment_path, threads, output_model):
    folder = output_model / "ModelFinder"
    folder.mkdir(parents=True, exist_ok=True)
    prefix = folder / "MF"

    if not (prefix.with_suffix(".treefile")).exists():
        run_command([
            str(iqtree_path),
            "-s", str(alignment_path),
            "-m", "MF",
            "-mset", "LG",
            "-pre", str(prefix),
            "-T", str(threads)
        ])

    # Extract best RHAS model from MF.iqtree
    iqtree_file = prefix.with_suffix(".iqtree")
    best_rhas = None
    with open(iqtree_file) as f:
        for line in f:
            if "Best-fit model according to BIC:" in line:
                model_full = line.split(":", 1)[1].strip()
                plus_index = model_full.find("+")
                if plus_index != -1:
                    best_rhas = model_full[plus_index + 1:].strip()
                else:
                    raise RuntimeError("ERROR: Cannot detect '+' in best model string.")
                break

    if best_rhas is None:
        raise RuntimeError("Could not detect best RHAS model from ModelFinder output.")

    print("\n>>> Best RHAS model detected:", best_rhas, "\n")
    return best_rhas


# =============================================================
# STEP 2 RHAS Model
# =============================================================

def extract_freerate_values(iqtree_file):
    props = []
    with open(iqtree_file) as f:
        for line in f:
            if "Site proportion and rates:" in line:
                parts = line.split(":")[1].strip().split(")")
                for p in parts:
                    p = p.strip().lstrip("(")
                    if not p:
                        continue
                    a, b = p.split(",")
                    props.append(a.strip())
                    props.append(b.strip())
                break

    if not props:
        raise RuntimeError("ERROR: Could not extract FreeRate parameters")

    return "{" + ",".join(props) + "}"

def extract_invariable_proportion(iqtree_file):
    with open(iqtree_file) as f:
        for line in f:
            if "Proportion of invariable sites:" in line:
                value = line.split(":")[1].strip()
                return value
    raise RuntimeError("ERROR: Could not extract invariable sites proportion")

def extract_gamma_shape(iqtree_file):
    with open(iqtree_file) as f:
        for line in f:
            if "Gamma shape alpha:" in line:
                value = line.split(":")[1].strip()
                return value
    raise RuntimeError("ERROR: Could not extract Gamma shape alpha")

# =============================================================
# STEP 3 RUN MODELS FROM TXT
# =============================================================

def run_models_from_txt(
    txt_path, iqtree_path, alignment_path, threads, length,
    best_rhas, output_model, output_simulation, model_finder_tree,
    modeldef_path=None, optimise_tree=False):

    with open(txt_path) as f:
        model_list = [line.strip() for line in f if line.strip()]

    for model_raw in model_list:

        print(f"\n==============================")
        print(f" Processing model: {model_raw}")
        print(f"==============================\n")

        parts = model_raw.split("+")
        if len(parts) < 2:
            print(f"ERROR: invalid model format â†’ {model_raw}")
            continue

        is_custom = modeldef_path is not None

        # =============================================================
        # CUSTOM MODEL (if -m is provided)
        # =============================================================
        if is_custom:
            print(f"â†’ Detected CUSTOM model (because -m was provided): {model_raw}\n")

            model_hy = sanitize_hyphen(model_raw)
            model_us = sanitize_underscore(model_raw)

            best_hy = sanitize_hyphen(best_rhas)
            best_us = sanitize_underscore(best_rhas)

            # ---------------------------------------------------------
            # CUSTOM FIX
            # ---------------------------------------------------------
            folder_model_fix = output_model / f"{model_hy}fix-{best_hy}"
            folder_sim_fix = output_simulation / f"{model_hy}fix-{best_hy}"
            folder_model_fix.mkdir(parents=True, exist_ok=True)
            folder_sim_fix.mkdir(parents=True, exist_ok=True)

            prefix_fix = folder_model_fix / f"{model_us}fix_{best_us}"
            
            run_command([
                str(iqtree_path),
                "-s", str(alignment_path),
                "-m", f"{model_raw}+{best_rhas}",
                "-pre", str(prefix_fix),
                "-prec", "10",
                "-T", str(threads),
                "-mdef", str(modeldef_path),
                "-te", str(model_finder_tree)
            ])

            iqtree_file = prefix_fix.with_suffix(".iqtree")
            
            rhas_without_f = best_rhas.replace("+F", "")
            modified_model = f"{model_raw}+{rhas_without_f}"
            
            has_i = "I" in rhas_without_f
            has_r = "R" in rhas_without_f
            has_g4 = "G4" in rhas_without_f
            
            if has_i:
                inv_prop = extract_invariable_proportion(iqtree_file)
                modified_model = modified_model.replace("+I", f"+I{{{inv_prop}}}")
            
            if has_r:
                import re
                fr_values = extract_freerate_values(iqtree_file)
                r_match = re.search(r'R(\d+)', modified_model)
                if r_match:
                    modified_model = re.sub(r'R(\d+)', rf'R\g<1>{fr_values}', modified_model)
            
            if has_g4:
                gamma_shape = extract_gamma_shape(iqtree_file)
                modified_model = modified_model.replace("+G4", f"+G4{{{gamma_shape}}}")

            run_command([
                str(iqtree_path),
                "--alisim", str(folder_sim_fix / "seq"),
                "--seqtype", "AA",
                "-m", modified_model,
                "-mdef", str(modeldef_path),
                "-t", str(prefix_fix) + ".treefile",
                "--length", str(length),
                "--out-format", "fasta",
                "--num-alignments", "100",
                "-T", str(threads)
            ], skip_if_output_exists=True, output_folder=folder_sim_fix)

            # ---------------------------------------------------------
            # CUSTOM FIX + PMSF
            # ---------------------------------------------------------
            best_rhas_pmsf = best_rhas.replace("+I", "").replace("I+", "")
            best_pmsf_hy = sanitize_hyphen(best_rhas_pmsf).lstrip("-")
            best_pmsf_us = sanitize_underscore(best_rhas_pmsf).lstrip("_")

            folder_model_fix_pmsf = output_model / f"{model_hy}fix-{best_pmsf_hy}-PMSF"
            folder_sim_fix_pmsf = output_simulation / f"{model_hy}fix-{best_pmsf_hy}-PMSF"
            folder_model_fix_pmsf.mkdir(parents=True, exist_ok=True)
            folder_sim_fix_pmsf.mkdir(parents=True, exist_ok=True)

            prefix_fix1 = folder_model_fix_pmsf / f"{model_us}fix_{best_pmsf_us}_PMSF_step1"
            prefix_fix2 = folder_model_fix_pmsf / f"{model_us}fix_{best_pmsf_us}_PMSF_step2"

            pmsf_model = f"{model_raw}+{best_rhas_pmsf}"

            # Determine which tree to use for -ft
            ft_tree = str(prefix_fix) + ".treefile" if optimise_tree else str(model_finder_tree)

            # Step 1
            run_command([
                str(iqtree_path),
                "-s", str(alignment_path),
                "-m", pmsf_model,
                "-mdef", str(modeldef_path),
                "-ft", ft_tree,
                "-me", "0.99",
                "-safe",
                "-pre", str(prefix_fix1),
                "-T", str(threads),
                "-n", "0"
            ])

            # Step 2
            run_command([
                str(iqtree_path),
                "-s", str(alignment_path),
                "-fs", str(prefix_fix1) + ".sitefreq",
                "-mdef", str(modeldef_path),
                "-m", pmsf_model,
                "-safe",
                "-pre", str(prefix_fix2),
                "-wsr",
                "-bb", "1000",
                "--wbtl"
            ])

            run_command(["python", "combine_sitefq_rate.py", str(folder_model_fix_pmsf)])

            run_command([
                str(iqtree_path),
                "--alisim", str(folder_sim_fix_pmsf / "seq"),
                "--seqtype", "AA",
                "-p", str(folder_model_fix_pmsf / f"{model_us}fix_{best_pmsf_us}_PMSF.nex"),
                "-t", str(prefix_fix2) + ".contree",
                "--length", str(length),
                "--out-format", "fasta",
                "--num-alignments", "100",
                "-mdef", str(modeldef_path)
            ], skip_if_output_exists=True, output_folder=folder_sim_fix_pmsf)

            # ---------------------------------------------------------
            # CUSTOM OPT
            # ---------------------------------------------------------
            folder_model_opt = output_model / f"{model_hy}opt-{best_hy}"
            folder_sim_opt = output_simulation / f"{model_hy}opt-{best_hy}"
            folder_model_opt.mkdir(parents=True, exist_ok=True)
            folder_sim_opt.mkdir(parents=True, exist_ok=True)

            prefix_opt = folder_model_opt / f"{model_us}opt_{best_us}"
            tree_opt = str(prefix_fix2) + ".treefile" if optimise_tree else str(model_finder_tree)
            
            run_command([
                str(iqtree_path),
                "-s", str(alignment_path),
                "-m", f"{model_raw}+{best_rhas}",
                "-mwopt",
                "-mdef", str(modeldef_path),
                "-pre", str(prefix_opt),
                "-prec", "10",
                "-T", str(threads),
                "-te", tree_opt
            ])

            run_command([
                "python", "extract_profiles_weights.py",
                str(folder_model_opt),
                str(modeldef_path)
            ])

            run_command([
                str(iqtree_path),
                "--alisim", str(folder_sim_opt / "seq"),
                "--seqtype", "AA",
                "-m", "OPT",
                "-mdef", str(prefix_opt) + ".nex",
                "-t", str(prefix_opt) + ".treefile",
                "--length", str(length),
                "--out-format", "fasta",
                "--num-alignments", "100",
                "-T", str(threads)
            ], skip_if_output_exists=True, output_folder=folder_sim_opt)

            # ---------------------------------------------------------
            # CUSTOM OPT + PMSF
            # ---------------------------------------------------------
            folder_model_opt_pmsf = output_model / f"{model_hy}opt-{best_pmsf_hy}-PMSF"
            folder_sim_opt_pmsf = output_simulation / f"{model_hy}opt-{best_pmsf_hy}-PMSF"
            folder_model_opt_pmsf.mkdir(parents=True, exist_ok=True)
            folder_sim_opt_pmsf.mkdir(parents=True, exist_ok=True)

            prefix_opt1 = folder_model_opt_pmsf / f"{model_us}opt_{best_pmsf_us}_PMSF_step1"
            prefix_opt2 = folder_model_opt_pmsf / f"{model_us}opt_{best_pmsf_us}_PMSF_step2"

            # Determine which tree to use for -ft (use opt tree)
            ft_tree_opt = str(prefix_opt) + ".treefile" if optimise_tree else str(model_finder_tree)

            # Step 1
            run_command([
                str(iqtree_path), "-s", str(alignment_path),
                "-m", pmsf_model,
                "-mwopt",
                "-mdef", str(modeldef_path),
                "-ft", ft_tree_opt,
                "-me", "0.99",
                "-safe",
                "-pre", str(prefix_opt1),
                "-T", str(threads),
                "-n", "0"
            ])

            # Step 2
            run_command([
                str(iqtree_path),
                "-s", str(alignment_path),
                "-fs", str(prefix_opt1) + ".sitefreq",
                "-m", pmsf_model,
                "-mwopt",
                "-safe",
                "-mdef", str(modeldef_path),
                "-pre", str(prefix_opt2),
                "-wsr",
                "-bb", "1000",
                "--wbtl"
            ])

            run_command(["python", "combine_sitefq_rate.py", str(folder_model_opt_pmsf)])

            run_command([
                str(iqtree_path),
                "--alisim", str(folder_sim_opt_pmsf / "seq"),
                "--seqtype", "AA",
                "-p", str(folder_model_opt_pmsf / f"{model_us}opt_{best_pmsf_us}_PMSF.nex"),
                "-t", str(prefix_opt2) + ".contree",
                "--length", str(length),
                "--out-format", "fasta",
                "-mdef", str(modeldef_path),
                "--num-alignments", "100"
            ], skip_if_output_exists=True, output_folder=folder_sim_opt_pmsf)

            continue  # END CUSTOM BRANCH

        # =============================================================
        # STANDARD MODEL (NO -m PROVIDED)
        # =============================================================
        print(f"detected STANDARD model (because no -m was provided): {model_raw}\n")

        model_hy = sanitize_hyphen(model_raw)
        model_us = sanitize_underscore(model_raw)
        best_hy = sanitize_hyphen(best_rhas)
        best_us = sanitize_underscore(best_rhas)

        base_model = f"{model_raw}+{best_rhas}"

        # -------------------------------------------------------------
        # (1) STANDARD FIX
        # -------------------------------------------------------------
        folder_model = output_model / f"{model_hy}fix-{best_hy}"
        folder_sim = output_simulation / f"{model_hy}fix-{best_hy}"
        folder_model.mkdir(parents=True, exist_ok=True)
        folder_sim.mkdir(parents=True, exist_ok=True)

        prefix = folder_model / f"{model_us}fix_{best_us}"
        
        run_command([
            str(iqtree_path),
            "-s", str(alignment_path),
            "-m", base_model,
            "-pre", str(prefix),
            "-prec", "10",
            "-T", str(threads),
            "-te", str(model_finder_tree)
        ])

        modified_base_model = base_model
        iqtree_file = prefix.with_suffix(".iqtree")
        
        rhas_without_f = best_rhas.replace("+F", "")
        
        if "R" in rhas_without_f:
            fr_values = extract_freerate_values(iqtree_file)
            import re
            r_match = re.search(r'\+R(\d+)', rhas_without_f)
            if r_match:
                r_num = r_match.group(1)
                modified_base_model = modified_base_model.replace(f"+R{r_num}", f"+R{r_num}{fr_values}")
        
        if "I" in rhas_without_f:
            inv_prop = extract_invariable_proportion(iqtree_file)
            modified_base_model = modified_base_model.replace("+I", f"+I{{{inv_prop}}}")
        
        if "G4" in rhas_without_f:
            gamma_shape = extract_gamma_shape(iqtree_file)
            modified_base_model = modified_base_model.replace("+G4", f"+G4{{{gamma_shape}}}")

        sim_cmd = [
            str(iqtree_path),
            "--alisim", str(folder_sim / "seq"),
            "--seqtype", "AA",
            "-m", modified_base_model,
            "-t", str(prefix) + ".treefile",
            "--length", str(length),
            "--out-format", "fasta",
            "--num-alignments", "100",
            "-T", str(threads)
        ]

        run_command(sim_cmd, skip_if_output_exists=True, output_folder=folder_sim)

        # -------------------------------------------------------------
        # (2) STANDARD PMSF
        # -------------------------------------------------------------
        best_rhas_pmsf = best_rhas.replace("+I", "").replace("I+", "")
        best_pmsf_hy = sanitize_hyphen(best_rhas_pmsf).lstrip("-")
        best_pmsf_us = sanitize_underscore(best_rhas_pmsf).lstrip("_")

        folder_model_pmsf = output_model / f"{model_hy}fix-{best_pmsf_hy}-PMSF"
        folder_sim_pmsf = output_simulation / f"{model_hy}fix-{best_pmsf_hy}-PMSF"
        folder_model_pmsf.mkdir(parents=True, exist_ok=True)
        folder_sim_pmsf.mkdir(parents=True, exist_ok=True)

        prefix1 = folder_model_pmsf / f"{model_us}fix_{best_pmsf_us}_PMSF_step1"
        prefix2 = folder_model_pmsf / f"{model_us}fix_{best_pmsf_us}_PMSF_step2"

        pmsf_model = f"{model_raw}+{best_rhas_pmsf}"

        # Determine which tree to use for -ft
        ft_tree = str(prefix) + ".treefile" if optimise_tree else str(model_finder_tree)

        # Step 1
        run_command([
            str(iqtree_path), "-s", str(alignment_path),
            "-m", pmsf_model,
            "-ft", ft_tree,
            "-me", "0.99", "-safe",
            "-pre", str(prefix1),
            "-T", str(threads),
            "-n", "0"
        ])

        # Step 2
        run_command([
            str(iqtree_path),
            "-s", str(alignment_path),
            "-fs", str(prefix1) + ".sitefreq",
            "-m", pmsf_model,
            "-safe",
            "-pre", str(prefix2),
            "-wsr", "-bb", "1000", "--wbtl"
        ])

        run_command(["python", "combine_sitefq_rate.py", str(folder_model_pmsf)])

        run_command([
            str(iqtree_path),
            "--alisim", str(folder_sim_pmsf / "seq"),
            "--seqtype", "AA",
            "-p", str(folder_model_pmsf / f"{model_us}fix_{best_pmsf_us}_PMSF.nex"),
            "-t", str(prefix2) + ".contree",
            "--length", str(length),
            "--out-format", "fasta",
            "--num-alignments", "100"
        ], skip_if_output_exists=True, output_folder=folder_sim_pmsf)

        # -------------------------------------------------------------
        # (3) STANDARD OPT
        # -------------------------------------------------------------
        folder_model_opt = output_model / f"{model_hy}opt-{best_hy}"
        folder_sim_opt = output_simulation / f"{model_hy}opt-{best_hy}"
        folder_model_opt.mkdir(parents=True, exist_ok=True)
        folder_sim_opt.mkdir(parents=True, exist_ok=True)

        prefix_opt = folder_model_opt / f"{model_us}opt_{best_us}"
        tree_opt = str(prefix2) + ".treefile" if optimise_tree else str(model_finder_tree)

        run_command([
            str(iqtree_path),
            "-s", str(alignment_path),
            "-m", base_model,
            "-mwopt",
            "-prec", "10",
            "-pre", str(prefix_opt),
            "-T", str(threads),
            "-te", tree_opt
        ])

        run_command(["python", "extract_profiles_weights.py", str(folder_model_opt)])

        run_command([
            str(iqtree_path),
            "--alisim", str(folder_sim_opt / "seq"),
            "--seqtype", "AA",
            "-m", "OPT",
            "-mdef", str(prefix_opt) + ".nex",
            "-t", str(folder_model / f"{model_us}fix_{best_us}.treefile"),
            "--length", str(length),
            "--out-format", "fasta",
            "--num-alignments", "100",
            "-T", str(threads)
        ], skip_if_output_exists=True, output_folder=folder_sim_opt)

        # -------------------------------------------------------------
        # (4) STANDARD OPT + PMSF
        # -------------------------------------------------------------
        folder_model_opt_pmsf = output_model / f"{model_hy}opt-{best_pmsf_hy}-PMSF"
        folder_sim_opt_pmsf = output_simulation / f"{model_hy}opt-{best_pmsf_hy}-PMSF"
        folder_model_opt_pmsf.mkdir(parents=True, exist_ok=True)
        folder_sim_opt_pmsf.mkdir(parents=True, exist_ok=True)

        prefix_opt1 = folder_model_opt_pmsf / f"{model_us}opt_{best_pmsf_us}_PMSF_step1"
        prefix_opt2 = folder_model_opt_pmsf / f"{model_us}opt_{best_pmsf_us}_PMSF_step2"

        # Determine which tree to use for -ft (use opt tree)
        ft_tree_opt = str(prefix_opt) + ".treefile" if optimise_tree else str(model_finder_tree)

        run_command([
            str(iqtree_path), "-s", str(alignment_path),
            "-m", pmsf_model,
            "-mwopt",
            "-ft", ft_tree_opt,
            "-me", "0.99", "-safe",
            "-pre", str(prefix_opt1),
            "-T", str(threads),
            "-n", "0"
        ])

        run_command([
            str(iqtree_path),
            "-s", str(alignment_path),
            "-fs", str(prefix_opt1) + ".sitefreq",
            "-m", pmsf_model,
            "-mwopt",
            "-safe",
            "-pre", str(prefix_opt2),
            "-wsr",
            "-bb", "1000",
            "--wbtl"
        ])

        run_command(["python", "combine_sitefq_rate.py", str(folder_model_opt_pmsf)])

        run_command([
            str(iqtree_path),
            "--alisim", str(folder_sim_opt_pmsf / "seq"),
            "--seqtype", "AA",
            "-p", str(folder_model_opt_pmsf / f"{model_us}opt_{best_pmsf_us}_PMSF.nex"),
            "-t", str(prefix_opt2) + ".contree",
            "--length", str(length),
            "--out-format", "fasta",
            "--num-alignments", "100"
        ], skip_if_output_exists=True, output_folder=folder_sim_opt_pmsf)


# =============================================================
# MAIN FUNCTION
# =============================================================

def main():
    global LOG_FILE
    
    parser = argparse.ArgumentParser()

    parser.add_argument("-s", "--sequence", required=True)
    parser.add_argument("-iqtree", required=True)
    parser.add_argument("-threads", type=int, default=1)
    parser.add_argument("-txt", required=True)
    parser.add_argument("-l", "--length", type=int, required=True)
    parser.add_argument("-m", "--modeldef", required=False, help="User-defined model file (.nex)")
    parser.add_argument("-optimise-tree", action="store_true", help="Use previous step's tree file for each model version")

    args = parser.parse_args()

    alignment_path = Path(args.sequence).resolve()
    iqtree_path = Path(args.iqtree).resolve()
    txt_path = Path(args.txt).resolve()
    modeldef_path = Path(args.modeldef).resolve() if args.modeldef else None

    base = alignment_path.parent
    output_model = base / "output_model"
    output_simulation = base / "output_simulation"
    output_model.mkdir(exist_ok=True)
    output_simulation.mkdir(exist_ok=True)

    # Initialize log file
    LOG_FILE = base / "command_log.txt"
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("="*80 + "\n")
        f.write("COMMAND EXECUTION LOG\n")
        f.write(f"Started at: {Path(__file__).name}\n")
        if args.optimise_tree:
            f.write("Mode: Tree optimisation enabled (-optimise-tree)\n")
        f.write("="*80 + "\n\n")

    # Step 1: ModelFinder
    best_rhas = run_model_finder(iqtree_path, alignment_path, args.threads, output_model)

    model_finder_tree = output_model / "ModelFinder" / "MF.treefile"

    # Step 2: Run models
    run_models_from_txt(
        txt_path, iqtree_path, alignment_path,
        args.threads, args.length,
        best_rhas, output_model, output_simulation,
        model_finder_tree, modeldef_path, args.optimise_tree
    )
    
    
    # Step 3: Run PBT analysis
    print(f"\n{'='*80}")
    print(f"Running PBT analysis...")
    print(f"{'='*80}\n")
    
    run_command([
        "python", "PBT.py",
        str(output_simulation),
        str(alignment_path),
        "-T", str(args.threads)
    ])
    
    print(f"\n{'='*80}")
    print(f"All commands logged to: {LOG_FILE}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()