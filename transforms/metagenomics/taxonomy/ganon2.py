from metasmith.python_api import *

lib     = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model   = Transform()
image   = model.AddRequirement(lib.GetType("containers::ganon.oci"))
db      = model.AddRequirement(lib.GetType("ref::ganon2_db"))
pair    = model.AddRequirement(lib.GetType("sequences::read_pair"))
r1      = model.AddRequirement(lib.GetType("sequences::zipped_forward_short_reads"), parents={pair})
r2      = model.AddRequirement(lib.GetType("sequences::zipped_reverse_short_reads"), parents={pair})

classif = model.AddProduct(lib.GetType("taxonomy::ganon2_classifications"))
report  = model.AddProduct(lib.GetType("taxonomy::ganon2_report"))

def protocol(context: ExecutionContext):
    idb      = context.Input(db)
    ir1      = context.Input(r1)
    ir2      = context.Input(r2)
    iclass   = context.Output(classif)
    irep     = context.Output(report)

    threads  = context.params.get('cpus')
    threads_arg = "" if threads is None else f"--threads {threads}"

    # ganon classify writes <prefix>.rep and <prefix>.tre alongside each other.
    # Use a stable prefix in the container's CWD then move both outputs.
    context.ExecWithContainer(
        image=image,
        cmd=f"""
            ganon classify --db-prefix {idb.container} \
                --paired-reads {ir1.container} {ir2.container} \
                --output-prefix ganon2_out {threads_arg}
            mv ganon2_out.rep {iclass.container}
            mv ganon2_out.tre {irep.container}
        """
    )

    return ExecutionResult(
        manifest=[{
            classif: iclass.local,
            report:  irep.local,
        }],
        success=irep.local.exists(),
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
