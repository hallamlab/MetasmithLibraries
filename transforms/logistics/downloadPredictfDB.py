from metasmith.python_api import *

lib   = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()
image = model.AddRequirement(lib.GetType("containers::predictf.oci"))
db    = model.AddProduct(lib.GetType("annotation::predictf_db"))

PREDICTF_REPO = "https://github.com/mdsufz/PredicTF.git"


def protocol(context: ExecutionContext):
    idb = context.Output(db)

    # PredicTF distributes its trained database as BacTFDB/ inside the repo:
    # a deepARG-format `database/v2/` (features.fasta/.dmnd/.gene.length) plus
    # the `model/` and `_predictf.xgdb` classifier files. predictf.py mounts
    # this directory at /predictf_db and hands it to deepARG.py via `--folder`.
    # The large model + DIAMOND files are tracked with git-lfs, so a plain
    # clone yields pointer stubs — `git lfs pull` materialises the real data.
    context.ExecWithContainer(
        image=image,
        cmd=f"""
            export GIT_LFS_SKIP_SMUDGE=0
            git clone --depth 1 {PREDICTF_REPO} PredicTF
            (cd PredicTF && git lfs install --local && git lfs pull)
            mkdir -p {idb.container}
            cp -r PredicTF/BacTFDB/. {idb.container}/
        """,
    )

    return ExecutionResult(
        manifest=[{db: idb.local}],
        success=(idb.local / "database" / "v2").exists(),
    )


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=image,
    labels=["local"],
    resources=Resources(
        cpus=2,
        memory=Size.GB(8),
        duration=Duration(hours=2),
    ),
)
