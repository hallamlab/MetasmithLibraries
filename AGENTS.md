# MetasmithLibraries — Development Notes

## Project structure

```
data_types/          # YAML type definitions (sequences, env, etc.)
resources/           # Data instance libraries (env declarations, reference DBs)
transforms/          # Transform implementations grouped by domain
  logistics/         # Data retrieval & format conversion
  assembly/          # Genome/metagenome assembly
  metagenomics/      # Binning, taxonomy, etc.
  functionalAnnotation/
  amplicon/
  pangenome/
tests/               # Pytest-based workflow & E2E tests
  test_data/         # Test datasets (ORA files, mock reads, assemblies)
  conftest.py        # Shared fixtures: agent, base_resources, tmp_inputs, etc.
```

## Build system

- **Rebuild metadata and re-solve the templates:** `./dev.sh -b` (needs the `msm` CLI on PATH)
- Alternatively: `mamba run -n msm msm build --types data_types --uniques resources/* --transforms transforms/*`
- The build regenerates all `_metadata/` directories from source YAML + transform Python files
- Every env resource file in `resources/env/` **must** have a matching type definition in `data_types/env.yml`, otherwise the build fails
- Every type referenced via `lib.GetType("namespace::type")` in transforms must exist in the corresponding `data_types/*.yml`

## Environments (containers + conda)

A tool's environment is declared generically. `resources/env/<tool>.env` is a
YAML file with an optional `container:` (a `docker://…` OCI URI, used by the
DOCKER/APPTAINER runtimes) and/or an optional `conda:` (a conda env name, used by
the MAMBA runtime). The engine selects which by the single global runtime (see
`ResolveEnvImage` / `GetContainerModel` in the metasmith engine). One `.env`
serves both a containerized run and a mamba run.

### Adding a new env

1. Add the type to `data_types/env.yml` with `extends: env` and a `provides` list
2. Create `resources/env/<name>.env` with `container: docker://…` and/or `conda: <name>`
3. If it has a `conda:` env, add a recipe `envs/tools/<name>.yml` (or re-run
   `python envs/gen_tool_envs.py`, which derives biocontainers specs automatically)
4. Run `./dev.sh -b` to rebuild metadata; `./dev.sh --create-envs` creates the conda test envs

## Writing transforms

- Transforms are Python files using `from metasmith.python_api import *`
- `TransformInstanceLibrary.ResolveParentLibrary(__file__)` loads types from the parent library's `_metadata/`
- Use `model.AddRequirement()` for inputs, `model.AddProduct()` for outputs
- For paired-end reads, use a grouping parent (e.g. `read_pair`) and set `parents={pair}` on both R1/R2 requirements
- `group_by=` in `TransformInstance()` controls how inputs are matched/grouped
- `context.ExecWithEnv().ifContainerDo(env=, cmd=)` declares how the tool runs; add
  `.ifVirtualEnvDo(env=, cmd=)` only for a conda arm you have actually run. `ExecWithContainer`
  is retired — the engine rejects it statically. See `docs/ENV_PORT.md`
- Container paths: `context.Input(x).container` (path inside container), `.local` (path on host), `.external` (path from outside container)

**A collecting transform must not pair two grouped slots by position.** `InputGroup(a)[i]` and
`InputGroup(b)[i]` arrive in independent task-arrival order and are deduped separately, so the
only thing relating them is declared lineage: `context.SourceOf(item, other_slot)` answers which
item of `other_slot` a given item descends from. `ppanggolin` is the reference — it names each
genome from the `ncbi::genome_name` its gbk descends from. `aggregator.py` shows the older
in-band alternative (join on a key present in both files) for cases where no lineage relates them.

**Anything downloaded from an accession is named by whoever asked for it, not by its header.**
`ncbi::genome_name` sits above `ncbi::assembly_accession` in lineage, so every product of
`getNcbiAssembly` inherits it. That transform *requires* a name and never reads one — the
declaration exists to put it in the lineage — which means **every caller registering an
accession must register a name above it**. No GenBank field works instead: `ORGANISM` is bare
species for most isolates, `DEFINITION` carries the strain only sometimes, and two assemblies of
one species collide under either (PPanGGOLiN then refuses the whole run over duplicate names).

## Writing tests

- Tests use `conftest.py` fixtures: `agent`, `base_resources`, `mlib`, `tmp_inputs`
- `tmp_inputs(["sequences.yml", ...])` creates a temporary `DataInstanceLibrary` with specified type libraries
- Use `inputs.AddItem(path, type)` for files, `inputs.AddValue(name, dict, type)` for JSON values
- Workflow generation tests: `agent.GenerateWorkflow(samples=, resources=, transforms=, targets=)`
- E2E tests: additionally call `agent.StageWorkflow()`, `agent.RunWorkflow()`, then `wait_for_workflow()`
- Mark E2E tests with `@pytest.mark.slow`
- Run tests with: `mamba run -n msm pytest tests/<file>.py -k "<pattern>" -v`

## Templates (`templates/`, authored from `main/`)

A template is a starting point a user picks in the GUI: a `metasmith.Spec` whose
input paths are `DEFERRED`, saved as `templates/<name>/spec.yml` with the deferred
input library packed inline. There is no template format — it is the same object a
stored workflow is, so a template validates the way a workflow does, by solving.

Shipping them here is what makes versioning free: a template arrives in the same
commit as the transforms it names and cannot be older than the library it was found in.

Authoring one is a module in `main/` defining `NAME`, `DESCRIPTION` and
`build_spec(rebuild=False)`, listed in `build_templates.py`. `main/_authoring.py`
owns the rest. Read `main/pangenome_heatmap_from_assembly.py` first — it is the
smallest complete example.

Four rules, each with a failure mode that is quiet if you break it:

- **No agent.** A template says what to build, never where. Whoever loads it supplies
  the host.
- **References stay inside the repo.** `Template.Save` refuses one that does not, because
  an absolute path is one machine's checkout and arrives at a colleague naming nothing.
- **Nothing rendered ships.** `--dag` writes an SVG under `results/` (git-ignored) so you
  can see whether the spec you wrote is the one you meant. The repository ships the spec;
  the GUI draws it in its own theme.
- **The input library is built once, then loaded back.** It ships inline in the spec, so an
  author reads it out of `templates/<name>/spec.yml` rather than rebuilding it. Deferred
  paths are minted on `AddItem` and identity follows the path, so re-minting on every build
  would change the template's task key each time and pile up duplicate rows. `--rebuild` is
  the deliberate way to start over after changing what the inputs *are*.

`./dev.sh -b` rebuilds `_metadata/` and then solves every template, failing by name — a
transform whose products change shape takes its templates down at build time. A template
that cannot ship stays listed in `BLOCKED` with the reason rather than being deleted.

## Driver scripts (`main/`)

Everything in `main/` that is not a template author runs against a real cluster.

- `main/examples/{diamond_uniref50_from_assembly,metag_workflow_from_reads}_sockeye.py` — HPC ports
  (SSH + APPTAINER + allocation-coded `/scratch`) that reference inputs/DBs by REMOTE path,
  supply pre-staged DBs as resources to prune the `local`-labeled `download*` steps, and run
  Deploy → Generate → Stage → Run → Wait. The metag one is a **W0/W1 pair**: run
  `main/examples/metag_setup_sockeye.py --run` first (prefetch the 17 tool containers via
  `env::pulled_container`, upload reads, verify DBs), then the workflow driver.
- `main/launch_dl_embeddings.py` — the deep-learning embedding workflow on a GPU cluster,
  with per-transform SLURM GPU `clusterOptions` rendered on top of the stock `slurm.nf`.
- `main/probe_planner.py` — plan-only: solve a target set and print which transforms were
  picked. Inputs are deferred; nothing is opened. This is the tool for "why did the planner
  add that step".

The shape of the DL workflow — targets, weights, transitive dependencies, GPU tiers — lives
once in `main/_dl_embeddings.py`; the launcher and the probe differ only in where the files
are. They had drifted apart when each carried its own copy.

Conventions:

- **Public-repo-safe config** — no hardcoded absolute paths, allocations, usernames, or DB
  paths. Site-specific values come from env vars with `<placeholder>` defaults (`MSM_SRC`,
  `MSM_HPC_HOST`, `MSM_SLURM_ACCOUNT`, `MSM_REF_DB_DIR`, …); `MSM_SRC` optionally prepends a
  metasmith source checkout to `sys.path`. HPC drivers `require_configured()` and exit if a
  placeholder is unfilled.
- `inputs.AddValue(name, value, type)` for inline values (e.g. `read_metadata`) and
  `inputs.AddItem(path, type, parents={...})` to chain lineage — meta → pair → reads is the
  canonical metag pattern.
- Include `transforms/logistics` so the planner auto-resolves external DBs, or supply them as
  pre-staged resources to skip the (login-node-only) downloads on HPC.
- To force all sibling transforms (e.g. all 3 binners), target a downstream that requires them
  all (`binning_local::cluster_table`), or give each sibling's target a distinct parent.
- A `sample_type` masks the library down to that row's lineage. Anything with no lineage
  relation to it — a weight tarball, a reference DB — becomes invisible to the plan and comes
  back as a `download*` step. Either leave the sample type unset or list the entry in
  `shared_input_paths`.

## Conda environment

- Use the `msm` env for `msm build` and `pytest`: `mamba run -n msm <command>`
