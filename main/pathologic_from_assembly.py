#!/usr/bin/env python3
"""Plan a PathoLogic (Pathway Tools) workflow for a nucleotide assembly FASTA.

Targets both ptools outputs (cyc folder + parsed CSV tables); the planner
fans out orfs -> {deepec, kofamscan, diamond_uniref50} -> ptools_annotation_gather
-> pathologic. Stops at DAG generation.
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
OUT_DIR = Path("results/pathologic")

MLIB = Path(__file__).resolve().parent.parent

inputs = DataInstanceLibrary(OUT_DIR.resolve() / "inputs.xgdb")
inputs.AddTypeLibrary(MLIB / "data_types" / "sequences.yml")
inputs.AddItem(ASSEMBLY.resolve(), "sequences::assembly")
inputs.Save()

smith = Agent(home=Source.FromLocal(OUT_DIR.resolve() / "msm_home"), runtime=ContainerRuntime.DOCKER)

targets = TargetBuilder()
targets.Add("annotation::pgdb_archive")
targets.Add("annotation::pgdb_csv_tables")

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
