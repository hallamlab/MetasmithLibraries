from pathlib import Path
from metasmith.python_api import *

lib     = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model   = Transform()
pan     = model.AddRequirement(lib.GetType("pangenome::pangenome"))
gbk     = model.AddRequirement(lib.GetType("sequences::gbk"), parents={pan})
image   = model.AddRequirement(lib.GetType("env::ppanggolin.env"))
matrix  = model.AddProduct(lib.GetType("pangenome::ppanggolin_matrix"))
pg      = model.AddProduct(lib.GetType("pangenome::ppanggolin_raw"))

def protocol(context: ExecutionContext):
    dep_paths=context.InputGroup(gbk)

    gb_list = Path("genbank_manifest.list")
    with open(gb_list, "w") as f:
        for p in dep_paths:
            # name from the GenBank `  ORGANISM` line -> `genus species PCCNNNN`
            # (kept hyphenated here so the manifest stays whitespace-safe; the
            # heatmap reintroduces spaces for display). first record wins.
            name = None
            with open(p.local) as g:
                for i, l in enumerate(g):
                    if i > 15: break
                    if "ORGANISM" not in l: continue
                    name = l.replace("ORGANISM", "").strip()
                    name = name.replace("[", "").replace("]", "")
                    for x in ",.'\"":
                        name = name.replace(x, "")
                    name = "-".join(name.split())
                    break
            if not name: name = p.local.name
            f.write(name+"\t"+str(p.container)+"\n")

    ipg = context.Output(pg)
    threads = context.params.get('cpus')
    threads = "" if threads is None else f"--cpu {threads}"
    context.ExecWithEnv().ifContainerDo(
        env=image,
        cmd=f"ppanggolin all --anno {gb_list} --identity 0.3 --coverage 0.8 {threads} --output {ipg.container}",
    )
    imatrix = context.Output(matrix)
    context.LocalShell(f"cp {ipg.local}/matrix.csv {imatrix.local}")
    return ExecutionResult(
        manifest=[
            {
                pg: ipg.local,
                matrix: imatrix.local
            },
        ],
        success=ipg.local.exists() and imatrix.local.exists(),
    )

TransformInstance(
    protocol=protocol,
    model=model,
    group_by=pan,
    resources=Resources(
        cpus=4,
        memory=Size.GB(8),
        duration=Duration(hours=3),
    )
)
