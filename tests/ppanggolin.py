from pathlib import Path
from metasmith.python_api import Agent, Source, SshSource, DataInstanceLibrary, TransformInstanceLibrary, DataTypeLibrary
from metasmith.python_api import Resources, Size, Duration
from metasmith.python_api import ContainerRuntime

base_dir = Path("./cache")

agent_home = Source.FromLocal((base_dir/"local_home").resolve())
smith = Agent(
    home = agent_home,
    runtime=ContainerRuntime.DOCKER
)

# agent_home = SshSource(host="fir", path="/scratch/phyberos/metasmith").AsSource()
# smith = Agent(
#     home = agent_home,
#     runtime=ContainerRuntime.APPTAINER
# )

# smith.Deploy()

# import ipynbname
# notebook_name = ipynbname.name()
notebook_name = Path(__file__).stem
in_dir = base_dir/f"{notebook_name}/inputs.xgdb"

inputs = DataInstanceLibrary(in_dir)
inputs.Purge()
inputs.AddTypeLibrary("ncbi", DataTypeLibrary.Load("../data_types/ncbi.yml"))
inputs.AddTypeLibrary("sequences", DataTypeLibrary.Load("../data_types/sequences.yml"))
inputs.AddTypeLibrary("pangenome", DataTypeLibrary.Load("../data_types/pangenome.yml"))

group = inputs.AddValue("pangenome", "e coli", "pangenome::pangenome")
inputs.AddValue("DH10b", "GCF_000019425.1", "ncbi::accession", parents={group})
inputs.AddValue("K12", "GCF_000005845.2", "ncbi::accession", parents={group})
inputs.AddItem((base_dir/f"{notebook_name}/epi300.gbk").resolve(), "sequences::gbk", parents={group})
inputs.Save()

inputs = DataInstanceLibrary.Load(in_dir)

resources = [
    DataInstanceLibrary.Load(f"../resources/{n}")
    for n in ["containers", "lib"]
]

transforms = [
    TransformInstanceLibrary.Load(f"../transforms/{n}")
    for n in ["dataDownload", "pangenome"]
]

task = smith.GenerateWorkflow(
    samples=inputs.AsSamples(),
    resources=resources,
    transforms=transforms,
    # targets=[inputs.GetType("sequences::gbk")]
    targets=[inputs.GetType("pangenome::heatmap")]
)
task.plan.RenderDAG(base_dir/f"{notebook_name}/dag")
print(task.ok, len(task.plan.steps))

smith.StageWorkflow(task, on_exist="clear")
# smith.StageWorkflow(task, on_exist="update_data")
# smith.StageWorkflow(task, on_exist="update_workflow")

smith.RunWorkflow(
    task,
    config_file=smith.GetNxfConfigPresets()["local"],
    resource_overrides={
        "all": Resources(
            memory=Size.GB(2),
        )
    }
)