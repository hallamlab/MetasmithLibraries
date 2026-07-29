"""amrfinderplus — NCBI AMRFinderPlus protein search (second-layer ARG validation).

Runs on the per-sample Prodigal proteins (sequences::orfs). The Protein_id
column echoes the input header (k141_XXXXXX_N), preserving the contig ID.
"""
from metasmith.python_api import *

lib = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()

image = model.AddRequirement(lib.GetType("containers::amrfinderplus.oci"))
orfs = model.AddRequirement(lib.GetType("sequences::orfs"))
db = model.AddRequirement(lib.GetType("annotation::amrfinderplus_db"))
out_results = model.AddProduct(lib.GetType("annotation::amrfinderplus_results"))


def protocol(context: ExecutionContext):
    iorfs = context.Input(orfs)
    idb = context.Input(db)
    iout = context.Output(out_results)

    threads = context.params.get("cpus", 8)

    context.ExecWithContainer(
        image=image,
        binds=[(idb.external, "/amrdb")],
        cmd=f"""
            amrfinder \
                -p {iorfs.container} \
                -d /amrdb \
                --plus \
                --threads {threads} \
                -o {iout.container}
        """,
    )

    return ExecutionResult(
        manifest=[{out_results: iout.local}],
        success=iout.local.exists(),
    )


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=orfs,
    resources=Resources(
        cpus=8,
        memory=Size.GB(8),
        duration=Duration(hours=2),
    ),
)
