rule run_blastn:
    """
    Run Diamond blastx to search protein database with assembly query.
    """
    input:
        fasta = "{assembly}.nohit.fasta.chunks",
        db = "%s/%s.nal" % (similarity_setting(config, "blastn", "path"), similarity_setting(config, "blastn", "name"))
    output:
        "{assembly}.blastn.nt.out.raw"
    params:
        db = "%s/%s" % (similarity_setting(config, "blastn", "path"), similarity_setting(config, "blastn", "name")),
        evalue = similarity_setting(config, "diamond_blastx", "evalue"),
        max_target_seqs = similarity_setting(config, "diamond_blastx", "max_target_seqs"),
        taxid = config["taxon"]["taxid"]
    threads: 30
    log:
        "logs/{assembly}/run_blastn.log"
    benchmark:
        "logs/{assembly}/run_blastn.benchmark.txt"
    shell:
        """(if [ -s {input.fasta} ]; then \
            blastn -task megablast \
                -query {input.fasta} \
                -db {params.db} \
                -outfmt "6 qseqid staxids bitscore std" \
                -max_target_seqs {params.max_target_seqs} \
                -max_hsps 1 \
                -evalue {params.evalue} \
                -num_threads {threads} \
                -negative_taxids {params.taxid} \
                -lcase_masking \
                -dust "20 64 1" \
                > {output}; \
        else \
            > {output}; \
        fi) 2> {log}"""