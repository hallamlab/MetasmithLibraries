# AGENTS.md

## Overview

Metasmith transform library for deep-learning protein models. The local source-of-truth lives in `data_types/`, `resources/*/_metadata/`, and `transforms/<domain>/*.py`; the build (`./dev.sh -b`) compiles flattened `_metadata/types/*.yml` per transform domain. See the auto-memory `build-contract` for the edit/generate split.

Workflows are launched from `main/launch_dl_embeddings.py` and execute on the remote agent host `fir` (Compute Canada). Per-transform GPU clusterOptions are injected into Nextflow via `make_fir_slurm_config()`; runtime hyperparameters (batch size, max length, chunk overlap) are baked as module-level constants in each transform's `.py` (the `user_params` runtime override channel was reverted in metasmith/dev).

## Environment

- **Local build env:** mamba env `msm_env` — the linuxbrew `msm` shim is missing the `metasmith` module, so commands must use `PATH=/home/tony/miniforge3/envs/msm_env/bin:$PATH`.
- **Rebuild:** `PATH=/home/tony/miniforge3/envs/msm_env/bin:$PATH ./dev.sh -b`
- **Remote host:** `fir` (login3); `HPC_MSM_HOME=/scratch/phyberos/metasmith`, scratch root `/scratch/phyberos/dl_testing_claude`.
- **SLURM account:** `def-shallam_gpu` (the only `phyberos` allocation that maps to GPU partitions; `rrg-shallam-ab` is CPU-only).

## Key paths

| Path | Purpose |
|------|---------|
| `data_types/<ns>.yml` | Hand-edited type definitions per namespace. |
| `resources/<r>/_metadata/{index,types/<ns>}.yml` | Hand-edited resource manifests and types. |
| `transforms/<domain>/*.py` | Transform implementations (hand-edited). |
| `transforms/<domain>/_metadata/types/*.yml` | **Build-generated**, do not hand-edit. |
| `main/launch_dl_embeddings.py` | Top-level driver (Generate → Stage → Run on fir). |
| `main/cache/task_keys.json` | Map of run name → metasmith task key (e.g. `metag_full_esmc → qKsXpL4y`). |
| `tests/manual/oom_probe.py` | Worst-case batch×max_len GPU probe, per MIG slice. |

## Launching workflows

```bash
# fosmids (4786 ORFs), one model
python main/launch_dl_embeddings.py run --target fosmids --only esmc

# metag (1.44M ORFs), one model
python main/launch_dl_embeddings.py run --target metag --only esmc

# smoke test (subsample to first N ORFs on fir)
python main/launch_dl_embeddings.py run --target metag --only esmc --test 32
```

`Agent.RunWorkflow(...)` returns as soon as the detached driver is launched on fir's login node — it is *not* a blocking wait. See **Monitoring** below for completion signals.

## Monitoring a running workflow

For task key `<KEY>`, the run dir is `/scratch/phyberos/metasmith/runs/<KEY>/`:

```
<KEY>/
  PID.lock                       # PID of the detached `msm api run_workflow` driver
  start.sh                       # what was nohup'd on the login node
  _metasmith/logs.latest/agent.log   # driver stdout/stderr; terminal status here
  nxf_work/<hash>/.command.err   # per-shard stderr (torch OOM traces land here)
  results/                       # workflow outputs
```

SLURM jobs are named `nf-p<N>__<transform>_(<shard>)` — filter `squeue` to `^nf-` for the active task list.

**Single ping when the run finishes** (Bash `run_in_background` + `until` loop — the completion notification is the ping):

```bash
PID=$(ssh fir 'cat /scratch/phyberos/metasmith/runs/<KEY>/PID.lock')
until ! ssh fir "kill -0 $PID 2>/dev/null"; do sleep 60; done
ssh fir 'tail -30 /scratch/phyberos/metasmith/runs/<KEY>/_metasmith/logs.latest/agent.log'
```

Driver-PID-gone covers both success and failure, so silence ≠ stuck. The trailing `tail` surfaces the terminal status with the notification.

**Per-shard pings as jobs land/finish:** use the `Monitor` tool with a `squeue` poll loop that diffs the `nf-*` set. Cover terminal states broadly — `COMPLETED|FAILED|CANCELLED|TIMEOUT|OUT_OF_MEMORY` — so crashloops don't go silent. Exit when both the `nf-*` queue is empty *and* the driver PID is gone (Nextflow's gap between process waves can momentarily show an empty queue while the driver is alive).

**Debugging a shard failure:** `nxf_work/<hash>/.command.err` is where torch tracebacks and OOM signatures land. The agent log only says "step N failed."

## Conventions

- Hand-edit only what the build contract calls "source-of-truth." `./dev.sh -b` regenerates the flattened type copies.
- Bake hyperparameters as module-level constants in transforms (`BATCH_SIZE`, `MAX_LEN`, `CHUNK_OVERLAP`). Do not reintroduce `context.params.get(...)` — the runtime override channel is dead.
- GPU tiers: `1g.10gb` (`gpu_small`) and `3g.40gb` (`gpu_med`). ProtT5-XL requires `gpu_med`; the other encoders OOM-probe-clean on either but run on `gpu_med` by default.
- `SHARD_SIZE` in `transforms/logistics/shardFasta.py` is baked (currently 196k); fosmids → 1 shard, metag → 8 shards. Length-sorted round-robin striping spreads long sequences evenly.

## Gotchas

- The linuxbrew `msm` is broken (wrong Python). Always prepend `msm_env`'s bin to `PATH` for builds and local API use.
- The `dev.sh` fallback `$HERE/../Metasmith/dev.sh -r` is also broken on this machine — rely on `msm_env`.
- `Agent.RunWorkflow(user_params=...)` was removed in metasmith/dev; pre-revert installs at `/scratch/phyberos/metasmith` may still accept it but next refresh will not. Do not add new callers.
- `nvidia-smi --query-compute-apps --id=<MIG_UUID>` returns empty inside sbatch jobs — you can't poll MIG-slice memory from inside. Use torch's own OOM trace as the signal.
- Container SIFs for ankh/prott5/esmfold/saprot may not be pre-pulled into `/scratch/phyberos/metasmith/container_images/`; the OOM probe falls back to `/scratch/phyberos/dl_testing_claude/container_tests/builds/<container>.sif`.
