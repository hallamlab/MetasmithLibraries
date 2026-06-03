#!/usr/bin/env python3
"""Plan the full metagenomics workflow for a nucleotide assembly + short reads.

Stops at DAG generation. The planner resolves:

  assembly --> prodigal --> orfs --> diamond_uniref50 + kofamscan
  assembly --> metabuli                                      (per-contig taxonomy)
  reads + assembly --> assembly_stats --> bam
       --> metabat2 / semibin2 / comebin --> bin_fasta
            --> checkm2 --> aggregator --> quality_bin_fasta
                                          --> skani_dedup --> cluster_table
       (one binner's bin_fasta) --> gtdbtk                   (per-bin taxonomy)
  reads --> phyloFlash                                       (SSU rRNA taxonomy)

External DBs (UniRef50, KOFAM, metabuli, GTDB, phyloFlash) are auto-resolved
by including the transforms/logistics library in the plan.
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
READS    = Path("/home/tony/agentic_workspace/projects/metasmith-libraries/phyloflash/tests/test_data/small_reads_R1.fq.gz")  # <interleaved short reads>
OUT_DIR  = Path("results/metag_workflow")

MLIB = Path(__file__).resolve().parent.parent

inputs = DataInstanceLibrary(OUT_DIR.resolve() / "inputs.xgdb")
for tl in ["sequences.yml", "alignment.yml", "ref.yml", "annotation.yml", "taxonomy.yml", "binning_local.yml"]:
    inputs.AddTypeLibrary(MLIB / "data_types" / tl)

meta  = inputs.AddValue("reads_metadata.json", {"parity": "paired", "length_class": "short"}, "sequences::read_metadata")
reads = inputs.AddItem(READS.resolve(),    "sequences::short_reads", parents={meta})
inputs.AddItem(ASSEMBLY.resolve(), "sequences::assembly",    parents={reads})
inputs.Save()

smith = Agent(home=Source.FromLocal(OUT_DIR.resolve() / "msm_home"), runtime=ContainerRuntime.DOCKER)

targets = TargetBuilder()
targets.Add("annotation::diamond_uniref50_results")
targets.Add("annotation::kofamscan_results")
targets.Add("taxonomy::metabuli")
targets.Add("taxonomy::gtdbtk")
targets.Add("binning_local::cluster_table")
targets.Add("taxonomy::phyloflash_summary")

task = smith.GenerateWorkflow(
    samples=list(inputs.AsSamples("sequences::read_metadata")),
    resources=[DataInstanceLibrary.Load(MLIB / "resources" / "containers"), inputs],
    transforms=[
        TransformInstanceLibrary.Load(MLIB / "transforms" / "logistics"),
        TransformInstanceLibrary.Load(MLIB / "transforms" / "assembly"),
        TransformInstanceLibrary.Load(MLIB / "transforms" / "metagenomics"),
        TransformInstanceLibrary.Load(MLIB / "transforms" / "functionalAnnotation"),
    ],
    targets=targets,
)

task.plan.RenderDAG(str(OUT_DIR.resolve() / "dag"), format="svg")
