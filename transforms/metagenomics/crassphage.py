"""crassphage — BBMap mapping of filtered reads to crAssphage NC_024711.

Human faecal contamination marker for source tracking. Maps the per-sample
filtered reads (sequences::clean_short_reads) to the crAssphage reference and
emits per-contig coverage stats. No contig_id dependency.
"""
from metasmith.python_api import *

lib = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()

image = model.AddRequirement(lib.GetType("containers::bbtools.oci"))
reads = model.AddRequirement(lib.GetType("sequences::clean_short_reads"))
ref = model.AddRequirement(lib.GetType("annotation::crassphage_ref"))
out_cov = model.AddProduct(lib.GetType("annotation::crassphage_coverage"))


def protocol(context: ExecutionContext):
    ireads = context.Input(reads)
    iref = context.Input(ref)
    iout = context.Output(out_cov)

    threads = context.params.get("cpus", 4)

    # nodisk=t keeps the (tiny) crAssphage index in memory; interleaved input is
    # auto-detected. covstats gives per-contig mapped depth/breadth.
    context.ExecWithContainer(
        image=image,
        cmd=f"""
            bbmap.sh \
                ref={iref.container} \
                in={ireads.container} \
                nodisk=t \
                threads={threads} \
                covstats={iout.container} \
                ambiguous=random
        """,
    )

    return ExecutionResult(
        manifest=[{out_cov: iout.local}],
        success=iout.local.exists(),
    )


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=reads,
    resources=Resources(
        cpus=4,
        memory=Size.GB(8),
        duration=Duration(hours=1),
    ),
)
