import sys
import math

BWA_INDEX = ['amb','ann','bwt','pac','sa']

def apply_similarity_search_defaults():
    """
    Apply defaults to similarity search databases.
    """
    similarity = {}
    if 'defaults' in config['similarity']:
        for key,value in config['similarity']['defaults'].items():
            for db in config['similarity']['databases']:
                if key not in db:
                    db[key] = value
                similarity.update({db['name']:db})
    else:
        for db in config['similarity']['databases']:
            similarity.update({db['name']:db})
    return similarity

def get_read_info(config):
    """
    Create dict of sequencing strategies, platforms and base count for reads.
    """
    reads = {}
    min = 0
    max = math.inf
    platforms = ('ILLUMINA','PACBIO_SMRT','LS454')
    strategies = ('paired','single')
    if 'reads' not in config:
        return reads
    if 'coverage' in config['reads']:
        if 'min' in config['reads']['coverage']:
            min = config['reads']['coverage']['min']
        if 'max' in config['reads']['coverage']:
            max = config['reads']['coverage']['max']
    for strategy in strategies:
        if strategy in config['reads']:
            for row in config['reads'][strategy]:
                accession = row[0]
                platform = row[1]
                if platform not in platforms:
                    print("WARNING: platform %s is not recognised, must be one of %s" % (platform,platforms),file=sys.stderr)
                try:
                    bases = row[2]
                    coverage = bases / config['assembly']['span']
                except:
                    coverage = 10
                if coverage >= min:
                    reads[accession] = {'platform':platform,'coverage':coverage,'strategy':strategy}
                    if coverage > max:
                        reads[accession]['subsample'] = max / coverage
                        print("WARNING: read file %s will be subsampled due to high coverage (%.2f > %.2f)" % (accession,coverage,max),file=sys.stderr)
                else:
                    print("WARNING: skipping read file %s due to low coverage (%.2f < %.2f)" % (accession,coverage,min),file=sys.stderr)
    return reads

def ncbi_idmap(name):
    """
    Make a list of remote "accession2taxid" files to download
    """
    url = 'ftp.ncbi.nlm.nih.gov/pub/taxonomy/accession2taxid'
    db = similarity[name]
    return ' '.join(list(map(lambda x: "%s/%s.accession2taxid.gz" % (url,x),db['idmap'])))

def list_similarity_results(config):
    """
    Generate a list of output filenames for sequence similarity searches
    based on list of databases in "config['similarity']".
    """
    path = []
    for db in config['similarity']['databases']:
        # suffix = 'out' if db['tool'] == 'blast' else 'taxified.out'
        suffix = 'out'
        program = 'blastn' if db['type'] == 'nucl' else 'blastx' if db['tool'] == 'blast' else 'diamond'
        masked = ''
        if 'mask_ids' in db and isinstance(db['mask_ids'],(list,)):
            masked = "minus.%s" % '.'.join(str(mask) for mask in db['mask_ids'])
        else:
            masked = 'full'
        path.append("%s.%s.%s.root.%s.%s.%s" % (config['assembly']['prefix'],program,db['name'],db['root'],masked,suffix))
    return path

def blast_query_file(name,assembly):
    """
    Generate filename for filtered query file for similarity searches.
    """
    file = assembly
    if 'exclude_hits' in similarity[name]:
        for db in similarity[name]['exclude_hits']:
            file = db + '_filtered.' + file
    return file

def list_sra_accessions(reads):
    """
    Return a list SRA accessions.
    """
    accessions = []
    if reads is not None:
        accessions = reads.keys()
    return accessions

def generate_mapping_command(accession,reads):
    """
    Generate a read mapping command appropriate to the
    sequencing strategy and library type.
    """
    cmd = 'bwa mem'
    if reads[accession]['platform'] == 'ILLUMINA':
        cmd = 'minimap2 -ax sr'
    elif reads[accession]['platform'] == 'PACBIO_SMRT':
        cmd = 'minimap2 -ax map-pb'
    elif reads[accession]['platform'] == 'ONT_MINION':
        cmd = 'minimap2 -ax map-ont'
    return cmd

def list_read_files(accession,reads,subsample):
    """
    List read files.
    """
    files = ''
    ext = 'fastq.gz'
    if subsample:
        ext = 'subsampled.fastq.gz'
    if reads[accession]['strategy'] == 'paired':
        files = ["%s_1.%s" % (accession,ext), "%s_2.%s" % (accession,ext)]
    elif reads[accession]['platform'] == 'PACBIO_SMRT':
        files = ["%s_subreads.%s" % (accession,ext)]
    else:
        files = ["%s.%s" % (accession,ext)]
    return files

def generate_subsample_command(accession,reads):
    """
    Generate a read mapping command appropriate to the
    sequencing strategy and library type.
    """
    cmd = 'mv'
    arrow = ''
    seed = 100
    if 'coverage' in reads and 'seed' in reads['coverage']:
        seed = reads['coverage']['seed']
    if 'subsample' in reads[accession]:
        cmd = "seqtk sample -s%s" % seed
        arrow = "%.2f | pigz -c > " % reads[accession]['subsample']
    return [cmd,arrow]

def prepare_ebi_sra_url(acc,suffix):
    base = 'ftp://ftp.sra.ebi.ac.uk/vol1/fastq'
    subdir = "/00%s" % acc[-1:] if len(acc) == 10 else ''
    url = "%s/%s%s/%s/%s%s" % ( base, acc[:6], subdir, acc, acc, suffix )
    return url

def prepare_ncbi_assembly_url(accession,name):
    base = 'ftp://ftp.ncbi.nlm.nih.gov/genomes/all'
    acc = accession.replace('_','').split('.',1)[0]
    path = '/'.join(acc[i:i+3] for i in range(0, len(acc), 3))
    asm = "%s_%s" % ( accession, name.replace(' ', '_') )
    url = "%s/%s/%s/%s_genomic.fna.gz" % ( base, path, asm, asm )
    return url

# def prepare_ebi_sra_url(acc):
#     base = 'ftp://ftp.sra.ebi.ac.uk/vol1'
#     subdir = "/00%s" % acc[-1:] if len(acc) == 10 else ''
#     url = "%s/%s/%s%s/%s" % ( base, acc[:3].lower(), acc[:6], subdir, acc )
#     return url

def cov_files_by_platform(reads,assembly,platform):
    """
    Return a list of coverage files for a given sequencing platform.
    """
    accessions = []
    if reads is not None:
        accessions += [accession for accession in reads if reads[accession]['platform'] == platform]
    return list(map(lambda sra: "%s.%s.bam.cov" % (assembly,sra),accessions))

def platform_cov_files(reads,assembly):
    platforms = set()
    if reads is not None:
        for accession in reads:
            if reads[accession]['platform'] not in platforms:
                platforms.add(reads[accession]['platform'])
    return list(map(lambda platform: "%s.%s.sum.cov" % (assembly,platform),platforms))