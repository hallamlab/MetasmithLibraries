from metasmith.python_api import *

lib     = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model   = Transform()
image   = model.AddRequirement(lib.GetType("containers::metaphlan.oci"))
db      = model.AddRequirement(lib.GetType("ref::metaphlan_db"))
pair    = model.AddRequirement(lib.GetType("sequences::read_pair"))
r1      = model.AddRequirement(lib.GetType("sequences::zipped_forward_short_reads"), parents={pair})
r2      = model.AddRequirement(lib.GetType("sequences::zipped_reverse_short_reads"), parents={pair})

profile = model.AddProduct(lib.GetType("taxonomy::metaphlan_profile"))
sam     = model.AddProduct(lib.GetType("taxonomy::metaphlan_sam"))

def protocol(context: ExecutionContext):
    idb      = context.Input(db)
    ir1      = context.Input(r1)
    ir2      = context.Input(r2)
    iprof    = context.Output(profile)
    isam     = context.Output(sam)

    threads  = context.params.get('cpus')
    threads_arg = "" if threads is None else f"--nproc {threads}"

    # v4.2 quirks: --offline avoids compute-node firewall hits; comma-joined
    # paired input requires --mapout (so we capture the bowtie2 SAM as a
    # companion product); --db_dir replaces the v4.1 --bowtie2db flag.
    context.ExecWithContainer(
        image=image,
        cmd=f"""
            metaphlan {ir1.container},{ir2.container} \
                --input_type fastq --offline \
                --db_dir {idb.container} {threads_arg} \
                -o {iprof.container} \
                --mapout {isam.container}
        """
    )

    return ExecutionResult(
        manifest=[{
            profile: iprof.local,
            sam:     isam.local,
        }],
        success=iprof.local.exists(),
    )

TransformInstance(
    protocol=protocol,
    model=model,
    group_by=pair,
    resources=Resources(
        cpus=8,
        memory=Size.GB(64),  # bowtie2 indexes are ~33 GB; 32 GB OOMs
        duration=Duration(hours=2),
    )
)
