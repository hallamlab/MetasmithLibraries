#!/usr/bin/env python3
"""Plan the full metagenomics workflow starting from short reads.

Stops at DAG generation. The planner resolves:

  reads --> seqkit_reads --> read_qc_stats
  reads + read_qc_stats --> bbduk --> clean_short_reads
  clean_short_reads --> megahit --> assembly
  assembly --> prodigal --> orfs --> diamond_uniref50 + kofamscan
  assembly --> metabuli                                      (per-contig taxonomy)
  reads + assembly --> assembly_stats --> bam + per-contig/per-bp coverage
       --> metabat2 / semibin2 / comebin --> bin_fasta + contig_to_bin_table
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

READS   = Path("/home/tony/agentic_workspace/projects/metasmith-libraries/phyloflash/tests/test_data/small_reads_R1.fq.gz")  # <interleaved short reads>
OUT_DIR = Path("results/metag_workflow")

MLIB = Path(__file__).resolve().parent.parent

inputs = DataInstanceLibrary(OUT_DIR.resolve() / "inputs.xgdb")
for tl in ["sequences.yml", "alignment.yml", "ref.yml", "annotation.yml", "taxonomy.yml", "binning.yml", "binning_local.yml"]:
    inputs.AddTypeLibrary(MLIB / "data_types" / tl)

meta = inputs.AddValue("reads_metadata.json", {"parity": "paired", "length_class": "short"}, "sequences::read_metadata")
inputs.AddItem(READS.resolve(), "sequences::short_reads", parents={meta})
inputs.Save()

smith = Agent(home=Source.FromLocal(OUT_DIR.resolve() / "msm_home"), runtime=ContainerRuntime.DOCKER)

targets = TargetBuilder()
targets.Add("sequences::read_qc_stats")
targets.Add("sequences::orfs")
targets.Add("sequences::assembly_stats")
targets.Add("sequences::assembly_per_contig_coverage")
targets.Add("sequences::assembly_per_bp_coverage")
targets.Add("annotation::diamond_uniref50_results")
targets.Add("annotation::kofamscan_results")
targets.Add("taxonomy::metabuli")
targets.Add("taxonomy::checkm_stats")
targets.Add("taxonomy::gtdbtk")
targets.Add("binning::metabat2_contig_to_bin_table")
targets.Add("binning::semibin2_contig_to_bin_table")
targets.Add("binning::comebin_contig_to_bin_table")
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
