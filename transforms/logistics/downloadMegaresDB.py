from metasmith.python_api import *

lib   = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()
image = model.AddRequirement(lib.GetType("containers::diamond.oci"))
db    = model.AddProduct(lib.GetType("annotation::megares_diamond_db"))

# MEGARes v3.00 nucleotide+protein DB. The DIAMOND path needs protein FASTA;
# MEGARes ships a single combined FASTA — diamond makedb reads it as protein.
MEGARES_URL = "https://www.meglab.org/downloads/megares_v3.00/megares_database_v3.00.fasta"


def protocol(context: ExecutionContext):
    idb = context.Output(db)

    # mounts the .dmnd's parent at /db and references by name (tcdb pattern),
    # so the product is a single `.dmnd` file (ext: dmnd).
    context.ExecWithContainer(
        image=image,
        cmd=f"""
            wget -q --no-check-certificate {MEGARES_URL} -O megares.fasta
            diamond makedb --in megares.fasta -d megares
            mv megares.dmnd {idb.container}
        """,
    )

    return ExecutionResult(
        manifest=[{db: idb.local}],
        success=idb.local.exists(),
    )


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=image,
    labels=["local"],
    resources=Resources(
        cpus=2,
        memory=Size.GB(8),
        duration=Duration(hours=1),
    ),
)
