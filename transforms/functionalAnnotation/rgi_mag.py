"""rgi_mag — RGI/CARD ARG detection on COMEBin MAG contigs.

Second RGI pass requested by Antonio: run on the per-MAG FASTA
(sequences::comebin_bin_fasta) in contig mode. MAG FASTA headers are the same
k141_XXXXXX contigs, preserved in RGI's output. One output per MAG.
"""
from metasmith.python_api import *

lib = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()

image = model.AddRequirement(lib.GetType("containers::rgi.oci"))
mag = model.AddRequirement(lib.GetType("sequences::comebin_bin_fasta"))
card = model.AddRequirement(lib.GetType("annotation::card_db"))
out_results = model.AddProduct(lib.GetType("annotation::rgi_mag_results"))


def protocol(context: ExecutionContext):
    imag = context.Input(mag)
    icard = context.Input(card)
    iout = context.Output(out_results)

    threads = context.params.get("cpus", 4)

    # Contig mode: RGI calls ORFs internally but keeps the contig name as the
    # ORF_ID prefix, so k141_XXXXXX is retained.
    context.LocalShell(f"cp -r {icard.external} ./localDB")
    context.ExecWithContainer(
        image=image,
        cmd=f"""
            rgi main \
                --input_sequence {imag.container} \
                --output_file rgi_mag_out \
                --input_type contig \
                --local \
                --num_threads {threads} \
                --include_loose \
                --clean
        """,
    )

    context.LocalShell(f"cp rgi_mag_out.txt {iout.local}")

    return ExecutionResult(
        manifest=[{out_results: iout.local}],
        success=iout.local.exists(),
    )


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=mag,
    resources=Resources(
        cpus=4,
        memory=Size.GB(8),
        duration=Duration(hours=2),
    ),
)
