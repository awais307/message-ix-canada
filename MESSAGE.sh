#!/bin/bash
#SBATCH --account=def-mcpher16
#SBATCH --cpus-per-task=8
#SBATCH --mem=125G
#SBATCH --time=24:00:00
#SBATCH --mail-user=user@example.com
#SBATCH --mail-type=ALL
#SBATCH --array=1-2


echo "Current working directory: $PWD"
echo "Starting run at: `date`"

module load python/3.10 StdEnv/2023 gcc/12.3 arrow/15.0.1
virtualenv --no-download $SLURM_TMPDIR/env
source $SLURM_TMPDIR/env/bin/activate
pip install --no-index --upgrade pip
pip install --no-index -e .

# Export the path to the CPLEX installation - SESIT team's project folder
export PATH=$PATH:/project/rrg-mcpher16/SHARED2/software/cplex/cplex/bin/x86-64_linux/

# Delete bloat from MESSAGE folder
rm -rf model/notebooks model/__pycache__
rm -rf *.yml LICENSE *.pdf *.md

# Define a function to generate different input flags for each task - when running a job array
generate_flags() {
  local i=$SLURM_ARRAY_TASK_ID
  case $i in # Increase the number of cases here depending on your use case
    1) flags="";; # This function needs to be reworked to be applied to the MESSAGE model
    *) flags="";; # or raise an error
  esac
}

echo ""
echo "Job Array ID / Job ID: $SLURM_ARRAY_JOB_ID / $SLURM_JOB_ID"
echo "This is job $SLURM_ARRAY_TASK_ID out of $SLURM_ARRAY_TASK_COUNT jobs."
echo ""

# Call the function to generate input flags for each job
#generate_flags

# Begin running script
srun python MESSAGE_CA.py #${flags}
