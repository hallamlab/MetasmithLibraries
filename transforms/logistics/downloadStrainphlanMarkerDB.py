# StrainPhlAn needs the EXACT SGB marker index that produced the upstream
# taxonomy::metaphlan_sam profiles (mpa_vJan25_CHOCOPhlAnSGB_202503, hardcoded
# in metagenomics/taxonomy/strainphlan.py's MPA_INDEX) -- an index mismatch
# between the profile and sample2markers.py's marker db silently changes the
# species/marker set. downloadMetaphlanDB.py installs whatever --install
# resolves as "latest" at run time, which drifts across re-runs and container
# rebuilds, so it can't satisfy this. This transform pins the index instead,
# producing the annotation::metaphlan_db type strainphlan.py actually requires.
from metasmith.python_api import *

lib   = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()
image = model.AddRequirement(lib.GetType("containers::metaphlan.oci"))
out   = model.AddProduct(lib.GetType("annotation::metaphlan_db"))

MPA_INDEX = "mpa_vJan25_CHOCOPhlAnSGB_202503"


def protocol(context: ExecutionContext):
    iout = context.Output(out)
    threads = context.params.get('cpus')
    threads_arg = "" if threads is None else f"--nproc {threads}"

    context.ExecWithContainer(
        image=image,
        cmd=f"""
            mkdir -p {iout.container}
            metaphlan --install --index {MPA_INDEX} --bowtie2db {iout.container} {threads_arg}
        """,
    )
    return ExecutionResult(
        manifest=[{out: iout.local}],
        success=(iout.local / f"{MPA_INDEX}.pkl").exists(),
    )


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=image,
    resources=Resources(
        cpus=4,
        memory=Size.GB(16),
        duration=Duration(hours=6),
    ),
)
