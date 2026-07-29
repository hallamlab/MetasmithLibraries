from pathlib import Path
from metasmith.python_api import *

lib   = TransformInstanceLibrary.ResolveParentLibrary(__file__)
model = Transform()
image = model.AddRequirement(lib.GetType("containers::diamond.oci"))  # shell only
ref   = model.AddProduct(lib.GetType("annotation::feast_sources"))

# ===========================================================================
# STUB — NOT runnable as-is. FEAST source tracking needs curated external
# community profiles (human gut, livestock, wildlife, soil, freshwater) from
# MGnify / EMP, formatted to a FEAST source OTU/species table. That curation is
# deferred (see plan "Still unsure about" + container_builds/main/feast). This
# downloader only scaffolds the directory + a manifest so the transform graph
# resolves; finalise the sources before running FEAST for real.
# ===========================================================================
SOURCES = [
    "human_gut", "livestock", "wildlife", "soil", "freshwater",
]


def protocol(context: ExecutionContext):
    iref = context.Output(ref)

    iref.local.mkdir(parents=True, exist_ok=True)
    readme = iref.local / "TODO_SOURCES.md"
    readme.write_text(
        "FEAST external source profiles — TODO.\n\n"
        "Populate this directory with a curated source OTU/species abundance "
        "table covering:\n"
        + "".join(f"  - {s}\n" for s in SOURCES)
        + "\nSource candidates: MGnify (mgnify.org), EMP (earthmicrobiome.org).\n"
        "Format to a FEAST source matrix (samples x taxa) aligned to the "
        "MetaPhlAn species table used as the sink.\n"
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
