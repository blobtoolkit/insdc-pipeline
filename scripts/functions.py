import pathlib


def reads_by_prefix(config):
    """Return read meta by prefix"""
    reads = {}
    if "reads" not in config:
        return {}

    for strategy in ("paired", "single"):
        if not strategy in config["reads"] or not config["reads"][strategy]:
            continue
        for entry in config["reads"][strategy]:
            if isinstance(entry, list):
                meta = {
                    "prefix": entry[0],
                    "platform": entry[1],
                    "strategy": strategy,
                    "base_count": entry[2],
                    "file": entry[3],
                }
                if len(entry) == 5:
                    meta["url"] = entry[4].split(";")
            else:
                meta = entry
            reads.update({meta["prefix"]: meta})
    return reads


def minimap_tuning(config, prefix):
    """Set minimap2 mapping parameter."""
    reads = reads_by_prefix(config)
    tunings = {"ILLUMINA": "sr", "OXFORD_NANOPORE": "map-ont", "PACBIO_SMRT": "map-pb"}
    return tunings[reads[prefix]["platform"]]


def read_files(config, prefix):
    """Get read filenames."""
    reads = reads_by_prefix(config)
    return reads[prefix]["file"].split(";")


def seqtk_sample_input(config, prefix):
    """Generate seqtk command to subsamplereads if required."""
    meta = reads_by_prefix(config)[prefix]
    filenames = meta["file"].split(";")
    ratio = 1
    if "coverage" in config["reads"] and "max" in config["reads"]["coverage"]:
        base_count = meta["base_count"]
        if isinstance(base_count, int):
            ratio = (
                config["assembly"]["span"]
                * config["reads"]["coverage"]["max"]
                / base_count
            )
    if ratio <= 0.95:
        command = " ".join(
            [
                "<(seqtk sample -s 100 %s %.2f)" % (filename, ratio)
                for filename in filenames
            ]
        )
    else:
        command = " ".join(filenames)
    return command


def diamond_db_name(config):
    """Generate filtered diamond database name."""
    name = "reference_proteomes"
    parts = ["diamond", name]
    return ".".join(parts)


def blobdir_name(config):
    """Generate blobdir name."""
    name = config["assembly"]["prefix"]
    if "revision" in config and config["revision"] > 0:
        name = "%s.%d" % (name, config["revision"])
    return name


def blobtools_cov_flag(config):
    """Generate --cov flag for blobtools add."""
    keys = reads_by_prefix(config).keys()
    if keys:
        return "--cov " + " --cov ".join(
            [
                "%s/%s.%s.bam=%s"
                % (minimap_path, config["assembly"]["prefix"], key, key)
                for key in keys
            ]
        )
    return ""


def set_blast_chunk(config):
    """Set minimum chunk size for splitting long sequences."""
    return config["settings"].get("blast_chunk", 100000)


def set_blast_chunk_overlap(config):
    """Set overlap length for splitting long sequences."""
    return config["settings"].get("blast_overlap", 0)


def set_blast_max_chunks(config):
    """Set minimum chunk size for splitting long sequences."""
    return config["settings"].get("blast_max_chunks", 10)


def set_blast_min_length(config):
    """Set minimum sequence length for running blast searches."""
    return config["settings"].get("blast_min_length", 1000)


def read_similarity_settings(config, group):
    """Read similarity settings for blast rules and outputs."""
    settings = {
        "evalue": 1.0e-10,
        "import_evalue": 1.0e-25,
        "max_target_seqs": 10,
        "name": "reference_proteomes",
        "taxrule": "bestdistorder",
    }
    if "defaults" in config["similarity"]:
        settings.update({**config["similarity"]["defaults"]})
    if group in config["similarity"]:
        settings.update({**config["similarity"][group]})
    return settings


def similarity_setting(config, group, value):
    """Get a single similarity setting value."""
    settings = read_similarity_settings(config, group)
    setting = settings.get(value, None)
    if setting is not None:
        return setting
    settings = {
        "evalue": 1.0e-25,
        "max_target_seqs": 10,
        "taxrule": "bestdistorder",
        **settings,
    }
    if value.startswith("import_"):
        value = value.replace("import_", "")
    return settings[value]


def get_basal_lineages(config):
    """Get basal BUSCO lineages from config."""
    if "basal_lineages" in config["busco"]:
        return config["busco"]["basal_lineages"]
    basal = {"archaea_odb10", "bacteria_odb10", "eukaryota_odb10"}
    lineages = []
    if "lineages" in config["busco"]:
        for lineage in config["busco"]["lineages"]:
            if lineage in basal:
                lineages.push(lineage)
    return lineages
