from metasmith.python_api import *

lib     = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model   = Transform()
dep     = model.AddRequirement(lib.GetType("ncbi::genomeAccession"))
image   = model.AddRequirement(lib.GetType("containers::ncbi-datasets.oci"))
fna     = model.AddProduct(lib.GetType("sequences::genome-like"))
faa     = model.AddProduct(lib.GetType("sequences::orfs"))
gff     = model.AddProduct(lib.GetType("sequences::gff"))
gbk     = model.AddProduct(lib.GetType("sequences::gbk"))

def protocol(context: ExecutionContext):
    dep_path=context.Input(dep)
    fna_path=context.Output(fna)

    context.ExecWithContainer(
        image=image,
        cmd=f"""\
            datasets download genome accession GCF_000005845.2 \
                --include gff3,rna,cds,protein,genome,seq-report
        """,
    )

    return ExecutionResult(
        manifest=[
            {
                fna: dep_path.local,
            },
        ],
        success=False,
    )

TransformInstance(
    protocol=protocol,
    model=model,
    group_by=dep,
    output_signature={
        fna: "genome.fna",
        gbk: "genome.gbk",
        faa: "orfs.faa",
        gff: "orfs.gff",
    },
)
