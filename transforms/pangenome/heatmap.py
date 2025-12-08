from pathlib import Path
from metasmith.python_api import *

lib     = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model   = Transform()
image   = model.AddRequirement(lib.GetType("containers::python_for_data_science.oci"))
clust   = model.AddRequirement(lib.GetType("lib::hierarchical_clustering.py"))
clust   = model.AddRequirement(lib.GetType("lib::local"))
script  = model.AddRequirement(lib.GetType("lib::pangenome_heatmap.py"))
matrix  = model.AddRequirement(lib.GetType("pangenome::ppanggolin_matrix"))
out     = model.AddProduct(lib.GetType("pangenome::heatmap"))

def protocol(context: ExecutionContext):
    imatrix=context.Input(matrix)
    iscript=context.Input(script)
    iout=context.Output(out)
    context.ExecWithContainer(
        image=image,
        cmd=f"""\
            python {iscript.container} {imatrix.container} {iout.container}.svg && mv {iout.container}.svg {iout.container}
        """,
    )

    return ExecutionResult(
        manifest=[
            {
                out: iout.local,
            },
        ],
        success=iout.local.exists(),
    )

TransformInstance(
    protocol=protocol,
    model=model,
    group_by=matrix,
    resources=Resources(
        cpus=1,
        memory=Size.GB(4),
        duration=Duration(hours=1),
    )
)
