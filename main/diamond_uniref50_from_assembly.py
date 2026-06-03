#!/usr/bin/env python3
"""Plan a DIAMOND UniRef50 annotation workflow for a nucleotide assembly FASTA.

Stops at DAG generation — prints the resolved transform chain and exits.
"""
import sys
from pathlib import Path

sys.path.insert(0, "/home/tony/agentic_workspace/projects/metasmith/dev/src")
from metasmith.python_api import (
    Agent, Source, ContainerRuntime,
    DataInstanceLibrary, TransformInstanceLibrary,
    TargetBuilder,
)

ASSEMBLY = Path("/home/tony/agentic_workspace/data/scadc/references/pcc1.genbank.fna")  # <assembly>
OUT_DIR = Path("results/diamond_uniref50")

MLIB = Path(__file__).resolve().parent.parent

inputs = DataInstanceLibrary(OUT_DIR.resolve() / "inputs.xgdb")
inputs.AddTypeLibrary(MLIB / "data_types" / "sequences.yml")
inputs.AddItem(ASSEMBLY.resolve(), "sequences::assembly")
inputs.Save()

smith = Agent(home=Source.FromLocal(OUT_DIR.resolve() / "msm_home"), runtime=ContainerRuntime.DOCKER)

targets = TargetBuilder()
targets.Add("annotation::diamond_uniref50_results")

task = smith.GenerateWorkflow(
    samples=list(inputs.AsSamples("sequences::assembly")),
    resources=[DataInstanceLibrary.Load(MLIB / "resources" / "containers"), inputs],
    transforms=[
        TransformInstanceLibrary.Load(MLIB / "transforms" / "logistics"),
        TransformInstanceLibrary.Load(MLIB / "transforms" / "metagenomics"),
        TransformInstanceLibrary.Load(MLIB / "transforms" / "functionalAnnotation"),
    ],
    targets=targets,
)

task.plan.RenderDAG(str(OUT_DIR.resolve() / "dag"), format="svg")
