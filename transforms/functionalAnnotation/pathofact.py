"""pathofact — PathoFact 2.0 integrated ARG + VF + toxin + MGE prediction.

Runs on assembled contigs (sequences::assembly), calling ORFs internally, and
emits the four PathoFact prediction tables. Contig IDs (k141_XXXXXX) are carried
in each output's Contig column.

NOTE: BUILD-blocked. PathoFact 2.0 is a conda/Snakemake pipeline with no clean
biocontainer; the image (containers::pathofact.oci) and its bundled DBs
(annotation::pathofact_db) must be built in container_builds/main/pathofact
before this transform can run. The exact in-container invocation below is the
intended contract — finalise it against the built image's entrypoint.
"""
import glob
from pathlib import Path
from metasmith.python_api import *

lib = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()

image = model.AddRequirement(lib.GetType("containers::pathofact.oci"))
asm = model.AddRequirement(lib.GetType("sequences::assembly"))
db = model.AddRequirement(lib.GetType("annotation::pathofact_db"))
out_amr = model.AddProduct(lib.GetType("annotation::pathofact_amr"))
out_vf = model.AddProduct(lib.GetType("annotation::pathofact_vf"))
out_tox = model.AddProduct(lib.GetType("annotation::pathofact_tox"))
out_mge = model.AddProduct(lib.GetType("annotation::pathofact_mge"))


def protocol(context: ExecutionContext):
    iasm = context.Input(asm)
    idb = context.Input(db)
    oamr = context.Output(out_amr)
    ovf = context.Output(out_vf)
    otox = context.Output(out_tox)
    omge = context.Output(out_mge)

    threads = context.params.get("cpus", 16)

    # Entrypoint wrapper `pathofact` (defined by the container build) runs the
    # Snakemake pipeline end-to-end and writes results under pf_out/.
    context.ExecWithContainer(
        image=image,
        binds=[(idb.external, "/pathofact_db")],
        cmd=f"""
            pathofact \
                --input {iasm.container} \
                --db /pathofact_db \
                --outdir pf_out \
                --threads {threads}
        """,
    )

    def _grab(pattern, dest, header):
        hits = sorted(glob.glob(pattern))
        if hits:
            context.LocalShell(f"cp {hits[0]} {dest.local}")
        else:
            Path(dest.local).write_text(header)

    _grab("pf_out/**/*AMR*pred*.tsv", oamr, "Contig\tORF\tARG\tprediction\n")
    _grab("pf_out/**/*[Vv]irulence*.tsv", ovf, "Contig\tORF\tVF\tprediction\n")
    _grab("pf_out/**/*[Tt]oxin*.tsv", otox, "Contig\tORF\ttoxin\tprediction\n")
    _grab("pf_out/**/*MGE*.tsv", omge, "Contig\tORF\tMGE\tprediction\n")

    return ExecutionResult(
        manifest=[{
            out_amr: oamr.local,
            out_vf: ovf.local,
            out_tox: otox.local,
            out_mge: omge.local,
        }],
        success=all(p.local.exists() for p in (oamr, ovf, otox, omge)),
    )


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=asm,
    resources=Resources(
        cpus=16,
        memory=Size.GB(48),
        duration=Duration(hours=12),
    ),
)
