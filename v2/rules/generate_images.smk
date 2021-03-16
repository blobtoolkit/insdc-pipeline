rule generate_images:
    """
    Use BlobTools2 view to generate a set of static images.
    """
    input:
        valid = "{blobdir}.valid",
        cov = expand("{{blobdir}}/{sra}_cov.json", sra=list_sra_accessions(reads))
    output:
        "{blobdir}/cumulative.png"
    params:
        blobdir = lambda wc: wc.blobdir,
        host = "http://localhost",
        ports = "8000-8099"
    threads: 3
    log:
        "logs/{blobdir}/generate_images.log"
    benchmark:
        "logs/{blobdir}/generate_images.benchmark.txt"
    script:
        """../scripts/generate_static_images.py"""
