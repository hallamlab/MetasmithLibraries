import glob
import os
from pathlib import Path
import shutil
from metasmith.python_api import *

lib     = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model   = Transform()
lst     = model.AddRequirement(lib.GetType("ncbi::accessionList"))
gbk     = model.AddRequirement(lib.GetType("sequences::gbk"), parents={lst})
image   = model.AddRequirement(lib.GetType("containers::ppanggolin.oci"))
pg      = model.AddProduct(lib.GetType("pangenome::ppanggolinRaw"))

def protocol(context: ExecutionContext):
    dep_paths=context.InputGroup(gbk)

    gb_list = Path("genbank_manifest")
    with open(gb_list, "w") as f:
        for p in dep_paths:
            p = p.local
            f.write(p.stem+"\t"+str(p)+"\n")

    pg_out = context.Output(pg)
    threads = context.params.get('cpus')
    threads = "" if threads is None else f"--cpu {threads}"
    context.ExecWithContainer(
        image=image,
        cmd=f"ppanggolin all --anno {gb_list} {threads} --output {pg_out.container}",
    )

    return ExecutionResult(
        manifest=[
            {
                pg: pg_out.local,
            },
        ],
        success=pg_out.local.exists(),
    )

TransformInstance(
    protocol=protocol,
    model=model,
    group_by=lst,
    output_signature={
        pg: "ppanggolin_out",
    },
    resources=Resources(
        cpus=4,
        memory=Size.GB(8),
        duration=Duration(hours=3),
    )
)
