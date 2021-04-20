#!/usr/bin/env python3

"""
Generate config files for BlobToolKit insdc-pipeline.

Usage:
  insdc_assemblies_to_config.py <config_file>
    [--taxdump /path/to/ncbi_new_taxdump] [--rank genus] [--root 2759]
    [--offset 0] [--strategy WGS] [--out /path/to/output/directory]

Options:
  --taxdump=<taxdump>    Path to NCBI taxdump directory [default: ../taxdump]
  --rank=<rank>          Similarity search database masking level [default: genus]
  --root=<root>          Root taxID [default: 2759] (default is all Eukaryota)
  --out=<out>            Path to output directory [default: .]
  --offset=<offset>     Number of records to skip [default: 0]
  --strategy=<strategy>  Sequencing strategy [default: WGS]
"""

import os
import re
import requests
import sys
import tolkein
import yaml
from docopt import docopt
from pathlib import Path
from defusedxml import ElementTree as ET
from collections import defaultdict
from copy import deepcopy
import taxonomy

STEP = 50  # how many assembly records to request at a time

MIN_SPAN = 10000000

opts = docopt(__doc__)

NODES = str(Path(opts['--taxdump']) / 'nodes.dmp')
if not os.path.isfile(NODES):
    print("ERROR: File '%s' does not exist" % NODES, file=sys.stderr)
    quit(__doc__)

NAMES = str(Path(opts['--taxdump']) / 'names.dmp')
if not os.path.isfile(NAMES):
    print("ERROR: File '%s' does not exist" % NAMES, file=sys.stderr)
    quit(__doc__)

LINEAGES = str(Path(opts['--taxdump']) / 'taxidlineage.dmp')
if not os.path.isfile(LINEAGES):
    print("ERROR: File '%s' does not exist" % LINEAGES, file=sys.stderr)
    quit(__doc__)

OFFSET = int(opts['--offset'])
RANK = opts['--rank']
# awk '{print $5}' nodes.dmp | grep -v no | sort | uniq
valid_ranks = ('class', 'cohort', 'family', 'forma', 'genus', 'infraclass',
               'infraorder', 'kingdom', 'order', 'parvorder', 'phylum', 'species',
               'subclass', 'subfamily', 'subgenus', 'subkingdom', 'suborder',
               'subphylum', 'subspecies', 'subtribe', 'superclass', 'superfamily',
               'superkingdom', 'superorder', 'superphylum', 'tribe', 'varietas')
if RANK and RANK not in valid_ranks:
    print("ERROR: '%s' is not a valid value for --rank" % RANK, file=sys.stderr)
    quit(__doc__)

try:
    ROOT = int(opts['--root'])
except ValueError:
    print("ERROR: '%s' is not a valid value for --root" % opts['--root'], file=sys.stderr)
    quit(__doc__)

STRATEGY = opts['--strategy']

OUTDIR = opts['--out']
#
# try:
#     os.makedirs(OUTDIR, exist_ok=True)
# except OSError:
#     print("ERROR: Unable to create output directory '%s'" % OUTDIR, file=sys.stderr)
#     quit(__doc__)

DEFAULT_META = {}

if os.path.isfile(sys.argv[1]):
    with open(sys.argv[1], 'r') as fh:
        try:
            DEFAULT_META = yaml.full_load(fh)
        except yaml.YAMLError as exc:
            print(exc)

"""
Generate config files for all INSDC assemblies from a given <ROOT> taxon for
which read data are available.
Group generated files in directories by <RANK> to simplify reuse of filtered
BLAST databases.
"""


def grep_line(path, taxid):
    """Return the first line in the file at path beginning with taxid."""
    file = open(path, "r")
    for line in file:
        if re.match(str(taxid)+r'\s', line):
            return line
    return False


def split_line(line):
    """Split a lineage into a list of ancestral taxids."""
    taxids = [int(x) for x in line.split()[2:-1]]
    taxids.reverse()
    return taxids


def find_busco_lineages(taxid, lineage_file):
    """Work out which BUSCO sets to run for a given taxid."""
    BUSCO_SETS = {
        422676: 'aconoidasida',
        7898: 'actinopterygii',
        5338: 'agaricales',
        155619: 'agaricomycetes',
        33630: 'alveolata',
        5794: 'apicomplexa',
        6854: 'arachnida',
        6656: 'arthropoda',
        4890: 'ascomycota',
        8782: 'aves',
        5204: 'basidiomycota',
        68889: 'boletales',
        3699: 'brassicales',
        134362: 'capnodiales',
        33554: 'carnivora',
        91561: 'cetartiodactyla',
        34395: 'chaetothyriales',
        3041: 'chlorophyta',
        5796: 'coccidia',
        28738: 'cyprinodontiformes',
        7147: 'diptera',
        147541: 'dothideomycetes',
        3193: 'embryophyta',
        33392: 'endopterygota',
        314146: 'euarchontoglires',
        33682: 'euglenozoa',
        2759: 'eukaryota',
        5042: 'eurotiales',
        147545: 'eurotiomycetes',
        9347: 'eutheria',
        72025: 'fabales',
        4751: 'fungi',
        314147: 'glires',
        1028384: 'glomerellales',
        5178: 'helotiales',
        7524: 'hemiptera',
        7399: 'hymenoptera',
        5125: 'hypocreales',
        50557: 'insecta',
        314145: 'laurasiatheria',
        147548: 'leotiomycetes',
        7088: 'lepidoptera',
        4447: 'liliopsida',
        40674: 'mammalia',
        33208: 'metazoa',
        6029: 'microsporidia',
        6447: 'mollusca',
        4827: 'mucorales',
        1913637: 'mucoromycota',
        6231: 'nematoda',
        33183: 'onygenales',
        9126: 'passeriformes',
        5820: 'plasmodium',
        92860: 'pleosporales',
        38820: 'poales',
        5303: 'polyporales',
        9443: 'primates',
        4891: 'saccharomycetes',
        8457: 'sauropsida',
        4069: 'solanales',
        147550: 'sordariomycetes',
        33634: 'stramenopiles',
        32523: 'tetrapoda',
        155616: 'tremellomycetes',
        7742: 'vertebrata',
        33090: 'viridiplantae',
        71240: 'eudicots',
    }
    line = grep_line(lineage_file, taxid)
    lineages = []
    if line:
        ancestors = split_line(line)
        for taxid in ancestors:
            if taxid in BUSCO_SETS:
                lineages.append("%s_odb10" % BUSCO_SETS[taxid])
    return lineages


def count_assemblies(root):
    """
    Query INSDC assemblies descended from <root> taxon.

    Return count as int.
    """
    warehouse = 'https://www.ebi.ac.uk/ena/data/warehouse'
    url = ("%s/search?query=\"tax_tree(%d)\"&result=assembly&resultcount"
           % (warehouse, root))
    response = requests.get(url)
    if response.ok:
        m = re.search(r'[\d,+]+', response.content.decode('utf-8'))
        return int(m.group(0).replace(',', ''))
    else:
        return 0


def deep_find_text(data, tags):
    """
    Find nested attributes in xml.

    Return attribute value.
    """
    for tag in tags:
        try:
            data = data.find(tag)
        except:
            return None
    return data.text


def list_assemblies(root, offset, count):
    """
    Query INSDC assemblies descended from <root> taxon.

    Return list of <count> entries from <offset> as tree.
    """
    warehouse = 'https://www.ebi.ac.uk/ena/data/warehouse'
    url = ("%s/search?query=\"tax_tree(%d)\"&result=assembly&display=xml&offset=%d&length=%d"
           % (warehouse, root, offset, count))
    try:
        response = requests.get(url)
        if response.ok:
            return response.content
        else:
            return None
    except:
        result = list_assemblies(root, offset, count)
        return result


def assembly_meta(asm, default_meta):
    """Return dict of metadata values for an assembly."""
    meta = deepcopy(default_meta)
    if 'assembly' not in meta:
        meta['assembly'] = {}
    if 'taxon' not in meta:
        meta['taxon'] = {}
    genome_representation = asm.find('GENOME_REPRESENTATION').text
    if genome_representation == 'full':
        meta['assembly']['accession'] = asm.attrib['accession']
        meta['assembly']['bioproject'] = deep_find_text(asm, ('STUDY_REF', 'IDENTIFIERS', 'PRIMARY_ID'))
        meta['assembly']['biosample'] = deep_find_text(asm, ('SAMPLE_REF', 'IDENTIFIERS', 'PRIMARY_ID'))
        meta['taxon']['taxid'] = int(deep_find_text(asm, ('TAXON', 'TAXON_ID')))
        meta['taxon']['name'] = deep_find_text(asm, ('TAXON', 'SCIENTIFIC_NAME'))
        meta['assembly']['level'] = asm.find('ASSEMBLY_LEVEL').text
        meta['assembly']['alias'] = asm.attrib['alias']
        wgs_prefix = deep_find_text(asm, ('WGS_SET', 'PREFIX'))
        wgs_version = deep_find_text(asm, ('WGS_SET', 'VERSION'))
        if wgs_prefix and wgs_version:
            meta['assembly']['prefix'] = "%s%s" % (wgs_prefix, wgs_version.zfill(2))
        elif ' ' not in meta['assembly']['alias']:
            meta['assembly']['prefix'] = meta['assembly']['alias'].replace('.','_')
        else:
            meta['assembly']['prefix'] = meta['assembly']['accession'].replace('.','_')
        attributes = asm.find('ASSEMBLY_ATTRIBUTES')
        for attribute in attributes.findall('ASSEMBLY_ATTRIBUTE'):
            if attribute.find('TAG').text == 'total-length':
                meta['assembly']['span'] = int(attribute.find('VALUE').text)
            elif attribute.find('TAG').text == 'scaffold-count':
                meta['assembly']['scaffold-count'] = int(attribute.find('VALUE').text)
    return meta


def assembly_reads(biosample):
    """
    Query INSDC reads for a <biosample>.

    Return a dict of SRA accession, FASTQ ftp url, md5 and file size.
    """
    warehouse = 'https://www.ebi.ac.uk/ena/data/warehouse'
    url = ("%s/filereport?accession=%s&result=read_run&fields=run_accession,fastq_bytes,base_count,library_strategy,library_selection,library_layout,instrument_platform,fastq_ftp"
           % (warehouse, biosample))
    try:
        response = requests.get(url)
        sra = None
        if response.ok:
            lines = response.content.decode('utf-8').splitlines()
            if len(lines) > 1:
                sra = []
                header = lines[0].split('\t')
                for line in lines[1:]:
                    fields = line.split('\t')
                    values = {}
                    reads = False
                    strat = False
                    for i in range(0, len(header)):
                        value = fields[i]
                        if header[i] == 'fastq_bytes':
                            value = fields[i].split(';')
                            if int(value[0] or 0) > 0:
                                reads = True
                                if len(value) >= 2:
                                    values.update({'library_layout': 'PAIRED'})
                                else:
                                    values.update({'library_layout': 'SINGLE'})
                        if header[i] == 'library_strategy':
                            if value == STRATEGY:
                                strat = True
                        values.update({header[i]: value})
                    if reads and strat:
                        if 'base_count' not in values:
                            values['base_count'] = [0]
                        sra.append(values)
        return sra
    except:
        return None


def ncbi_assembly_reads(biosample):
    """
    Query NCBI INSDC reads for a <biosample>.

    Return a dict of SRA accession, etc.
    """
    eutils = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils'
    esearch = ("%s/esearch.fcgi?db=sra&term=%s&usehistory=y"
               % (eutils, biosample))
    response = requests.get(esearch)
    sra = None
    if response.ok:
        search = ET.fromstring(response.content)
        count = int(search.find('Count').text)
        if count > 0:
            print(biosample)
            webenv = search.find('WebEnv').text
            key = search.find('QueryKey').text
            # print(webenv)
            esummary = ("%s/esummary.fcgi?db=sra&query_key=%s&WebEnv=%s"
                        % (eutils, key, webenv))
            # print(esummary)
            sum_response = requests.get(esummary)
            if sum_response.ok:
                summaries = ET.fromstring(sum_response.content).findall('DocSum')
                for docsum in summaries:
                    text = docsum.find('Item').text
                    # print(text)
            # quit()
    return sra


graph = taxonomy.node_graph(NODES)
parents = taxonomy.parents_at_rank(graph, ROOT, RANK)
asm_count = count_assemblies(ROOT)


def base_count(x):
    """Return number of bases or zero."""
    if isinstance(x['base_count'], list):
        return int(x['base_count'][0] or 0)
    else:
        return 0


def current_versions(string='all'):
    """Get curent versions of hosted datasets from BTK API."""
    btk = "https://blobtoolkit.genomehubs.org/api/v1/search/%s" % string
    response = requests.get(btk)
    current = {}
    if response.ok:
        data = yaml.full_load(response.text)
        for asm in data:
            if 'version' in asm:
                current.update({asm['prefix']: asm['version']})
            else:
                current.update({asm['prefix']: 1})
    return current


def create_outdir(span, version=1, _lineage='all'):
    """Create output directory."""
    span = tolkein.tobin.readable_bin(span)
    name = "%s/v%s/%s" % (OUTDIR, str(version), span)
    os.makedirs("%s/" % name, exist_ok=True)
    return name


search_term = 'all'
with open(NAMES, 'r') as fh:
    lines = fh.readlines()
    for l in lines:
        l = l[:-3]
        parts = re.split(r'\t\|\t', l)
        if parts[0] == str(ROOT) and parts[3] == 'scientific name':
            search_term = parts[1]
versions = current_versions(search_term)

step = STEP
for offset in range(OFFSET, asm_count + 1, step):
    count = step if offset + step < asm_count else asm_count - offset + 1
    print("%d: %d" % (offset, count))
    xml = list_assemblies(ROOT, offset, count)
    assemblies = ET.fromstring(xml)
    for assembly in assemblies:
        meta = {}
        meta = assembly_meta(assembly, DEFAULT_META)
        if 'span' not in meta['assembly'] or meta['assembly']['span'] < MIN_SPAN:
            continue
        if 'prefix' in meta['assembly'] and 'biosample' in meta['assembly'] and meta['assembly']['biosample']:
            if 'similarity' not in meta:
                meta['similarity'] = {}
            if 'default' not in meta['similarity']:
                meta['similarity']['defaults'] = {}
            if RANK:
                if str(meta['taxon']['taxid']) in parents:
                    meta['taxon'][RANK] = int(parents[str(meta['taxon']['taxid'])])
                    meta['similarity']['defaults']['mask_ids'] = [meta['taxon'][RANK]]
            if 'reads' not in meta:
                meta['reads'] = {}
            if 'busco' not in meta:
                meta['busco'] = {}
            meta['busco']['lineages'] = find_busco_lineages(meta['taxon']['taxid'], LINEAGES)
            sra = assembly_reads(meta['assembly']['biosample'])
            base_counts = {}
            fastq_ftp = {}
            # if not sra:
            #     sra = ncbi_assembly_reads(meta['assembly']['biosample'])
            version = 1
            if meta['assembly']['prefix'] in versions:
                version = versions[meta['assembly']['prefix']] + 1
                continue
            meta['version'] = version
            lineage = 'all'
            if meta['busco']['lineages']:
                lineage = meta['busco']['lineages'][0]
            print(meta['assembly']['prefix'])
            if sra:
                sra.sort(key=lambda x: base_count(x), reverse=True)
                platforms = defaultdict(dict)
                for d in sra:
                    platforms[d['instrument_platform']].update({d['run_accession']: d})
                for platform, data in platforms.items():
                    meta['reads'][platform] = {}
                    strategies = defaultdict(list)
                    for key, value in data.items():
                        strategies[value['library_strategy']].append(key)
                    for strategy, accessions in strategies.items():
                        paired = []
                        single = []
                        for acc in accessions:
                            if data[acc]['library_layout'] == 'PAIRED':
                                paired.append(acc)
                            else:
                                single.append(acc)
                            base_counts[acc] = int(data[acc]['base_count'] or 0)
                            fastq_ftp[acc] = data[acc]['fastq_ftp']
                        if paired or single:
                            meta['reads'][platform][strategy] = {}
                            if paired:
                                meta['reads'][platform][strategy]['paired'] = paired
                            if single:
                                meta['reads'][platform][strategy]['single'] = single
                short_n = 3
                long_n = 10
                strategy = 'WGS'
                meta['reads']['paired'] = []
                meta['reads']['single'] = []
                for platform in ('ILLUMINA', 'LS454'):
                    if platform in meta['reads']:
                        if 'paired' in meta['reads'][platform][strategy]:
                            new_reads = meta['reads'][platform][strategy]['paired'][:short_n]
                            meta['reads']['paired'].extend([acc, platform, base_counts[acc], fastq_ftp[acc]]
                                                           for acc in new_reads)
                            short_n -= len(meta['reads']['paired'])
                        if short_n > 0:
                            if 'single' in meta['reads'][platform][strategy]:
                                new_reads = meta['reads'][platform][strategy]['single'][:short_n]
                                meta['reads']['single'].extend([acc, platform, base_counts[acc], fastq_ftp[acc]]
                                                               for acc in new_reads)
                                short_n -= len(meta['reads']['single'])
                for platform in ('PACBIO_SMRT', 'OXFORD_NANOPORE'):
                    if platform in meta['reads']:
                        if 'single' in meta['reads'][platform][strategy]:
                            new_reads = meta['reads'][platform][strategy]['single'][:long_n]
                            meta['reads']['single'] = [[acc, platform, base_counts[acc], fastq_ftp[acc]]
                                                       for acc in new_reads]
                outdir = create_outdir(meta['assembly']['span'], version, lineage)
                with open("%s/%s.yaml" % (outdir, meta['assembly']['prefix']), 'w') as fh:
                    fh.write(yaml.dump(meta))
            else:
                outdir = create_outdir(meta['assembly']['span'], version, lineage)
                with open("%s/%s.yaml" % (outdir, meta['assembly']['prefix']), 'w') as fh:
                    fh.write(yaml.dump(meta))
