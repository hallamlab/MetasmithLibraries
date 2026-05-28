from metasmith.python_api import *

lib     = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model   = Transform()
image   = model.AddRequirement(lib.GetType("containers::centrifuger.oci"))
db      = model.AddRequirement(lib.GetType("ref::centrifuger_db"))
pair    = model.AddRequirement(lib.GetType("sequences::read_pair"))
r1      = model.AddRequirement(lib.GetType("sequences::zipped_forward_short_reads"), parents={pair})
r2      = model.AddRequirement(lib.GetType("sequences::zipped_reverse_short_reads"), parents={pair})

classif = model.AddProduct(lib.GetType("taxonomy::centrifuger_classifications"))
kreport = model.AddProduct(lib.GetType("taxonomy::centrifuger_kreport"))
summary = model.AddProduct(lib.GetType("taxonomy::centrifuger_summary"))

def protocol(context: ExecutionContext):
    idb     = context.Input(db)
    ir1     = context.Input(r1)
    ir2     = context.Input(r2)
    iclass  = context.Output(classif)
    ikrep   = context.Output(kreport)
    isumm   = context.Output(summary)

    threads = context.params.get('cpus')
    threads_arg = "" if threads is None else f"-t {threads}"

    context.ExecWithContainer(
        image=image,
        cmd=f"""
            centrifuger -x {idb.container} \
                -1 {ir1.container} -2 {ir2.container} \
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
    group_by=pair,
    resources=Resources(
        cpus=8,
        memory=Size.GB(32),
        duration=Duration(hours=2),
    )
)
