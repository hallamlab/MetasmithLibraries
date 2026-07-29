from pathlib import Path
from metasmith.python_api import *

lib   = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()
image = model.AddRequirement(lib.GetType("containers::diamond.oci"))  # shell only
ref   = model.AddProduct(lib.GetType("annotation::pathofact_db"))

# ===========================================================================
# STUB — NOT runnable as-is. PathoFact 2.0 needs its ~1.1 GB reference database
# (HMM profiles, DIAMOND DBs, MGE / toxin signatures) staged at runtime; the
# archive is published on Zenodo (record 14192463) and is NOT baked into the
# container image. Obtaining + unpacking that archive is deferred (see plan PG3
# / PG4 and container_builds/main/pathofact). This downloader only scaffolds the
# directory + a manifest so the transform graph resolves; replace it with the
# real Zenodo fetch + extract before running PathoFact for real.
# ===========================================================================
ZENODO_RECORD = "14192463"


def protocol(context: ExecutionContext):
    iref = context.Output(ref)

    iref.local.mkdir(parents=True, exist_ok=True)
    readme = iref.local / "TODO_PATHOFACT_DB.md"
    readme.write_text(
        "PathoFact 2.0 reference database — TODO.\n\n"
        "Populate this directory with the PathoFact2 database bundle "
        "(HMM profiles, DIAMOND DBs, MGE / toxin signatures) required at "
        "runtime by the PathoFact2 Snakemake workflow.\n\n"
        f"Source: Zenodo record {ZENODO_RECORD} "
        f"(https://zenodo.org/records/{ZENODO_RECORD}), ~1.1 GB.\n"
        "Download the archive, extract it here, and point PathoFact's "
        "config `db` at this directory.\n"
    )

    return ExecutionResult(
        manifest=[{ref: iref.local}],
        success=iref.local.exists(),
    )


TransformInstance(
    protocol=protocol,
    model=model,
    group_by=image,
    labels=["local"],
    resources=Resources(
        cpus=1,
        memory=Size.GB(2),
        duration=Duration(minutes=10),
    ),
)
