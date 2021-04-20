rule run_busco_v3:
    """
    Run BUSCO on a lineage.
    """
    input:
        fasta = '{assembly}.fasta',
        busco = config['busco']['lineage_dir']+'/{lineage}.tar.gz',
    output:
        full = '{assembly}.busco.{lineage}.tsv',
        short = '{assembly}.busco.{lineage}.txt'
    params:
        lineage = lambda wc: wc.lineage,
        lineage_dir = busco_dir,
        assembly = lambda wc: wc.assembly,
        outdir = lambda wc: "run_%s_%s" % (wc.assembly, wc.lineage)
    wildcard_constraints:
        lineage = r'\w+_odb9'
    conda:
        '../envs/busco.yaml'
    threads: get_threads('run_busco', multicore)
    log:
        'logs/{assembly}/run_busco/{lineage}.log'
    benchmark:
        'logs/{assembly}/run_busco/{lineage}.benchmark.txt'
    shell:
        'run_busco \
            -f \
            -i {input.fasta} \
            -o {params.assembly}_{params.lineage} \
            -l {params.lineage_dir}/{params.lineage} \
            -m geno \
            -c {threads} > {log} 2>&1 && \
        mv {params.outdir}/full_table_{params.assembly}_{params.lineage}.tsv {output.full} && \
        mv {params.outdir}/short_summary_{params.assembly}_{params.lineage}.txt {output.short} && \
        rm -rf {params.outdir} && rm -rf {params.assembly}_{params.lineage} && exit 0 || \
        rm -rf {params.outdir} && rm -rf {params.assembly}_{params.lineage} exit 1'

