"""feast — FEAST microbial source tracking.

Estimates the contribution of external source environments (human gut,
livestock, wildlife, soil, freshwater) to each sample's community, using the
sample's MetaPhlAn species profile (taxonomy::metaphlan_profile) as the sink and
the curated source matrix (annotation::feast_sources) as sources. No contig_id
dependency.

NOTE: BUILD-blocked + data-blocked.
  - Container (containers::feast.oci) is an R image to be built in
    container_builds/main/feast (over the workspace_r base).
  - Sources (annotation::feast_sources) are an external curated dataset that is
    currently only stubbed (see downloadFeastSources.py). Finalise both before
    running FEAST for real.
The in-container invocation below is the intended contract.
"""
from pathlib import Path
from metasmith.python_api import *

lib = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()

image = model.AddRequirement(lib.GetType("containers::feast.oci"))
profile = model.AddRequirement(lib.GetType("taxonomy::metaphlan_profile"))
sources = model.AddRequirement(lib.GetType("annotation::feast_sources"))
out_props = model.AddProduct(lib.GetType("annotation::feast_proportions"))


def protocol(context: ExecutionContext):
    iprofile = context.Input(profile)
    isources = context.Input(sources)
    iout = context.Output(out_props)

    # Wrapper `FEAST` (defined by the container build) aligns the sink profile to
    # the source matrix and runs the EM estimator, writing a proportions table.
    context.ExecWithContainer(
        image=image,
        binds=[(isources.external, "/feast_sources")],
        cmd=f"""
            FEAST \
                --sink {iprofile.container} \
                --sources /feast_sources \
                --out {iout.container}
        """,
    )

    if not iout.local.exists():
        Path(iout.local).write_text("source\tproportion\n")

    return ExecutionResult(
        manifest=[{out_props: iout.local}],
        success=iout.local.exists(),
    )


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=profile,
    resources=Resources(
        cpus=2,
        memory=Size.GB(8),
        duration=Duration(hours=1),
    ),
)
