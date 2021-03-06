"""
Fetching data from UCSC genomes
Creating image with genetic variants for a given gene
"""

from sqlalchemy import *
from weblogolib import *
import sqlalchemy.orm as orm
from io import StringIO
import requests
# import sys
# import json

#########
# Connection to database

engine = create_engine('mysql+pymysql://genome@genome-mysql.cse.ucsc.edu/hg38')
session = orm.sessionmaker()(bind=engine)

###########
# Database tables metadata
meta = MetaData(bind=engine)
meta.reflect(only=['refGene', 'snp147Common'])

gene_table = Table('refGene',
    meta,
    PrimaryKeyConstraint('name'),
    extend_existing=True)


snp_table = Table('snp147Common',
    meta,
    PrimaryKeyConstraint('name'),
    extend_existing=True)


##################
# ORM mapping tables to  objects
class DatabaseObject(object):
    def __repr__(self):
        return "\n".join(
            ["{:20s}: {}".format(key, self.__dict__[key]) for key in sorted(self.__dict__.keys())]
        )


class Gene(DatabaseObject):
    def __repr__(self):
        return("Gene {} ({})\nCDS location {} {}-{} on strand {}".format(
            g.name, g.name2, g.chrom, g.cdsStart, g.cdsEnd, g.strand))


class SNP(DatabaseObject):
    snp_class = Column('class', String)


orm.mapper(SNP, snp_table)
orm.mapper(Gene, gene_table)


def get_genome_sequence_ensembl(chrom, start, end):
    """
    API described here http://rest.ensembl.org/documentation/info/sequence_region
    """
    url = 'https://rest.ensembl.org/sequence/region/human/{0}:{1}..{2}:1?content-type=application/json'.format(chrom, start, end)
    r = requests.get(url, headers={"Content-Type": "application/json"}, timeout=10.000)
    if not r.ok:
        print("REST Request FAILED")
        decoded = r.json()
        print(decoded['error'])
        return
    else:
        print("REST Request OK")
        decoded = r.json()
        return decoded['seq']


def get_variants(gene):
    variants = {}
    for g in session.query(Gene).filter(Gene.name2 == gene).filter(Gene.cdsEnd > Gene.cdsStart).all():
        print(g.name)
        snps = session.query(SNP).filter(
            SNP.snp_class == 'single').filter(
            SNP.strand == g.strand).filter(
            SNP.chrom == g.chrom).filter(
            SNP.chromStart >= g.cdsStart).filter(
            SNP.chromEnd <= g.cdsEnd).all()
        for s in snps:
            alleles = s.alleles.decode('utf-8')[:-1].split(",")
            print(s.name, s.chrom, s.chromStart, s.chromEnd, alleles)
            variants[(s.chrom, s.chromStart)] = alleles
        break  # analyze only one gene record, skip the rest - for testing
    return variants


def get_logo(gene):
    variants = get_variants(gene)

    chrom = list(variants.keys())[0][0]
    positions = [k[1] for k in variants.keys()]
    start = min(positions)
    end = max(positions)

    sequence = get_genome_sequence_ensembl(chrom, start, end)

    print("Sequence Length", len(sequence))
    if len(sequence) > 5000:
        sequence = sequence[:5000]  # limit the length of sequence
        print("Updated sequence Length", len(sequence))
    seqs = ""
    seqs = ">\n"+sequence+"\n"
    for (chrom, position), alleles in variants.items():
        print(position - start, len(sequence))
        if position - start >= len(sequence):
            continue
        for allele in alleles:
            seq = ["-"] * len(sequence)
            # seq[start - position] = allele
            seq[position-start] = allele
            seqs += ">\n" + "".join(seq) + "\n"

    sequences = read_seq_data(StringIO(seqs))
    data = LogoData.from_seqs(sequences)
    options = LogoOptions()
    options.title = 'A Logo Title'
    options.scale_width = False
    options.logo_end = 1000
    options.stacks_per_line = 50
    formatting = LogoFormat(data, options)

    png = png_formatter(data, formatting)
    return png
