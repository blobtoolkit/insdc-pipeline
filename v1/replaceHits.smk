import os

"""
https://github.com/blobtoolkit/insdc-pipeline
https://blobtoolkit.genomehubs.org/pipeline/

Pipeline to run replace hits in a BlobDir
----------------------------------------------

Requirements:
 - BlobTools2 (https://github.com/blobtoolkit/blobtools2)
 - Conda (https://conda.io/docs/commands/conda-install.html)
 - SnakeMake (http://snakemake.readthedocs.io/en/stable/)

Basic usage:
  snakemake -p --use-conda \
    --directory ~/workdir \
    --configfile example.yaml \
    -s replaceHits.smk
    -j 8

© 2018-19 Richard Challis (University of Edinburgh), MIT License
© 2019-20 Richard Challis (Wellcome Sanger Institute), MIT License
"""

singularity: "docker://genomehubs/blobtoolkit:1.3"

include: 'scripts/functions.py'

supported_version = check_version()

use_singularity = check_config()

multicore = int(os.getenv('MULTICORE', 16))
maxcore = int(os.getenv('MAXCORE', 32))

similarity = apply_similarity_search_defaults()

keep = False
if 'keep_intermediates' in config:
    keep = bool(config['keep_intermediates'])
asm = config['assembly']['prefix']
rev = ''
if 'revision' in config:
    if config['revision'] > 0:
        rev = '.'+str(config['revision'])


rule all:
    """
    Dummy rule to set target of pipeline
    """
    input:
        "%s%s.hits.removed" % (asm, rev),
        "%s%s.meta.replaceHits" % (asm, rev),
        hit_fields(asm, rev, config['similarity']['taxrule'])


rule log_replaceHits:
    """
    Log use of replaceHits script
    """
    input:
        "%s%s.hits.removed" % (asm, rev),
        "{assembly}%s/meta.json" % rev,
        hit_fields(asm, rev, config['similarity']['taxrule'])
    output:
        touch(temp("{assembly}%s.meta.replaceHits" % rev))
    params:
        id = lambda wc: "%s%s" % (wc.assembly, rev),
        path = config['settings']['blobtools2_path'],
        gitdir = git_dir
    conda:
        './envs/blobtools2.yaml'
    threads: get_threads('log_replaceHits', 1)
    log:
        'logs/{assembly}/log_replaceHits.log'
    benchmark:
        'logs/{assembly}/log_replaceHits.benchmark.txt'
    resources:
        btk = 1
    shell:
        'COMMIT=$(git --git-dir {params.gitdir} rev-parse --short HEAD) \
        PATH={params.path}:$PATH && \
        blobtools replace --key settings.updates.replaceHits=$COMMIT  \
        {params.id} > {log} 2>&1'


# fetch database files
include: 'rules/fetch_ncbi_db.smk'
include: 'rules/fetch_taxdump.smk'
include: 'rules/fetch_uniprot.smk'
include: 'rules/extract_uniprot.smk'
include: 'rules/make_uniprot_db.smk'
# fetch assembly files
include: 'rules/fetch_assembly.smk'
# make filtered databases
include: 'rules/split_fasta.smk'
include: 'rules/make_taxid_list.smk'
include: 'rules/make_masked_lists.smk'
include: 'rules/make_diamond_db.smk'
include: 'rules/unchunk_blast.smk'
# run similarity searches
include: 'rules/run_windowmasker.smk'
include: 'rules/chunk_fasta.smk'
include: 'rules/run_blastn.smk'
include: 'rules/extract_nohit_sequences.smk'
include: 'rules/run_diamond_blastx.smk'
# run blobtools
include: 'rules/blobtoolkit_remove_hits.smk'
include: 'rules/blobtoolkit_add_hits.smk'
