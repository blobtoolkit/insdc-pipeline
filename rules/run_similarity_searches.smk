rule run_blastn:
    """
    Run NCBI blastn to search nucleotide database with assembly query.
    """
    input:
        fasta='{assembly}.fasta',
        db=lambda wc: "%s/%s.nal" % (similarity[wc.name]['local'],wc.name),
        taxids='{name}.root.{root}{masked}.taxids'
    output:
        raw='{assembly}.blastn.{name}.root.{root}{masked}.out.raw',
        nohit=temp('{assembly}.blastn.{name}.root.{root}{masked}.nohit')
    wildcard_constraints:
        root='\d+',
        masked='.[fm][ulins\d\.]+'
    params:
        db=lambda wc: "%s/%s" % (similarity[wc.name]['local'],wc.name),
        evalue=lambda wc:similarity[wc.name]['evalue'],
        max_target_seqs=lambda wc:similarity[wc.name]['max_target_seqs'],
        chunk=config['settings']['blast_chunk'],
        overlap=config['settings']['blast_overlap'],
        max_chunks=config['settings']['blast_max_chunks']
    conda:
         '../envs/pyblast.yaml'
    threads: 60
    log:
      lambda wc: "logs/%s/run_blastn/%s.root.%s%s.log" % (wc.assembly, wc.name, wc.root, wc.masked)
    resources:
        threads=60
    script:
        '../scripts/blast_wrapper.py'

rule unchunk_blast_results:
    """
    reformat blast results from chunked input.
    """
    input:
        '{assembly}.{algorithm}.{name}.root.{root}{masked}.out.raw'
    output:
        '{assembly}.{algorithm}.{name}.root.{root}{masked}.out'
    params:
        max_target_seqs=lambda wc:similarity[wc.name]['max_target_seqs']
    conda:
         '../envs/py3.yaml'
    threads: 1
    log:
      lambda wc: "logs/%s/unchunk_blast_results/%s.%s.root.%s%s.log" % (wc.assembly, wc.algorithm, wc.name, wc.root, wc.masked)
    resources:
        threads=1
    script:
        '../scripts/unchunk_blast.py'


rule extract_nohit_sequences:
    """
    Run seqtk to extract nohit sequences from assembly.
    """
    input:
        fasta='{assembly}.fasta',
        nohit='{assembly}.blastn.{name}.root.{root}{masked}.nohit'
    output:
        temp('{assembly}.blastn.{name}.root.{root}{masked}.fasta.nohit')
    conda:
         '../envs/pyblast.yaml'
    threads: 1
    log:
      lambda wc: "logs/%s/extract_nohit_sequences/%s.root.%s%s.log" % (wc.assembly, wc.name, wc.root, wc.masked)
    resources:
        threads=1
    shell:
        'seqtk subseq {input.fasta} {input.nohit} > {output} 2> {log}'

rule run_diamond_blastx:
    """
    Run Diamond blastx to search protein database with assembly query.
    """
    input:
        fasta="{assembly}.blastn.%s.root.{root}{masked}.fasta.nohit" % blast_db_name(config),
        db=lambda wc: "%s/full/%s.dmnd" % (similarity[wc.name]['local'],wc.name),
        taxids='{name}.root.{root}{masked}.taxids'
    output:
        '{assembly}.diamond.{name}.root.{root}{masked}.out'
    wildcard_constraints:
        root='\d+',
        masked='.[fm][ulins\d\.]+',
        assembly='\w+'
    params:
        db=lambda wc: wc.name,
        evalue=lambda wc:similarity[wc.name]['evalue'],
        max_target_seqs=lambda wc:similarity[wc.name]['max_target_seqs']
    conda:
         '../envs/diamond.yaml'
    threads: lambda x: maxcore
    log:
      lambda wc: "logs/%s/run_diamond_blastx/%s.root.%s%s.log" % (wc.assembly, wc.name, wc.root, wc.masked)
    resources:
        threads=lambda x: maxcore
    shell:
        'if ! [ -s {input.fasta} ]; then \
            touch {output} && exit 0; \
        fi; \
        diamond blastx \
            --query {input.fasta} \
            --db {input.db} \
            --taxonlist {input.taxids} \
            --outfmt 6 qseqid staxids bitscore qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore \
            --sensitive \
            --max-target-seqs {params.max_target_seqs} \
            --evalue {params.evalue} \
            --threads {threads} \
            > {output} 2> {log}'
