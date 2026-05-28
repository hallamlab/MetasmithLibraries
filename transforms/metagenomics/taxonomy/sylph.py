from metasmith.python_api import *

lib     = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model   = Transform()
image   = model.AddRequirement(lib.GetType("containers::sylph.oci"))
db      = model.AddRequirement(lib.GetType("ref::sylph_db"))
pair    = model.AddRequirement(lib.GetType("sequences::read_pair"))
r1      = model.AddRequirement(lib.GetType("sequences::zipped_forward_short_reads"), parents={pair})
r2      = model.AddRequirement(lib.GetType("sequences::zipped_reverse_short_reads"), parents={pair})

profile = model.AddProduct(lib.GetType("taxonomy::sylph_profile"))

def protocol(context: ExecutionContext):
    idb      = context.Input(db)
    ir1      = context.Input(r1)
    ir2      = context.Input(r2)
    iprof    = context.Output(profile)

    threads  = context.params.get('cpus')
    threads_arg = "" if threads is None else f"-t {threads}"

    context.ExecWithContainer(
        image=image,
        cmd=f"""
            sylph profile {idb.container} \
                -1 {ir1.container} -2 {ir2.container} \
                {threads_arg} \
                -o {iprof.container}
        """
    )

    return ExecutionResult(
        manifest=[{
            profile: iprof.local,
        }],
        success=iprof.local.exists(),
    )

TransformInstance(
    protocol=protocol,
    model=model,
    group_by=pair,
    resources=Resources(
        cpus=4,
        memory=Size.GB(8),
        duration=Duration(hours=1),
    )
)
