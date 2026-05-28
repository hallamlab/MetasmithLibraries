from metasmith.python_api import *

lib     = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model   = Transform()
img_k2  = model.AddRequirement(lib.GetType("containers::kraken2.oci"))
img_brk = model.AddRequirement(lib.GetType("containers::bracken.oci"))
img_bb  = model.AddRequirement(lib.GetType("containers::bbtools.oci"))
db      = model.AddRequirement(lib.GetType("ref::kraken2_db"))
reads   = model.AddRequirement(lib.GetType("sequences::short_reads"))

classif = model.AddProduct(lib.GetType("taxonomy::kraken2_classifications"))
kreport = model.AddProduct(lib.GetType("taxonomy::kraken2_report"))
bspec   = model.AddProduct(lib.GetType("taxonomy::bracken_species"))
breport = model.AddProduct(lib.GetType("taxonomy::bracken_kreport"))

def protocol(context: ExecutionContext):
    idb     = context.Input(db)
    ireads  = context.Input(reads)
    iclass  = context.Output(classif)
    ikrep   = context.Output(kreport)
    ibspec  = context.Output(bspec)
    ibrep   = context.Output(breport)

    threads = context.params.get('cpus')
    threads_arg = "" if threads is None else f"--threads {threads}"

    # kraken2 has no --interleaved mode: split via bbtools first.
    context.ExecWithContainer(
        image=img_bb,
        cmd=f"""
            reformat.sh in={ireads.container} \
                out1=split_r1.fq.gz out2=split_r2.fq.gz
        """
    )

    context.ExecWithContainer(
        image=img_k2,
        cmd=f"""
            kraken2 --paired --db {idb.container} {threads_arg} \
                --report {ikrep.container} \
                --output {iclass.container} \
                split_r1.fq.gz split_r2.fq.gz
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
    group_by=reads,
    resources=Resources(
        cpus=8,
        memory=Size.GB(96),
        duration=Duration(hours=2),
    )
)
