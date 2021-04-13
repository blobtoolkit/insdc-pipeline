import os

"""
https://github.com/blobtoolkit/insdc-pipeline
https://blobtoolkit.genomehubs.org/pipeline/

Pipeline to run Minimap
--------------------------------------------------

Requirements:
 - Conda (https://conda.io/docs/commands/conda-install.html)
 - SnakeMake (http://snakemake.readthedocs.io/en/stable/)

Basic usage:
  snakemake -p \
    --directory ~/workdir \
    --configfile example.yaml \
    -s minimap.smk
    -j 8

Author:
  Richard Challis

Contact:
  blobtoolkit@genomehubs.org

License:
  © 2021 Genome Research Limited, MIT License
"""

include: "scripts/functions.py"

rule all:
    """
    Dummy rule to define all outputs
    """
    input:
        expand("%s.{sra}.bam" % config["assembly"]["prefix"], sra=reads_by_prefix(config).keys())


include: "rules/run_minimap2_index.smk"
include: "rules/run_minimap2_align.smk"
