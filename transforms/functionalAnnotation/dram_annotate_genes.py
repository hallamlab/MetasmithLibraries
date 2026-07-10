from metasmith.python_api import *

lib = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()

image = model.AddRequirement(lib.GetType("containers::dram.oci"))
orfs  = model.AddRequirement(lib.GetType("sequences::orf_chunk"))
db    = model.AddRequirement(lib.GetType("annotation::dram_db"))
out   = model.AddProduct(lib.GetType("annotation::dram_annotations_chunk"))


def protocol(context: ExecutionContext):
    iorfs  = context.Input(orfs)
    idb    = context.Input(db)
    iannot = context.Output(out)

    threads = context.params.get("cpus", 8)
    annot_dir = "dram_annot"

    # The dram_db is bound at /db, but DRAM.config stores *absolute* DB paths
    # baked in at build time — possibly on another machine (e.g. a database
    # cloned across clusters). Trusting the shipped paths makes the DB
    # non-relocatable. Instead we regenerate the config at run time: read
    # whatever config ships in the DB dir, then repoint every path onto the
    # /db mount (dirname -> /db, basename kept so DB-version-specific filenames
    # survive). This works for any dram_db regardless of where/how it was built.
    #
    # DRAM 1.5.0 bug: annotate_called_genes_cmd() doesn't accept config_loc
    # but argparse always passes it (even as None), crashing annotate_genes.
    # Workaround: write a wrapper script and call annotate_called_genes()
    # directly, which DOES accept config_loc. Using a script file avoids
    # shell quoting issues with inline python -c inside ExecWithContainer.
    context.LocalShell("""cat > _run_dram.py << 'DRAMPY'
import os, json
os.environ["HOME"] = "/tmp"

annot_dir = os.environ["DRAM_ANNOT_DIR"]
threads   = int(os.environ["DRAM_THREADS"])

# Repoint every absolute DB path in the shipped config onto the /db mount.
with open("/db/DRAM.config") as fh:
    cfg = json.load(fh)

def repoint(o):
    if isinstance(o, dict):
        return {k: repoint(v) for k, v in o.items()}
    if isinstance(o, str) and o.startswith("/"):
        return "/db/" + os.path.basename(o)
    return o

with open("/tmp/DRAM.config", "w") as fh:
    json.dump(repoint(cfg), fh)

from mag_annotator.annotate_bins import annotate_called_genes
annotate_called_genes(
    ["input.clean.faa"],
    annot_dir,
    threads=threads,
    config_loc="/tmp/DRAM.config",
)
DRAMPY""")

    context.ExecWithContainer(
        image=image,
        binds=[(idb.external, "/db")],
        cmd=f"""
            export DRAM_ANNOT_DIR={annot_dir}
            export DRAM_THREADS={threads}
            sed '/^[^>]/s/\\*//g' {iorfs.container} > input.clean.faa
            python3 _run_dram.py
        """,
    )

    context.LocalShell(f"cp {annot_dir}/annotations.tsv {iannot.local}")

    return ExecutionResult(
        manifest=[
            {
                out: iannot.local,
            },
        ],
        success=iannot.local.exists(),
    )


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=orfs,
    resources=Resources(
        cpus=8,
        memory=Size.GB(64),
        duration=Duration(hours=12),
    ),
)
