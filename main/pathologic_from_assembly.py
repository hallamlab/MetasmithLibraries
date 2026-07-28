#!/usr/bin/env python3
"""Author the `pathologic_from_assembly` template.

Targets both PathoLogic outputs, which is what makes the planner fan orfs out to
deepec + kofamscan + diamond_uniref50 and gather them again.

    python main/pathologic_from_assembly.py [--rebuild] [--dag]
"""
import sys

import _authoring as A
from metasmith.python_api import DEFERRED, Spec

NAME = "pathologic_from_assembly"
DESCRIPTION = """
Build a Pathway Tools PGDB from a nucleotide assembly: ORF calling, three
annotation legs gathered together, then PathoLogic.
"""


def build_spec(rebuild: bool = False) -> Spec:
    def inputs(lib):
        lib.AddTypeLibrary(A.TYPES / "sequences.yml")
        lib.AddItem(DEFERRED, "sequences::assembly")

    return Spec(
        input_library=A.deferred_inputs(NAME, inputs, rebuild=rebuild),
        sample_type="sequences::assembly",
        target_types=["annotation::pgdb_archive", "annotation::pgdb_csv_tables"],
        transform_libraries=A.transforms("logistics", "metagenomics", "functionalAnnotation"),
        resource_libraries=[A.containers()],
    )


if __name__ == "__main__":
    A.cli(sys.modules[__name__])
