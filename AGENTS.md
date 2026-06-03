# MetasmithLibraries — Development Notes

## Project structure

```
data_types/          # YAML type definitions (sequences, containers, etc.)
resources/           # Data instance libraries (container URIs, reference DBs)
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

- **Rebuild metadata:** `./dev.sh -b` (requires `msm` CLI from the `msm_env` conda environment)
- Alternatively: `conda run -n msm_env msm build --types data_types --uniques resources/* --transforms transforms/*`
- The build regenerates all `_metadata/` directories from source YAML + transform Python files
- Every container resource file in `resources/containers/` **must** have a matching type definition in `data_types/containers.yml`, otherwise the build fails
- Every type referenced via `lib.GetType("namespace::type")` in transforms must exist in the corresponding `data_types/*.yml`

## Adding a new container

1. Add the type to `data_types/containers.yml` with `extends: container` and a `provides` list
2. Create `resources/containers/<name>.oci` containing the container URI (e.g. `docker://quay.io/org/image:tag`)
3. Run `./dev.sh -b` to rebuild metadata

## Writing transforms

- Transforms are Python files using `from metasmith.python_api import *`
- `TransformInstanceLibrary.ResolveParentLibrary(__file__)` loads types from the parent library's `_metadata/`
- Use `model.AddRequirement()` for inputs, `model.AddProduct()` for outputs
- For paired-end reads, use a grouping parent (e.g. `read_pair`) and set `parents={pair}` on both R1/R2 requirements
- `group_by=` in `TransformInstance()` controls how inputs are matched/grouped
- `context.ExecWithContainer(image=, cmd=)` runs commands inside the container
- Container paths: `context.Input(x).container` (path inside container), `.local` (path on host), `.external` (path from outside container)

## Writing tests

- Tests use `conftest.py` fixtures: `agent`, `base_resources`, `mlib`, `tmp_inputs`
- `tmp_inputs(["sequences.yml", ...])` creates a temporary `DataInstanceLibrary` with specified type libraries
- Use `inputs.AddItem(path, type)` for files, `inputs.AddValue(name, dict, type)` for JSON values
- Workflow generation tests: `agent.GenerateWorkflow(samples=, resources=, transforms=, targets=)`
- E2E tests: additionally call `agent.StageWorkflow()`, `agent.RunWorkflow()`, then `wait_for_workflow()`
- Mark E2E tests with `@pytest.mark.slow`
- Run tests with: `conda run -n msm_env pytest tests/<file>.py -k "<pattern>" -v`

## Driver scripts (`main/`)

Top-level scripts that exercise the library end-to-end (build inputs, plan, optionally stage/run). See `main/diamond_uniref50_from_assembly.py` for the minimal planning-only shape:

- mock module-level constants (e.g. `ASSEMBLY = Path("<assembly>")`) instead of argparse
- single `AddTypeLibrary` call for the input type, no guards, no error handling
- include `transforms/logistics` to let the planner auto-resolve external DBs (e.g. UniRef50)
- end with `task.plan.RenderDAG(out, format="svg")` for a planning-only driver

Longer drivers (`launch_dl_embeddings.py`, `probe_planner.py`, `render_dag.py`) keep the same structure but add CLI parsing, remote SshSource agents, and full stage/run/wait flows.

## Conda environment

- Use `msm_env` for running `msm build` and `pytest`
- `conda run -n msm_env <command>` or `conda activate msm_env`
