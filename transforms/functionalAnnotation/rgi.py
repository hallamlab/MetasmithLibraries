"""rgi — RGI/CARD main ARG detection on Prodigal proteins.

Runs on the full per-sample protein FASTA (sequences::orfs). RGI's ORF_ID
column carries the input protein header (k141_XXXXXX_N), so the original contig
ID is preserved for the downstream merge. CARD is provided pre-loaded as the
./localDB directory (annotation::card_db, built by downloadCardDB.py).
"""
from metasmith.python_api import *

lib = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()

image = model.AddRequirement(lib.GetType("containers::rgi.oci"))
orfs = model.AddRequirement(lib.GetType("sequences::orfs"))
card = model.AddRequirement(lib.GetType("annotation::card_db"))
out_results = model.AddProduct(lib.GetType("annotation::rgi_results"))


def protocol(context: ExecutionContext):
    iorfs = context.Input(orfs)
    icard = context.Input(card)
    iout = context.Output(out_results)

    threads = context.params.get("cpus", 8)

    # rgi main --local consumes ./localDB in the work dir; stage the prepared
    # CARD localDB there. RGI appends .txt to --output_file.
    context.LocalShell(f"cp -r {icard.external} ./localDB")
    context.ExecWithContainer(
        image=image,
        cmd=f"""
            rgi main \
                --input_sequence {iorfs.container} \
                --output_file rgi_out \
                --input_type protein \
                --local \
                -n {threads} \
                --include_loose \
                --clean
        """,
    )

    context.LocalShell(f"cp rgi_out.txt {iout.local}")

    return ExecutionResult(
        manifest=[{out_results: iout.local}],
        success=iout.local.exists(),
    )


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=orfs,
    resources=Resources(
        cpus=8,
        memory=Size.GB(16),
        duration=Duration(hours=4),
    ),
)
