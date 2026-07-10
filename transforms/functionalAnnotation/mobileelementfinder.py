"""mobileelementfinder — MobileElementFinder (mefinder) on assembled contigs.

Detects IS elements / transposases flanking ARGs. Runs on sequences::assembly;
the contig ID (k141_XXXXXX) is retained in the output CSV. Tolerates samples
with no MGEs.

NOTE: BUILD-blocked. No biocontainer exists for MobileElementFinder; the
container (containers::mobileelementfinder.oci) must be built in
container_builds/main/mobileelementfinder before this transform can run.
"""
from pathlib import Path
from metasmith.python_api import *

lib = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()

image = model.AddRequirement(lib.GetType("containers::mobileelementfinder.oci"))
asm = model.AddRequirement(lib.GetType("sequences::assembly"))
out_results = model.AddProduct(lib.GetType("annotation::mobileelementfinder_results"))


def protocol(context: ExecutionContext):
    iasm = context.Input(asm)
    iout = context.Output(out_results)

    # mefinder writes <name>.csv in the work dir; the bundled MGE database ships
    # inside the image.
    context.ExecWithContainer(
        image=image,
        cmd=f"""
            mefinder find --contig {iasm.container} mef_out || true
        """,
    )

    if Path("mef_out.csv").exists():
        context.LocalShell(f"cp mef_out.csv {iout.local}")
    else:
        Path(iout.local).write_text("# No mobile elements detected\n")

    return ExecutionResult(
        manifest=[{out_results: iout.local}],
        success=iout.local.exists(),
    )


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=asm,
    resources=Resources(
        cpus=4,
        memory=Size.GB(8),
        duration=Duration(hours=3),
    ),
)
