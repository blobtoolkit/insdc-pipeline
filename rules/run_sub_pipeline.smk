def input_config(wc):
    """Set sub pipeline inputs."""
    sub_config = {
        "blastn": ["%s/%s.stats" % (parent_dir, tool) for tool in ["diamond", "windowmasker"]],
        "blobtools": ["%s/%s.stats" % (parent_dir, tool) for tool in ["blastn", "busco", "diamond", "diamond_blastp", "minimap", "stats"]],
        "diamond": ["%s/%s.stats" % (parent_dir, tool) for tool in ["busco", "windowmasker"]],
        "diamond_blastp": ["%s/busco.stats" % parent_dir],
        "stats": ["%s/%s.stats" % (parent_dir, tool) for tool in ["minimap", "windowmasker"]],
        "view": ["%s/blobtools.stats" % parent_dir],
    }
    if wc.tool in sub_config:
        return sub_config[wc.tool]
    return []


def thread_config(wc):
    """Set sub pipeline thread counts."""
    sub_config = {}
    threads = config["settings"].get("threads", {})
    thread_defaults = {
        "blastn": 30,
        "blobtools": 4,
        "busco": 30,
        "diamond": 30,
        "diamond_blastp": 30,
        "minimap": 30,
        "windowmasker": 1,
    }
    return threads.get(wc.tool, thread_defaults.get(wc.tool, 4))


rule run_sub_pipeline:
    """
    Run a sub pipeline.
    """
    input:
        input_config
    output:
        "%s/{tool}.stats" % parent_dir
    params:
        tool = lambda wc: wc.tool,
        snake_path = workflow.basedir,
        parent_dir = parent_dir
    threads: thread_config
    log:
        "logs/{tool}/run_sub_pipeline.log"
    benchmark:
        "logs/{tool}/run_sub_pipeline.benchmark.txt"
    shell:
        """snakemake -p \
          -j {threads} \
          --directory {params.parent_dir}/{params.tool} \
          --configfile {params.parent_dir}/config.yaml \
          --latency-wait 60 \
          --stats {output} \
          -s {params.snake_path}/{params.tool}.smk 2> {log}"""
