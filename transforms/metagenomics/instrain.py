"""instrain — inStrain profile for per-MAG microdiversity / strain sharing.

Profiles a sample's read alignment (alignment::bam) against its assembly
contigs, partitioned into MAGs via the COMEBin contig-to-bin table. Contig IDs
(k141_XXXXXX) come straight from the assembly/bam.

NOTE: conditional + BAM-limited. Only the 12 gapfill samples currently have
BAMs published under assembly/alignment_bams; the other 89 would need re-mapping
(out of scope). Run only if cross-lake strain sharing is a key finding.
"""
from pathlib import Path
from metasmith.python_api import *

lib = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()

image = model.AddRequirement(lib.GetType("containers::instrain.oci"))
asm = model.AddRequirement(lib.GetType("sequences::assembly"))
bam = model.AddRequirement(lib.GetType("alignment::bam"), parents={asm})
stb = model.AddRequirement(lib.GetType("binning::comebin_contig_to_bin_table"), parents={asm})
out_profile = model.AddProduct(lib.GetType("annotation::instrain_profile"))
out_genome = model.AddProduct(lib.GetType("annotation::instrain_genome_info"))


def protocol(context: ExecutionContext):
    iasm = context.Input(asm)
    ibam = context.Input(bam)
    istb = context.Input(stb)
    iprofile = context.Output(out_profile)
    igenome = context.Output(out_genome)

    threads = context.params.get("cpus", 8)

    # inStrain wants a headerless scaffold<tab>bin file; our contig_to_bin table
    # carries a "contig\tbin" header, so strip it.
    context.ExecWithContainer(
        image=image,
        cmd=f"""
            tail -n +2 {istb.container} > stb.tsv || cp {istb.container} stb.tsv
            inStrain profile \
                {ibam.container} \
                {iasm.container} \
                -o instrain_out \
                -p {threads} \
                -s stb.tsv \
                --database_mode
        """,
    )

    Path("instrain_out").rename(iprofile.local)
    gi = iprofile.local / "output" / "instrain_out_genome_info.tsv"
    if gi.exists():
        context.LocalShell(f"cp {gi} {igenome.local}")
    else:
        Path(igenome.local).write_text("genome\tcoverage\tbreadth\tnucl_diversity\n")

    return ExecutionResult(
        manifest=[{out_profile: iprofile.local, out_genome: igenome.local}],
        success=iprofile.local.exists() and igenome.local.exists(),
    )


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=asm,
    resources=Resources(
        cpus=8,
        memory=Size.GB(24),
        duration=Duration(hours=6),
    ),
)
