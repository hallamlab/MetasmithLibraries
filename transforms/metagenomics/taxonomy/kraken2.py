from metasmith.python_api import *

lib     = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model   = Transform()
img_k2  = model.AddRequirement(lib.GetType("containers::kraken2.oci"))
img_brk = model.AddRequirement(lib.GetType("containers::bracken.oci"))
db      = model.AddRequirement(lib.GetType("ref::kraken2_db"))
pair    = model.AddRequirement(lib.GetType("sequences::read_pair"))
r1      = model.AddRequirement(lib.GetType("sequences::zipped_forward_short_reads"), parents={pair})
r2      = model.AddRequirement(lib.GetType("sequences::zipped_reverse_short_reads"), parents={pair})

classif = model.AddProduct(lib.GetType("taxonomy::kraken2_classifications"))
kreport = model.AddProduct(lib.GetType("taxonomy::kraken2_report"))
bspec   = model.AddProduct(lib.GetType("taxonomy::bracken_species"))
breport = model.AddProduct(lib.GetType("taxonomy::bracken_kreport"))

def protocol(context: ExecutionContext):
    idb     = context.Input(db)
    ir1     = context.Input(r1)
    ir2     = context.Input(r2)
    iclass  = context.Output(classif)
    ikrep   = context.Output(kreport)
    ibspec  = context.Output(bspec)
    ibrep   = context.Output(breport)

    threads = context.params.get('cpus')
    threads_arg = "" if threads is None else f"--threads {threads}"

    context.ExecWithContainer(
        image=img_k2,
        cmd=f"""
            kraken2 --paired --db {idb.container} {threads_arg} \
                --report {ikrep.container} \
                --output {iclass.container} \
                {ir1.container} {ir2.container}
        """
    )

    context.ExecWithContainer(
        image=img_brk,
        cmd=f"""
            bracken -d {idb.container} \
                -i {ikrep.container} \
                -o {ibspec.container} \
                -w {ibrep.container} \
                -r 150 -l S
        """
    )

    return ExecutionResult(
        manifest=[{
            classif: iclass.local,
            kreport: ikrep.local,
            bspec:   ibspec.local,
            breport: ibrep.local,
        }],
        success=ikrep.local.exists() and ibspec.local.exists(),
    )

TransformInstance(
    protocol=protocol,
    model=model,
    group_by=pair,
    resources=Resources(
        cpus=8,
        memory=Size.GB(96),
        duration=Duration(hours=2),
    )
)
