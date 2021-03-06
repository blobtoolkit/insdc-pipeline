# BTK Pipeline v2

Splits original pipeline into sub-pipelines that can be run independently or using the `blobtoolkit.smk` meta pipeline.

The previous pipeline is available inside the v1 directory.

## Sub-pipelines

1. `minimap.smk` - align reads to the genome assembly using minimap2.

1. `windowmasker.smk` - identify and mask repetitive regions using Windowmasker. Masked sequences are used in all blast searches.

1. `stats.smk` - calculate sequence statistics for each contif and for chunks (default up to 10) of long contigs (>100 kb). Calculate coverage stats using mosdepth.

1. `busco.smk` - run BUSCO using specific and basal lineages.

1. `diamond_blastp.smk` - Diamond blastp search of busco gene models for basal lineages (`archaea_odb10`, `bacteria_odb10` and `eukaryota_odb10`) against the UniProt reference proteomes.

1. `diamond.smk` - Diamond blastx search of assembly contigs against the UniProt reference proteomes. Contigs are split into chunks to allow distribution-based taxrules. Contigs over 1Mb are subsampled by retaining only the most BUSCO-dense 100 kb region from each chunk. 

1. `blastn.smk` - NCBI blastn search of assembly contigs with no Diamond blastx match against the NCBI nt database

1. `blobtools.smk` - import analysis results into a BlobDir dataset

1. `view.smk` - BlobDir validation and static image generation


## Dependencies

### BlobToolKit components
The various BlobToolKit components can be downloaded from their respecive Github repositories:
```
VERSION=release/v2.5.0
mkdir -p ~/blobtoolkit
cd ~/blobtoolkit
git clone -b $VERSION https://github.com/blobtoolkit/blobtools2
git clone -b $VERSION https://github.com/blobtoolkit/specification
git clone -b $VERSION https://github.com/blobtoolkit/pipeline
git clone -b $VERSION https://github.com/blobtoolkit/viewer
```

### Pipeline dependencies
Most pipeline dependencies can be installed using conda. The mamba replacement for conda is faster and more stable:
```
conda install -y -n base -c conda-forge mamba
```
Use `mamba` where you would normally use `conda` for creating environments and installing packages:
```
mamba create -y -n btk_env -c conda-forge -c bioconda -c tolkit \
    python=3.8 snakemake docopt defusedxml psutil pyyaml tqdm ujson urllib3 \
    entrez-direct minimap2=2.17 seqtk diamond=2 busco=5 \
    samtools=1.10 pysam=0.16 mosdepth=0.2.9 tolkein
```
Activate this environment:
```
conda activate btk_env
```

### Additional viewer dependencies
If these are not installable on your local compute environment (e.g. a shared cluster), it may be necessary to run the viewer steps separately:
```
sudo apt update && sudo apt-get -y install firefox xvfb

conda activate btk_env
mamba install -y -c conda-forge geckodriver selenium pyvirtualdisplay nodejs=10
pip install fastjsonschema;
cd ~/blobtoolkit/viewer
npm install
```

### PATH setup
Commands below assume that BLobToolKit executables and scripts are available in you PATH:
```
export PATH=~/blobtoolkit/blobtools2:~/blobtoolkit/specification:~/blobtoolkit/insdc-pipeline/scripts:$PATH
```

### Databases
Download the NCBI taxdump
```bash
TAXDUMP=/volumes/databases/taxdump_2021_03
mkdir -p $TAXDUMP;
cd $TAXDUMP;
curl -L ftp://ftp.ncbi.nih.gov/pub/taxonomy/new_taxdump/new_taxdump.tar.gz | tar xzf -;
cd -;
```

Download and extract UniProt reference proteomes
```bash
UNIPROT=/volumes/databases/uniprot_2021_03
mkdir -p $UNIPROT
wget -q -O $UNIPROT/reference_proteomes.tar.gz \
 ftp.ebi.ac.uk/pub/databases/uniprot/current_release/knowledgebase/reference_proteomes/$(curl \
     -vs ftp.ebi.ac.uk/pub/databases/uniprot/current_release/knowledgebase/reference_proteomes/ 2>&1 | \
     awk '/tar.gz/ {print $9}')
cd $UNIPROT
tar xf reference_proteomes.tar.gz

touch reference_proteomes.fasta.gz
find . -mindepth 2 | grep "fasta.gz" | grep -v 'DNA' | grep -v 'additional' | xargs cat >> reference_proteomes.fasta.gz

printf "accession\taccession.version\ttaxid\tgi\n" > reference_proteomes.taxid_map
zcat */*/*.idmapping.gz | grep "NCBI_TaxID" | awk '{print $1 "\t" $1 "\t" $3 "\t" 0}' >> reference_proteomes.taxid_map

diamond makedb -p 16 --in reference_proteomes.fasta.gz --taxonmap reference_proteomes.taxid_map --taxonnodes $TAXDUMP/nodes.dmp --taxonnames $TAXDUMP/names.dmp -d reference_proteomes.dmnd
cd -
```

Download NCBI nt database:
```bash
NT=/volumes/databases/nt_2021_03
wget "ftp://ftp.ncbi.nlm.nih.gov/blast/db/nt.??.tar.gz" -P $NT/ &&
for file in $NT/*.tar.gz; do
    tar xf $file -C $NT && rm $file;
done
```

## Configuration
The BlobToolKit pipeline requires a YAML format configuration file to specify file locations, parameters and metadata.

### Example

config.yaml
```yaml
assembly:
  accession: GCA_902806685.1
  alias: iAphHyp1.1
  bioproject: PRJEB36756
  biosample: SAMEA994723
  file: /volumes/data/by_accession/GCA_902806685.1/assembly/GCA_902806685.1.fasta.gz
  level: chromosome
  prefix: CADCXM01
  scaffold-count: 87
  span: 408137179
  url: ftp://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/902/806/685/GCA_902806685.1_iAphHyp1.1/GCA_902806685.1_iAphHyp1.1_genomic.fna.gz
busco:
  download_dir: /volumes/databases/busco_2021_03
  lineages:
    - lepidoptera_odb10
    - endopterygota_odb10
    - insecta_odb10
    - arthropoda_odb10
    - metazoa_odb10
    - eukaryota_odb10
    - bacteria_odb10
    - archaea_odb10
  basal_lineages:
    - eukaryota_odb10
    - bacteria_odb10
    - archaea_odb10
reads:
  coverage:
    max: 30
  paired:
    - prefix: ERR3316071
      platform: ILLUMINA
      base_count: 33696183030
      file: /volumes/data/by_accession/GCA_902806685.1/reads/ERR3316071_1.fastq.gz;/volumes/data/by_accession/GCA_902806685.1/reads/ERR3316071_2.fastq.gz
      url: ftp.sra.ebi.ac.uk/vol1/fastq/ERR331/001/ERR3316071/ERR3316071_1.fastq.gz;ftp.sra.ebi.ac.uk/vol1/fastq/ERR331/001/ERR3316071/ERR3316071_2.fastq.gz
    - prefix: ERR3316069
      platform: ILLUMINA
      base_count: 33234827596
      file: /volumes/data/by_accession/GCA_902806685.1/reads/ERR3316069_1.fastq.gz;/volumes/data/by_accession/GCA_902806685.1/reads/ERR3316069_2.fastq.gz
      url: ftp.sra.ebi.ac.uk/vol1/fastq/ERR331/009/ERR3316069/ERR3316069_1.fastq.gz;ftp.sra.ebi.ac.uk/vol1/fastq/ERR331/009/ERR3316069/ERR3316069_2.fastq.gz
    - prefix: ERR3316072
      platform: ILLUMINA
      base_count: 30325234266
      file: /volumes/data/by_accession/GCA_902806685.1/reads/ERR3316072_1.fastq.gz;/volumes/data/by_accession/GCA_902806685.1/reads/ERR3316072_2.fastq.gz
      url: ftp.sra.ebi.ac.uk/vol1/fastq/ERR331/002/ERR3316072/ERR3316072_1.fastq.gz;ftp.sra.ebi.ac.uk/vol1/fastq/ERR331/002/ERR3316072/ERR3316072_2.fastq.gz
revision: 0
settings:
  blast_chunk: 100000
  blast_max_chunks: 10
  blast_overlap: 0
  blast_min_length: 1000
  taxdump: /volumes/databases/taxdump_2021_03
  tmp: /tmp
similarity:
  defaults:
    evalue: 1.0e-10
    import_evalue: 1.0e-25
    max_target_seqs: 10
    taxrule: bestdistorder
  diamond_blastx:
    name: reference_proteomes
    path: /volumes/databases/uniprot_2021_03
  diamond_blastp:
    name: reference_proteomes
    path: /volumes/databases/uniprot_2021_03
    import_max_target_seqs: 100000
  blastn:
    name: nt
    path: /volumes/databases/ncbi_nt_2021_04
taxon:
  name: Maniola hyperantus
  taxid: '2795564'
version: 1
```

In this example, `url:` definitions are optional and used to show the source for publicly available files. The `file:` keys give locations of the files locally and must be completed.

The assembly `span:` and reads `base_count:` need only be specified if reads coverage `max:` is to be used for the purposes of subsampling read files when mapping.

BUSCO will be run for all `lineages:` in the busco section. Any lineages also specified in `basal_lineages:` will be used as sources of BUSCO genes for the diamond_blastp step. 

## Running the pipeline

For public assemblies, the script `scripts/generate_config.py` will fetch copies of assembly and read files and generate a YAML config file. There is also a `run_btk_pipeline.sh` wrapper script that will call `generate_config.py` and run the full meta pipeline when called with a public assembly accession:

```
run_btk_pipeline.sh GCA_902806685.1
```

The snakemake command in this script may be used as an example for running the pipeline on local assemblies.
