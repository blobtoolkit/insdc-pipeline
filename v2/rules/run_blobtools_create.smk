rule run_blobtools_create:
    """
    Run blobtools create.
    """
    input:
        fasta = "%s.fasta" % config["assembly"]["prefix"],
        busco = expand("%s/%s.busco.{lineage}.tsv" % (busco_path, config["assembly"]["prefix"]), lineage=config['busco']['lineages']),
        bam = expand("%s/%s.{sra}.bam" % (minimap_path, config["assembly"]["prefix"]), sra=reads_by_prefix(config).keys()),
        blast = "%s/%s.diamond.reference_proteomes.out" % (diamond_path, config["assembly"]["prefix"]),
        taxdump = config["settings"]["taxdump"],
        yaml = "%s.meta.yaml" % config["assembly"]["prefix"]
    output:
        "%s/meta.json" % blobdir_name(config),
        "%s/identifiers.json" % blobdir_name(config),
        "%s/%s_phylum.json" % (blobdir_name(config), config["similarity"]["taxrule"]),
        expand("%s/{sra}_cov.json" % blobdir_name(config), sra=reads_by_prefix(config).keys()),
        expand("%s/{lineage}_busco.json" % blobdir_name(config), lineage=config['busco']['lineages'])
    params:
        busco = lambda wc: " --busco ".join(expand("%s/%s.busco.{lineage}.tsv" % (busco_path, config["assembly"]["prefix"]), lineage=config['busco']['lineages'])),
        cov = lambda wc: " --cov ".join(expand("%s/%s.{sra}.bam" % (minimap_path, config["assembly"]["prefix"]), sra=reads_by_prefix(config).keys())),
        blobdir = blobdir_name(config)
    threads: 30
    log:
        "logs/%s/run_blobtools_create.log" % config["assembly"]["prefix"]
    benchmark:
        "logs/%s/run_blobtools_create.benchmark.txt" % config["assembly"]["prefix"]
    shell:
        """blobtools replace \
            --fasta {input.fasta} \
            --meta {input.yaml} \
            --taxdump {input.taxdump} \
            --busco {params.busco} \
            --cov {params.cov} \
            --hits {input.blast}
            {params.blobdir} > {log} 2>&1"""