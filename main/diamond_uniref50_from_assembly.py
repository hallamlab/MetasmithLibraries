#!/usr/bin/env python3
"""Author the `diamond_uniref50_from_assembly` template.

The simplest shape there is: one deferred input, one target. Read this one first
if you are writing a template.

    python main/diamond_uniref50_from_assembly.py [--rebuild] [--dag]
"""
import sys

import _authoring as A
from metasmith.python_api import DEFERRED, Spec

NAME = "diamond_uniref50_from_assembly"
DESCRIPTION = """
Annotate a nucleotide assembly against UniRef50 with DIAMOND.
"""


def build_spec(rebuild: bool = False) -> Spec:
    def inputs(lib):
        lib.AddTypeLibrary(A.TYPES / "sequences.yml")
        lib.AddItem(DEFERRED, "sequences::assembly")

    return Spec(
        input_library=A.deferred_inputs(NAME, inputs, rebuild=rebuild),
        sample_type="sequences::assembly",
        target_types=["annotation::diamond_uniref50_results"],
        transform_libraries=A.transforms("logistics", "metagenomics", "functionalAnnotation"),
        resource_libraries=[A.containers()],
    )


if __name__ == "__main__":
    A.cli(sys.modules[__name__])
