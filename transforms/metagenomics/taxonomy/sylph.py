from metasmith.python_api import *

lib     = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model   = Transform()
image   = model.AddRequirement(lib.GetType("containers::sylph.oci"))
img_bb  = model.AddRequirement(lib.GetType("containers::bbtools.oci"))
db      = model.AddRequirement(lib.GetType("ref::sylph_db"))
reads   = model.AddRequirement(lib.GetType("sequences::short_reads"))

profile = model.AddProduct(lib.GetType("taxonomy::sylph_profile"))

def protocol(context: ExecutionContext):
    idb      = context.Input(db)
    ireads   = context.Input(reads)
    iprof    = context.Output(profile)

    threads  = context.params.get('cpus')
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
            sylph profile {idb.container} \
                -1 split_r1.fq.gz -2 split_r2.fq.gz \
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
    group_by=reads,
    resources=Resources(
        cpus=4,
        memory=Size.GB(8),
        duration=Duration(hours=1),
    )
)
