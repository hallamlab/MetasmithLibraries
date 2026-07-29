#!/usr/bin/env python3
"""Author the `pangenome_heatmap_from_assembly` template.

One NCBI assembly accession per sample -- add more rows via the GUI's sample
table to grow the pangenome:

  accession --> getNcbiAssembly --> gbk
  gbk (sharing a pangenome ancestor) --> ppanggolin --> ppanggolin_matrix
  ppanggolin_matrix --> heatmap --> pangenome::heatmap

`pangenome::pangenome` has no producing transform -- it exists purely so
`ppanggolin` can require "all genomes sharing this ancestor." Modeled as one
literal value every deferred accession is minted under, and named in
`shared_input_paths` so it stays a single shared ancestor across however many
accession rows the user adds, rather than each sample getting its own.

    python main/pangenome_heatmap_from_assembly.py [--rebuild] [--dag]
"""
import sys

import _authoring as A
from metasmith.python_api import DEFERRED, Spec

NAME = "pangenome_heatmap_from_assembly"
DESCRIPTION = """
Build a pangenome from NCBI assembly accessions and render it as a heatmap.
"""


def build_spec(rebuild: bool = False) -> Spec:
    def inputs(lib):
        lib.AddTypeLibrary(A.TYPES / "ncbi.yml")
        lib.AddTypeLibrary(A.TYPES / "pangenome.yml")
        lib.AddTypeLibrary(A.TYPES / "sequences.yml")
        pan = lib.AddValue("pangenome.json", {"logistics": "pangenome"},
                            "pangenome::pangenome")
        lib.AddItem(DEFERRED, "ncbi::assembly_accession", parents={pan})

    return Spec(
        input_library=A.deferred_inputs(NAME, inputs, rebuild=rebuild),
        sample_type="ncbi::assembly_accession",
        shared_input_paths=["pangenome.json"],
        target_types=["pangenome::heatmap"],
        transform_libraries=A.transforms("logistics", "pangenome"),
        resource_libraries=[A.containers(), A.MLIB / "resources" / "lib"],
    )


if __name__ == "__main__":
    A.cli(sys.modules[__name__])
