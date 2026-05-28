from metasmith.python_api import *

lib     = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model   = Transform()
image   = model.AddRequirement(lib.GetType("containers::centrifuger.oci"))
img_bb  = model.AddRequirement(lib.GetType("containers::bbtools.oci"))
db      = model.AddRequirement(lib.GetType("ref::centrifuger_db"))
reads   = model.AddRequirement(lib.GetType("sequences::short_reads"))

classif = model.AddProduct(lib.GetType("taxonomy::centrifuger_classifications"))
kreport = model.AddProduct(lib.GetType("taxonomy::centrifuger_kreport"))
summary = model.AddProduct(lib.GetType("taxonomy::centrifuger_summary"))

def protocol(context: ExecutionContext):
    idb     = context.Input(db)
    ireads  = context.Input(reads)
    iclass  = context.Output(classif)
    ikrep   = context.Output(kreport)
    isumm   = context.Output(summary)

    threads = context.params.get('cpus')
    threads_arg = "" if threads is None else f"-t {threads}"

    context.ExecWithContainer(
        image=img_bb,
        cmd=f"""
            reformat.sh in={ireads.container} \
                out1=split_r1.fq.gz out2=split_r2.fq.gz
        """
    )

    context.ExecWithContainer(
        image=image,
        cmd=f"""
            centrifuger -x {idb.container} \
                -1 split_r1.fq.gz -2 split_r2.fq.gz \
                {threads_arg} > {iclass.container}

            centrifuger-kreport -x {idb.container} {iclass.container} > {ikrep.container}

            centrifuger-quant -x {idb.container} -c {iclass.container} 2>/dev/null > {isumm.container}
        """
    )

    return ExecutionResult(
        manifest=[{
            classif: iclass.local,
            kreport: ikrep.local,
            summary: isumm.local,
        }],
        success=ikrep.local.exists() and iclass.local.exists(),
    )

TransformInstance(
    protocol=protocol,
    model=model,
    group_by=reads,
    resources=Resources(
        cpus=8,
        memory=Size.GB(32),
        duration=Duration(hours=2),
    )
)
