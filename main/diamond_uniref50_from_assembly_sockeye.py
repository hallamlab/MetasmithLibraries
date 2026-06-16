#!/usr/bin/env python3
"""Run a DIAMOND UniRef50 annotation workflow for a nucleotide assembly FASTA on SOCKEYE.

Sockeye port of diamond_uniref50_from_assembly.py. Minimal differences:
  - Agent retargeted to sockeye over SSH with the APPTAINER runtime and sockeye's
    module quirk (`module load gcc/9.4.0` BEFORE `module load apptainer`; a bare
    `module load apptainer` silently no-ops on sockeye).
  - The input FASTA is uploaded to sockeye and referenced by its REMOTE path —
    metasmith does not auto-transfer non-resident inputs (it fails fast instead),
    so the .xgdb item must point at a path that already exists on the agent host.
  - Deploys to $HOME (sockeye's /scratch is allocation-coded and refuses mkdir).
  - Runs end-to-end (Deploy -> Generate -> Stage -> Run -> Wait -> Result) rather
    than stopping at DAG generation.

Set MSM_SLURM_ACCOUNT=<allocation> to submit through the SLURM executor;
unset it to use the default (local) executor.

NOTE: our sockeye deploy smoke reached Deploy GREEN (use-sif) but StageWorkflow
currently trips the open #240 lib-bind bug; this script is wired correctly and
will complete once #240 is resolved.
"""
import os
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, "/home/tony/agentic_workspace/projects/metasmith/dev/src")
from metasmith.python_api import (
    Agent, SshSource, ContainerRuntime,
    DataInstanceLibrary, TransformInstanceLibrary,
    TargetBuilder,
)

# ── sockeye target ───────────────────────────────────────────────────────────
HPC_HOST = "sockeye"
SETUP_COMMANDS = ["module load gcc/9.4.0", "module load apptainer"]
# prodigal (16GB) and diamond (64GB) exceed the 8GB local cap, so they must run
# on SLURM. txyliu's standard (CPU) allocation; override via MSM_SLURM_ACCOUNT.
DEFAULT_SLURM_ACCOUNT = "st-shallam-1"

# Pre-built UniRef50 DIAMOND DB already on sockeye. Supplying it as a
# ref::uniref50_diamond_db resource lets the planner SKIP downloadUniRef50DB
# (which is hard-labeled `local` → pinned to the login node, where its 64GB ask
# + 60GB wget + `diamond makedb` cannot run). Pattern mirrors launch_dl_embeddings.
REMOTE_UNIREF50_DMND = Path("/arc/project/st-shallam-1/pwy_group/lib/diamond/uniref50.dmnd")

LOCAL_ASSEMBLY = Path("/home/tony/agentic_workspace/data/scadc/references/pcc1.genbank.fna")  # <assembly>
OUT_DIR = Path("results/diamond_uniref50_sockeye")

MLIB = Path(__file__).resolve().parent.parent


def ssh_capture(cmd: str) -> str:
    return subprocess.run(
        ["ssh", HPC_HOST, cmd], capture_output=True, text=True, check=True
    ).stdout.strip()


def stage_input_to_sockeye(base_dir: str) -> str:
    """Upload the assembly under base_dir on sockeye, return its remote path (idempotent)."""
    remote_dir = f"{base_dir}/diamond_uniref50/inputs"
    remote_path = f"{remote_dir}/{LOCAL_ASSEMBLY.name}"
    ssh_capture(f"mkdir -p {remote_dir}")
    remote_size = subprocess.run(
        ["ssh", HPC_HOST, f"stat -c %s {remote_path} 2>/dev/null || echo MISSING"],
        capture_output=True, text=True,
    ).stdout.strip()
    if remote_size == str(LOCAL_ASSEMBLY.stat().st_size):
        print(f"==> input already on sockeye: {remote_path}", flush=True)
    else:
        print(f"==> uploading {LOCAL_ASSEMBLY.name} -> {HPC_HOST}:{remote_path}", flush=True)
        subprocess.run(["scp", str(LOCAL_ASSEMBLY), f"{HPC_HOST}:{remote_path}"], check=True)
    return remote_path


def prefetch_tool_containers(agent_home: str, task_key: str):
    """Pre-pull the plan's tool containers into the agent cache on the LOGIN node.

    sockeye compute nodes have NO outbound network, so a step's lazy
    `apptainer exec docker://...` dies with 'no route to host'. metasmith's
    Deploy pulls only its own image, not per-transform tools. We warm the cache
    here: parse the staged workflow.nf for the `containers::<x>.oci` it actually
    uses, read each .oci's docker URL, and pull it as a .sif (sockeye = use-sif).
    """
    run = f"{agent_home}/runs/{task_key}"
    setup = " && ".join(SETUP_COMMANDS)
    remote = f"""
        set -e
        {setup}
        export APPTAINER_CACHEDIR="{agent_home}/.apptainer_cache"; mkdir -p "$APPTAINER_CACHEDIR"
        R="{run}"; CACHE="{agent_home}/container_images"; mkdir -p "$CACHE"
        names=$(grep -oE 'containers::[A-Za-z0-9._-]+\\.oci' "$R/workflow.nf" | sed 's/containers:://' | sort -u)
        echo "plan containers: $names"
        for n in $names; do
            oci=$(find "$R/_metasmith/task/data" -name "$n" | head -1)
            [ -z "$oci" ] && {{ echo "FAIL: no .oci file for $n"; exit 2; }}
            url=$(tr -d '[:space:]' < "$oci")
            cname=$(printf '%s' "$url" | sed 's#://#..#g; s#:#..#g; s#/#_#g')
            sif="$CACHE/$cname.sif"
            if [ -e "$sif" ]; then echo "cached: $n"; else
                echo "pulling: $n ($url)"
                apptainer pull "$sif" "$url" || {{ echo "FAIL pull: $n"; exit 3; }}
                echo "ok: $n"
            fi
        done
        echo "prefetch done"
    """
    print("==> prefetch tool containers on login node", flush=True)
    res = subprocess.run(["ssh", HPC_HOST, remote], capture_output=True, text=True)
    print(res.stdout, flush=True)
    if res.returncode != 0 or "prefetch done" not in res.stdout:
        print(res.stderr, file=sys.stderr)
        raise RuntimeError("tool container prefetch failed")


def main():
    account = os.environ.get("MSM_SLURM_ACCOUNT", DEFAULT_SLURM_ACCOUNT)
    user = ssh_capture("echo $USER")
    # sockeye FORBIDS running SLURM jobs from /arc/home — the agent home (and thus
    # Nextflow's work dir) must live on allocation-coded scratch: /scratch/<alloc>/<user>.
    scratch = f"/scratch/{account}/{user}"
    agent_home = f"{scratch}/metasmith"
    remote_assembly = stage_input_to_sockeye(scratch)

    out = OUT_DIR.resolve()
    out.mkdir(parents=True, exist_ok=True)

    # inputs.xgdb references REMOTE (sockeye) paths; not validated locally
    inputs = DataInstanceLibrary(out / "inputs.xgdb")
    inputs.AddTypeLibrary(MLIB / "data_types" / "sequences.yml")
    inputs.AddTypeLibrary(MLIB / "data_types" / "ref.yml")
    inputs.AddItem(Path(remote_assembly), "sequences::assembly")
    # pre-staged DB → planner skips the (login-node-impossible) download step
    inputs.AddItem(REMOTE_UNIREF50_DMND, "ref::uniref50_diamond_db")
    inputs.Save()

    smith = Agent(
        home=SshSource(host=HPC_HOST, path=agent_home).AsSource(),
        runtime=ContainerRuntime.APPTAINER,
        setup_commands=SETUP_COMMANDS,
    )

    print("==> Deploy()", flush=True)
    smith.Deploy()

    targets = TargetBuilder()
    targets.Add("annotation::diamond_uniref50_results")

    print("==> GenerateWorkflow()", flush=True)
    task = smith.GenerateWorkflow(
        samples=list(inputs.AsSamples("sequences::assembly")),
        resources=[DataInstanceLibrary.Load(MLIB / "resources" / "containers"), inputs],
        transforms=[
            TransformInstanceLibrary.Load(MLIB / "transforms" / "logistics"),
            TransformInstanceLibrary.Load(MLIB / "transforms" / "metagenomics"),
            TransformInstanceLibrary.Load(MLIB / "transforms" / "functionalAnnotation"),
        ],
        targets=targets,
    )
    if not task.ok or len(task.plan.steps) == 0:
        print(f"!! plan failed: hints={list(task.plan.hints)}", file=sys.stderr)
        return 3
    task.plan.RenderDAG(str(out / "dag"), format="svg")
    print(f"==> task key: {task.GetKey()}  steps={len(task.plan.steps)}", flush=True)

    print("==> StageWorkflow(on_exist=clear)", flush=True)
    smith.StageWorkflow(task, on_exist="clear")

    # sockeye compute nodes have no internet → warm the tool-container cache now
    prefetch_tool_containers(agent_home, task.GetKey())

    print(f"==> RunWorkflow (SLURM, account={account})", flush=True)
    smith.RunWorkflow(
        task,
        config_file=smith.GetNxfConfigPresets()["slurm"],
        params=dict(slurmAccount=account),
    )

    print("==> WaitForWorkflow", flush=True)
    result = smith.WaitForWorkflow(task, timeout_s=10800.0, poll_s=15.0)
    print(f"==> status: {result['status']} after {result['elapsed_s']:.1f}s", flush=True)
    for line in result["tail"]:
        print(f"    {line}")
    if result["status"] != "completed":
        return 2

    src = smith.GetResultSource(task)
    print(f"==> result source: {src.GetPath()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
