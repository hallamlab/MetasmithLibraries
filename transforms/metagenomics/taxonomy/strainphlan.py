"""strainphlan — per-sample consensus markers from the MetaPhlAn SAM.

First (per-sample) step of StrainPhlAn: sample2markers.py reconstructs consensus
marker sequences from the MetaPhlAn bowtie2 SAM (taxonomy::metaphlan_sam). The
cross-sample `strainphlan` tree-building step is an aggregate run downstream and
is gated on relevant pathogens appearing (conditional per Antonio's table).
"""
import glob
from pathlib import Path
from metasmith.python_api import *

lib = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()

image = model.AddRequirement(lib.GetType("containers::metaphlan.oci"))
sam = model.AddRequirement(lib.GetType("taxonomy::metaphlan_sam"))
out_markers = model.AddProduct(lib.GetType("annotation::strainphlan_consensus_markers"))


def protocol(context: ExecutionContext):
    isam = context.Input(sam)
    iout = context.Output(out_markers)

    threads = context.params.get("cpus", 4)

    # sample2markers.py emits <stem>.pkl into the output dir.
    context.ExecWithContainer(
        image=image,
        cmd=f"""
            mkdir -p markers
            sample2markers.py -i {isam.container} -o markers -n {threads}
        """,
    )

    pkls = sorted(glob.glob("markers/*.pkl"))
    if pkls:
        context.LocalShell(f"cp {pkls[0]} {iout.local}")
    else:
        Path(iout.local).touch()

    return ExecutionResult(
        manifest=[{out_markers: iout.local}],
        success=iout.local.exists(),
    )


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=sam,
    resources=Resources(
        cpus=4,
        memory=Size.GB(8),
        duration=Duration(hours=2),
    ),
)
