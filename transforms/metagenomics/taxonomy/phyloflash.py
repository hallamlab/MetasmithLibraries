from metasmith.python_api import *

lib     = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model   = Transform()
image   = model.AddRequirement(lib.GetType("containers::phyloflash.oci"))
db      = model.AddRequirement(lib.GetType("ref::phyloflash_db"))
pair    = model.AddRequirement(lib.GetType("sequences::read_pair"))
r1      = model.AddRequirement(lib.GetType("sequences::zipped_forward_short_reads"), parents={pair})
r2      = model.AddRequirement(lib.GetType("sequences::zipped_reverse_short_reads"), parents={pair})

html    = model.AddProduct(lib.GetType("taxonomy::phyloflash_report_html"))
summary = model.AddProduct(lib.GetType("taxonomy::phyloflash_summary"))
ntu     = model.AddProduct(lib.GetType("taxonomy::phyloflash_ntu_abundance"))
ssu     = model.AddProduct(lib.GetType("taxonomy::phyloflash_ssu_spades"))

def protocol(context: ExecutionContext):
    idb      = context.Input(db)
    ir1      = context.Input(r1)
    ir2      = context.Input(r2)
    ihtml    = context.Output(html)
    isumm    = context.Output(summary)
    intu     = context.Output(ntu)
    issu     = context.Output(ssu)

    threads  = context.params.get('cpus')
    threads_arg = "" if threads is None else f"-CPUs {threads}"

    # phyloFlash writes <lib>.* into CWD; use a stable -lib prefix then
    # move the four products. SPAdes is default-on, EMIRGE default-off in
    # v3.4 — no flag needed to skip it. -html requests the HTML report.
    context.ExecWithContainer(
        image=image,
        cmd=f"""
            phyloFlash.pl -lib pf_out \
                -read1 {ir1.container} -read2 {ir2.container} \
                -dbhome {idb.container} {threads_arg} \
                -html
            mv pf_out.phyloFlash.html             {ihtml.container}
            mv pf_out.phyloFlash.report.csv       {isumm.container}
            mv pf_out.phyloFlash.NTUabundance.csv {intu.container}
            mv pf_out.spades_rRNAs.final.fasta    {issu.container}
        """
    )

    return ExecutionResult(
        manifest=[{
            html:    ihtml.local,
            summary: isumm.local,
            ntu:     intu.local,
            ssu:     issu.local,
        }],
        success=isumm.local.exists() and intu.local.exists(),
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
