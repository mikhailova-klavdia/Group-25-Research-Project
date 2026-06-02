"""
TAL1 locus analysis tools for exploring T-cell acute lymphoblastic leukemia associated mutations.

This MCP Server provides 4 tools:
1. visualize_variant_positions: Visualize genomic context and positions of variants near a gene
2. predict_variant_effects: Predict functional impact of a variant on gene expression, accessibility and histone marks
3. compare_variant_effects: Compare predicted effects of disease variants versus background variants
4. analyze_tal1_variants: Complete TAL1 variant analysis workflow with oncogenic and background variants

All tools were extracted from `alphagenome/colabs/example_analysis_workflow.ipynb`.
"""

# Define the MCP server and import required packages
import io
import itertools
import os
from pathlib import Path
from datetime import datetime
from typing import Annotated, Optional, List, Dict, Any

import numpy as np
import pandas as pd
import plotnine as gg
import matplotlib.pyplot as plt
from fastmcp import FastMCP

from alphagenome import colab_utils
from alphagenome.data import gene_annotation
from alphagenome.data import genome
from alphagenome.data import transcript as transcript_utils
from alphagenome.models import dna_client
from alphagenome.models import variant_scorers
from alphagenome.visualization import plot_components

# Define the INPUT_DIR and OUTPUT_DIR
# Project root is two levels up from this file (src/tools/example_analysis_workflow.py)
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
DEFAULT_INPUT_DIR = PROJECT_ROOT / "tmp_inputs" / "example_analysis_workflow"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "tmp_outputs" / "example_analysis_workflow"

INPUT_DIR = Path(os.environ.get("EXAMPLE_ANALYSIS_WORKFLOW_INPUT_DIR", DEFAULT_INPUT_DIR))
OUTPUT_DIR = Path(os.environ.get("EXAMPLE_ANALYSIS_WORKFLOW_OUTPUT_DIR", DEFAULT_OUTPUT_DIR))

# Mkdir if not exist
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Define the timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Define the MCP server
example_analysis_workflow_mcp = FastMCP(name="example_analysis_workflow")

# Utility functions (not exposed as tools)
def get_oncogenic_tal1_variants() -> pd.DataFrame:
    """Returns a dataframe of oncogenic T-ALL variants that affect TAL1."""
    variant_data = """
ID	CHROM	POS	REF	ALT	output	Study ID	Study Variant ID
Jurkat	chr1	47239296	C	CCGTTTCCTAACC	1	Mansour_2014
MOLT-3	chr1	47239296	C	ACC	1	Mansour_2014
Patient_1	chr1	47239296	C	AACG	1	Mansour_2014
Patient_2	chr1	47239291	CTAACC	TTTACCGTCTGTTAACGGC	1	Mansour_2014
Patient_3-5	chr1	47239296	C	ACG	1	Mansour_2014
Patient_6	chr1	47239296	C	ACC	1	Mansour_2014
Patient_7	chr1	47239295	AC	TCAAACTGGTAACC	1	Mansour_2014
Patient_8	chr1	47239296	C	AACC	1	Mansour_2014
new 3' enhancer 1	chr1	47212072	T	TGGGTAAACCGTCTGTTCAGCG	1	Smith_2023	UPNT802
new 3' enhancer 2	chr1	47212074	G	GAACGTT	1	Smith_2023	UPNT613
intergenic SNV 1	chr1	47230639	C	T	1	Liu_2020	SJALL043861_D1
intergenic SNV 2	chr1	47230639	C	T	1	Liu_2020	SJALL018373_D1
SJALL040467_D1	chr1	47239296	C	AACC	1	Liu_2020	SJALL040467_D1
PATBGC	chr1	47239296	C	AACC	1	Liu_2017	PATBGC
PATBTX	chr1	47239296	C	ACGGATATAACC	1	Liu_2017	PATBTX
PARJAY	chr1	47239296	C	ACGGAATTTCTAACC	1	Liu_2017	PARJAY
PARSJG	chr1	47239296	C	AACC	1	Liu_2017	PARSJG
PASYAJ	chr1	47239296	C	AACC	1	Liu_2017	PASYAJ
PATRAB	chr1	47239293	TTA	CTAACGG	1	Liu_2017	PATRAB
PAUBXP	chr1	47239296	C	ACC	1	Liu_2017	PAUBXP
PATENL	chr1	47239296	C	AACC	1	Liu_2017	PATENL
PARNXJ	chr1	47239296	C	ACG	1	Liu_2017	PARNXJ
PASXSI	chr1	47239296	C	AACC	1	Liu_2017	PASXSI
PASNEH	chr1	47239296	C	ACC	1	Liu_2017	PASNEH
PAUAFN	chr1	47239296	C	AACC	1	Liu_2017	PAUAFN
PARASZ	chr1	47239296	C	ACC	1	Liu_2017	PARASZ
PARWNW	chr1	47239296	C	ACC	1	Liu_2017	PARWNW
PASFKA	chr1	47239293	TTA	ACCGTTAATCAA	1	Liu_2017	PASFKA
PATEIT	chr1	47239296	C	AC	1	Liu_2017	PATEIT
PASMHF	chr1	47239296	C	AC	1	Liu_2017	PASMHF
PARJNX	chr1	47239296	C	AC	1	Liu_2017	PARJNX
PASYWF	chr1	47239296	C	AC	1	Liu_2017	PASYWF
"""
    return pd.read_table(io.StringIO(variant_data), sep='\t')


def generate_background_variants(
    variant: genome.Variant, max_number: int = 100
) -> pd.DataFrame:
    """Generates a dataframe of background variants for a given variant."""
    nucleotides = np.array(list('ACGT'), dtype='<U1')

    def generate_unique_strings(n, max_number, random_seed=42):
        """Generates unique random strings of length n."""
        rng = np.random.default_rng(random_seed)

        if 4**n < max_number:
            raise ValueError(
                'Cannot generate that many unique strings for the given length.'
            )

        generated_strings = set()
        while len(generated_strings) < max_number:
            indices = rng.integers(0, 4, size=n)
            new_string = ''.join(nucleotides[indices])
            if new_string != variant.alternate_bases:
                generated_strings.add(new_string)
        return list(generated_strings)

    permutations = []
    if 4 ** len(variant.alternate_bases) < max_number:
        # Get all
        for p in itertools.product(
            nucleotides, repeat=len(variant.alternate_bases)
        ):
            permutations.append(''.join(p))
    else:
        # Sample some
        permutations = generate_unique_strings(
            len(variant.alternate_bases), max_number
        )
    ism_candidates = pd.DataFrame({
        'ID': ['mut_' + str(variant.position) + '_' + x for x in permutations],
        'CHROM': variant.chromosome,
        'POS': variant.position,
        'REF': variant.reference_bases,
        'ALT': permutations,
        'output': 0.0,
        'original_variant': variant.name,
    })
    return ism_candidates


def vcf_row_to_variant(vcf_row: pd.Series) -> genome.Variant:
    """Parse a row of a vcf df into a genome.Variant."""
    variant = genome.Variant(
        chromosome=str(vcf_row.CHROM),
        position=int(vcf_row.POS),
        reference_bases=vcf_row.REF,
        alternate_bases=vcf_row.ALT,
        name=vcf_row.ID,
    )
    return variant


def inference_df(
    qtl_df: pd.DataFrame,
    input_sequence_length: int,
) -> pd.DataFrame:
    """Returns a pd.DataFrame with variants and intervals ready for inference."""
    df = []
    for _, row in qtl_df.iterrows():
        variant = vcf_row_to_variant(row)

        interval = genome.Interval(
            chromosome=row['CHROM'], start=row['POS'], end=row['POS']
        ).resize(input_sequence_length)

        df.append({
            'interval': interval,
            'variant': variant,
            'output': row['output'],
            'variant_id': row['ID'],
            'POS': row['POS'],
            'REF': row['REF'],
            'ALT': row['ALT'],
            'CHROM': row['CHROM'],
        })
    return pd.DataFrame(df)


def coarse_grained_mute_groups(eval_df):
    grp = []
    for row in eval_df.itertuples():
        if row.POS >= 47239290:  # MUTE site.
            if row.ALT_len > 4:
                grp.append('MUTE' + '_other')
            else:
                grp.append('MUTE' + '_' + str(row.ALT_len))
        else:
            grp.append(str(row.POS) + '_' + str(row.ALT_len))

    grp = pd.Series(grp)
    return pd.Categorical(grp, categories=sorted(grp.unique()), ordered=True)


def get_tal1_score_for_cd34_cells(score_data):
    """Extracts the TAL1 expression score in CD34+ cells from the model output."""
    gene_index = score_data.obs.query('gene_name == "TAL1"').index[0]
    cell_type_index = (
        score_data.var.query('ontology_curie == "CL:0001059"').index[0]
    )
    return score_data[gene_index, cell_type_index].X[0, 0]


# Public tools exposed to users
@example_analysis_workflow_mcp.tool
def visualize_variant_positions(
    variants_file: Annotated[Optional[str], "Path to TSV/CSV file with variant data"] = None,
    gene_chromosome: Annotated[str, "Chromosome of gene (e.g., 'chr1')"] = "chr1",
    gene_start: Annotated[int, "Gene interval start position"] = 47209255,
    gene_end: Annotated[int, "Gene interval end position"] = 47242023,
    gene_strand: Annotated[str, "Gene strand ('+' or '-')"] = "-",
    gtf_url: Annotated[str, "URL to GENCODE GTF annotation file"] = "https://storage.googleapis.com/alphagenome/reference/gencode/hg38/gencode.v46.annotation.gtf.gz.feather",
    api_key: Annotated[Optional[str], "AlphaGenome API key"] = None,
    out_prefix: Annotated[str, "Output file prefix"] = f"variant_positions_{timestamp}"
) -> Dict[str, Any]:
    """
    Visualize genomic context and positions of variants near a gene of interest.
    """
    # Load variants
    if variants_file:
        if variants_file.endswith('.tsv'):
            variants_df = pd.read_csv(variants_file, sep='\t')
        else:
            variants_df = pd.read_csv(variants_file)
    
    # If no variants provided, use TAL1 oncogenic variants as default
    if variants_file is None:
        variants_df = get_oncogenic_tal1_variants()
    
    # Load gene annotations
    gtf = pd.read_feather(gtf_url)
    gtf_transcript = gene_annotation.filter_transcript_support_level(
        gene_annotation.filter_protein_coding(gtf), ['1']
    )
    gtf_longest_transcript = gene_annotation.filter_to_longest_transcript(
        gtf_transcript
    )
    longest_transcript_extractor = transcript_utils.TranscriptExtractor(
        gtf_longest_transcript
    )
    
    # Define gene interval
    gene_interval = genome.Interval(
        chromosome=gene_chromosome,
        start=gene_start,
        end=gene_end,
        strand=gene_strand
    )
    
    # Gather unique variant positions and create labels
    unique_positions = variants_df['POS'].unique()
    unique_positions.sort()
    
    # Build position labels to avoid overplotting
    labels = []
    prev_pos = -1
    for pos in unique_positions:
        if prev_pos != -1 and abs(pos - prev_pos) < 100:
            labels.append('')  # Skip label for close positions
        else:
            labels.append(str(pos))
        prev_pos = pos
    
    # Build plot
    fig = plot_components.plot(
        [
            plot_components.TranscriptAnnotation(
                longest_transcript_extractor.extract(gene_interval)
            ),
        ],
        annotations=[
            plot_components.VariantAnnotation(
                [
                    genome.Variant(
                        chromosome=gene_chromosome,
                        position=x,
                        reference_bases='N',
                        alternate_bases='N',
                    )
                    for x in unique_positions
                ],
                labels=labels,
                use_default_labels=False,
            )
        ],
        interval=gene_interval,
        title=f'Positions of variants on {gene_chromosome}:{gene_start}-{gene_end}',
    )
    
    # Save figure
    output_path = OUTPUT_DIR / f"{out_prefix}.png"
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    # Save variant positions data
    positions_csv = OUTPUT_DIR / f"{out_prefix}_positions.csv"
    positions_df = pd.DataFrame({
        'position': unique_positions,
        'label': labels[:len(unique_positions)]
    })
    positions_df.to_csv(positions_csv, index=False)
    
    return {
        "message": f"Visualized {len(unique_positions)} variant positions",
        "artifacts": [
            {
                "description": "Variant positions visualization",
                "path": str(output_path.resolve())
            },
            {
                "description": "Variant positions data",
                "path": str(positions_csv.resolve())
            }
        ]
    }


@example_analysis_workflow_mcp.tool
def predict_variant_effects(
    variant_chrom: Annotated[str, "Variant chromosome (e.g., 'chr1')"] = "chr1",
    variant_pos: Annotated[int, "Variant position"] = 47239296,
    variant_ref: Annotated[str, "Reference allele"] = "C",
    variant_alt: Annotated[str, "Alternate allele"] = "CCGTTTCCTAACC",
    variant_name: Annotated[Optional[str], "Variant identifier/name"] = None,
    gene_chromosome: Annotated[str, "Gene chromosome"] = "chr1",
    gene_start: Annotated[int, "Gene interval start"] = 47209255,
    gene_end: Annotated[int, "Gene interval end"] = 47242023,
    gene_strand: Annotated[str, "Gene strand"] = "-",
    ontology_terms: Annotated[List[str], "Ontology terms for cell type (e.g., ['CL:0001059'] for CD34+)"] = ["CL:0001059"],
    sequence_length: Annotated[int, "Input sequence length (power of 2, e.g., 1048576 for 2^20)"] = 1048576,
    gtf_url: Annotated[str, "URL to GENCODE GTF file"] = "https://storage.googleapis.com/alphagenome/reference/gencode/hg38/gencode.v46.annotation.gtf.gz.feather",
    api_key: Annotated[Optional[str], "AlphaGenome API key"] = None,
    out_prefix: Annotated[str, "Output file prefix"] = f"variant_effects_{timestamp}"
) -> Dict[str, Any]:
    """
    Predict functional impact of a variant on gene expression, accessibility and histone marks.
    """
    # Create DNA model
    if api_key:
        dna_model = dna_client.create(api_key)
    else:
        dna_model = dna_client.create(colab_utils.get_api_key())
    
    # Load gene annotations
    gtf = pd.read_feather(gtf_url)
    gtf_transcript = gene_annotation.filter_transcript_support_level(
        gene_annotation.filter_protein_coding(gtf), ['1']
    )
    gtf_longest_transcript = gene_annotation.filter_to_longest_transcript(
        gtf_transcript
    )
    longest_transcript_extractor = transcript_utils.TranscriptExtractor(
        gtf_longest_transcript
    )
    
    # Define variant and interval
    variant = genome.Variant(
        chromosome=variant_chrom,
        position=variant_pos,
        reference_bases=variant_ref,
        alternate_bases=variant_alt,
        name=variant_name or f"{variant_chrom}:{variant_pos}_{variant_ref}>{variant_alt}"
    )
    
    gene_interval = genome.Interval(
        chromosome=gene_chromosome,
        start=gene_start,
        end=gene_end,
        strand=gene_strand
    )
    
    # Make predictions
    output = dna_model.predict_variant(
        interval=gene_interval.resize(sequence_length),
        variant=variant,
        requested_outputs={
            dna_client.OutputType.RNA_SEQ,
            dna_client.OutputType.CHIP_HISTONE,
            dna_client.OutputType.DNASE,
        },
        ontology_terms=ontology_terms,
    )
    
    # Build plot
    longest_transcripts = longest_transcript_extractor.extract(gene_interval)
    fig = plot_components.plot(
        [
            plot_components.TranscriptAnnotation(longest_transcripts),
            # RNA-seq tracks
            plot_components.Tracks(
                tdata=output.alternate.rna_seq.filter_to_nonpositive_strand()
                - output.reference.rna_seq.filter_to_nonpositive_strand(),
                ylabel_template='{biosample_name} ({strand})\n{name}',
                filled=True,
            ),
            # DNAse tracks
            plot_components.Tracks(
                tdata=output.alternate.dnase.filter_to_nonpositive_strand()
                - output.reference.dnase.filter_to_nonpositive_strand(),
                ylabel_template='{biosample_name} ({strand})\n{name}',
                filled=True,
            ),
            # Chip histone
            plot_components.Tracks(
                tdata=output.alternate.chip_histone.filter_to_nonpositive_strand()
                - output.reference.chip_histone.filter_to_nonpositive_strand(),
                ylabel_template='{biosample_name} ({strand})\n{name}',
                filled=True,
            ),
        ],
        annotations=[plot_components.VariantAnnotation([variant])],
        interval=gene_interval,
        title=(
            f'Effect of {variant.name} on predicted RNA Expression, DNAse, and ChIP-Histone'
        ),
    )
    
    # Save figure
    output_path = OUTPUT_DIR / f"{out_prefix}.png"
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    # Save variant info
    variant_csv = OUTPUT_DIR / f"{out_prefix}_variant.csv"
    variant_df = pd.DataFrame([{
        'variant_name': variant.name,
        'chromosome': variant.chromosome,
        'position': variant.position,
        'ref': variant.reference_bases,
        'alt': variant.alternate_bases,
        'ontology_terms': ','.join(ontology_terms)
    }])
    variant_df.to_csv(variant_csv, index=False)
    
    return {
        "message": f"Predicted effects for variant {variant.name}",
        "artifacts": [
            {
                "description": "Variant effect visualization",
                "path": str(output_path.resolve())
            },
            {
                "description": "Variant information",
                "path": str(variant_csv.resolve())
            }
        ]
    }


@example_analysis_workflow_mcp.tool
def compare_variant_effects(
    variants_file: Annotated[Optional[str], "Path to file with disease variants"] = None,
    number_background_variants: Annotated[int, "Number of background variants per disease variant"] = 3,
    gene_name: Annotated[str, "Gene name to score (e.g., 'TAL1')"] = "TAL1",
    ontology_term: Annotated[str, "Ontology term for cell type"] = "CL:0001059",
    sequence_length: Annotated[int, "Input sequence length"] = 1048576,
    api_key: Annotated[Optional[str], "AlphaGenome API key"] = None,
    out_prefix: Annotated[str, "Output file prefix"] = f"variant_comparison_{timestamp}"
) -> Dict[str, Any]:
    """
    Compare predicted gene expression effects of disease variants versus background variants.
    """
    # Validate input
    if variants_file is None:
        # Use default TAL1 oncogenic variants
        oncogenic_variants = get_oncogenic_tal1_variants()
    else:
        if variants_file.endswith('.tsv'):
            oncogenic_variants = pd.read_csv(variants_file, sep='\t')
        else:
            oncogenic_variants = pd.read_csv(variants_file)
    
    # Create DNA model
    if api_key:
        dna_model = dna_client.create(api_key)
    else:
        dna_model = dna_client.create(colab_utils.get_api_key())
    
    # Generate background variants
    variants = []
    for vcf_row in oncogenic_variants.itertuples():
        variants.append(
            genome.Variant(
                chromosome=str(vcf_row.CHROM),
                position=int(vcf_row.POS),
                reference_bases=vcf_row.REF,
                alternate_bases=vcf_row.ALT,
                name=vcf_row.ID,
            )
        )
    
    background_variants = pd.concat([
        generate_background_variants(variant, number_background_variants)
        for variant in variants
    ])
    all_variants = pd.concat([oncogenic_variants, background_variants])
    eval_df = inference_df(all_variants, input_sequence_length=sequence_length)
    
    # Additional annotations
    eval_df['ALT_len'] = eval_df['ALT'].str.len()
    eval_df['variant_group'] = (
        eval_df['POS'].astype(str) + '_' + eval_df['ALT_len'].astype(str)
    )
    eval_df['output'] = eval_df['output'].fillna(0) != 0
    eval_df['coarse_grained_variant_group'] = coarse_grained_mute_groups(eval_df)
    
    # Score the variants
    scores = dna_model.score_variants(
        intervals=eval_df['interval'].to_list(),
        variants=eval_df['variant'].to_list(),
        variant_scorers=[variant_scorers.RECOMMENDED_VARIANT_SCORERS['RNA_SEQ']],
        max_workers=2,
    )
    
    # Extract scores for gene and cell type
    eval_df[f'{gene_name.lower()}_diff'] = [
        get_tal1_score_for_cd34_cells(x[0]) for x in scores
    ]
    
    # Prepare plot data
    plot_df = eval_df.loc[eval_df.REF != eval_df.ALT].copy()
    plot_df['variant'] = plot_df['variant'].astype(str)
    plot_df = plot_df.loc[
        :,
        [
            'variant',
            'output',
            f'{gene_name.lower()}_diff',
            'coarse_grained_variant_group',
        ],
    ].drop_duplicates()
    
    # Create plots for each variant group
    facet_title_by_group = {}
    for group in plot_df.coarse_grained_variant_group.unique():
        group_data = plot_df[plot_df.coarse_grained_variant_group == group]
        if 'MUTE' in group:
            facet_title_by_group[group] = f"chr1:47239296\n{group.split('_')[1]} bp ins."
        else:
            pos, length = group.split('_')
            facet_title_by_group[group] = f"chr1:{pos}\n{length} bp"
    
    # Create comparison plots
    artifacts = []
    for i, group in enumerate(plot_df.coarse_grained_variant_group.unique()):
        subplot_df = pd.concat(
            [plot_df.assign(plot_group='density'), plot_df.assign(plot_group='rain')]
        )
        subplot_df = subplot_df[subplot_df.coarse_grained_variant_group == group]
        subplot_df = subplot_df[
            ~((subplot_df.plot_group == 'density') & (subplot_df.output))
        ]
        
        col_width = np.ptp(subplot_df[f'{gene_name.lower()}_diff']) / 200
        if col_width == 0:
            col_width = 0.01
        subplot_df['col_width'] = subplot_df['output'].map(
            {True: 1.5 * col_width, False: 1.25 * col_width}
        )
        
        plt_ = (
            gg.ggplot(subplot_df)
            + gg.aes(x=f'{gene_name.lower()}_diff')
            + gg.geom_col(
                gg.aes(
                    y=1,
                    width='col_width',
                    fill='output',
                    x=f'{gene_name.lower()}_diff',
                    alpha='output',
                ),
                data=subplot_df[subplot_df['plot_group'] == 'rain'],
            )
            + gg.geom_density(
                gg.aes(
                    x=f'{gene_name.lower()}_diff',
                    fill='output',
                ),
                data=subplot_df[subplot_df['plot_group'] == 'density'],
                color='white',
            )
            + gg.facet_wrap('~output + plot_group', nrow=1, scales='free_x')
            + gg.scale_alpha_manual({True: 1, False: 0.3})
            + gg.scale_fill_manual({True: '#FAA41A', False: 'gray'})
            + gg.labs(title=facet_title_by_group.get(group, group))
            + gg.theme_minimal()
            + gg.geom_vline(xintercept=0, linetype='dotted')
            + gg.theme(
                figure_size=(1.2, 3),
                legend_position='none',
                axis_text_x=gg.element_blank(),
                panel_grid_major_x=gg.element_blank(),
                panel_grid_minor_x=gg.element_blank(),
                strip_text=gg.element_blank(),
                axis_title_y=gg.element_blank(),
                axis_title_x=gg.element_blank(),
                plot_title=gg.element_text(size=9),
            )
            + gg.scale_y_reverse()
            + gg.coord_flip()
        )
        
        # Save individual plot
        plot_path = OUTPUT_DIR / f"{out_prefix}_{group}.png"
        plt_.save(plot_path, dpi=150)
        
        artifacts.append({
            "description": f"Comparison plot for {group}",
            "path": str(plot_path.resolve())
        })
    
    # Save comparison data
    comparison_csv = OUTPUT_DIR / f"{out_prefix}_scores.csv"
    eval_df.to_csv(comparison_csv, index=False)
    artifacts.append({
        "description": "Variant comparison scores",
        "path": str(comparison_csv.resolve())
    })
    
    return {
        "message": f"Compared {len(oncogenic_variants)} disease variants with {len(background_variants)} background variants",
        "artifacts": artifacts
    }


@example_analysis_workflow_mcp.tool
def analyze_tal1_variants(
    number_background_variants: Annotated[int, "Number of background variants per oncogenic variant"] = 20,
    sequence_length: Annotated[int, "Input sequence length"] = 1048576,
    gtf_url: Annotated[str, "URL to GENCODE GTF file"] = "https://storage.googleapis.com/alphagenome/reference/gencode/hg38/gencode.v46.annotation.gtf.gz.feather",
    api_key: Annotated[Optional[str], "AlphaGenome API key"] = None,
    out_prefix: Annotated[str, "Output file prefix"] = f"tal1_analysis_{timestamp}"
) -> Dict[str, Any]:
    """
    Complete TAL1 variant analysis workflow analyzing oncogenic T-ALL variants.
    """
    # Create DNA model
    if api_key:
        dna_model = dna_client.create(api_key)
    else:
        dna_model = dna_client.create(colab_utils.get_api_key())
    
    # Load gene annotations
    gtf = pd.read_feather(gtf_url)
    gtf_transcript = gene_annotation.filter_transcript_support_level(
        gene_annotation.filter_protein_coding(gtf), ['1']
    )
    gtf_longest_transcript = gene_annotation.filter_to_longest_transcript(
        gtf_transcript
    )
    longest_transcript_extractor = transcript_utils.TranscriptExtractor(
        gtf_longest_transcript
    )
    
    # Define TAL1 interval
    tal1_interval = genome.Interval(
        chromosome='chr1', start=47209255, end=47242023, strand='-'
    )
    
    # Get oncogenic variants
    oncogenic_variants = get_oncogenic_tal1_variants()
    
    # 1. Visualize variant positions
    unique_positions = oncogenic_variants['POS'].unique()
    unique_positions.sort()
    
    labels = [
        '47212072, 47212074',
        '',
        '47230639',
        '47239291 - 47239296',
        '',
        '',
        '',
    ]
    
    fig1 = plot_components.plot(
        [
            plot_components.TranscriptAnnotation(
                longest_transcript_extractor.extract(tal1_interval)
            ),
        ],
        annotations=[
            plot_components.VariantAnnotation(
                [
                    genome.Variant(
                        chromosome='chr1',
                        position=x,
                        reference_bases='N',
                        alternate_bases='N',
                    )
                    for x in unique_positions
                ],
                labels=labels,
                use_default_labels=False,
            )
        ],
        interval=tal1_interval,
        title='Positions of variants near TAL1',
    )
    
    positions_path = OUTPUT_DIR / f"{out_prefix}_positions.png"
    fig1.savefig(positions_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    # 2. Predict effects for first variant
    first_variant = vcf_row_to_variant(oncogenic_variants.iloc[0])
    ontology_terms = ['CL:0001059']
    
    output = dna_model.predict_variant(
        interval=tal1_interval.resize(sequence_length),
        variant=first_variant,
        requested_outputs={
            dna_client.OutputType.RNA_SEQ,
            dna_client.OutputType.CHIP_HISTONE,
            dna_client.OutputType.DNASE,
        },
        ontology_terms=ontology_terms,
    )
    
    longest_transcripts = longest_transcript_extractor.extract(tal1_interval)
    fig2 = plot_components.plot(
        [
            plot_components.TranscriptAnnotation(longest_transcripts),
            plot_components.Tracks(
                tdata=output.alternate.rna_seq.filter_to_nonpositive_strand()
                - output.reference.rna_seq.filter_to_nonpositive_strand(),
                ylabel_template='{biosample_name} ({strand})\n{name}',
                filled=True,
            ),
            plot_components.Tracks(
                tdata=output.alternate.dnase.filter_to_nonpositive_strand()
                - output.reference.dnase.filter_to_nonpositive_strand(),
                ylabel_template='{biosample_name} ({strand})\n{name}',
                filled=True,
            ),
            plot_components.Tracks(
                tdata=output.alternate.chip_histone.filter_to_nonpositive_strand()
                - output.reference.chip_histone.filter_to_nonpositive_strand(),
                ylabel_template='{biosample_name} ({strand})\n{name}',
                filled=True,
            ),
        ],
        annotations=[plot_components.VariantAnnotation([first_variant])],
        interval=tal1_interval,
        title=(
            'Effect of variant on predicted RNA Expression, DNAse, and ChIP-Histone'
            f' in CD34 positive HSC.\n{first_variant.name}'
        ),
    )
    
    effects_path = OUTPUT_DIR / f"{out_prefix}_effects.png"
    fig2.savefig(effects_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    # 3. Compare oncogenic vs background variants
    variants = []
    for vcf_row in oncogenic_variants.itertuples():
        variants.append(
            genome.Variant(
                chromosome=str(vcf_row.CHROM),
                position=int(vcf_row.POS),
                reference_bases=vcf_row.REF,
                alternate_bases=vcf_row.ALT,
                name=vcf_row.ID,
            )
        )
    
    background_variants = pd.concat([
        generate_background_variants(variant, number_background_variants)
        for variant in variants
    ])
    all_variants = pd.concat([oncogenic_variants, background_variants])
    eval_df = inference_df(all_variants, input_sequence_length=sequence_length)
    
    eval_df['ALT_len'] = eval_df['ALT'].str.len()
    eval_df['variant_group'] = (
        eval_df['POS'].astype(str) + '_' + eval_df['ALT_len'].astype(str)
    )
    eval_df['output'] = eval_df['output'].fillna(0) != 0
    eval_df['coarse_grained_variant_group'] = coarse_grained_mute_groups(eval_df)
    
    # Score variants
    scores = dna_model.score_variants(
        intervals=eval_df['interval'].to_list(),
        variants=eval_df['variant'].to_list(),
        variant_scorers=[variant_scorers.RECOMMENDED_VARIANT_SCORERS['RNA_SEQ']],
        max_workers=2,
    )
    
    eval_df['tal1_diff_in_cd34'] = [
        get_tal1_score_for_cd34_cells(x[0]) for x in scores
    ]
    
    # Save all results
    results_csv = OUTPUT_DIR / f"{out_prefix}_all_scores.csv"
    eval_df.to_csv(results_csv, index=False)
    
    # Create comparison plots for two example groups
    plot_df = eval_df.loc[eval_df.REF != eval_df.ALT].copy()
    plot_df['variant'] = plot_df['variant'].astype(str)
    plot_df = plot_df.loc[
        :,
        [
            'variant',
            'output',
            'tal1_diff_in_cd34',
            'coarse_grained_variant_group',
        ],
    ].drop_duplicates()
    
    comparison_plots = []
    for group in ['MUTE_2', 'MUTE_3']:
        if group not in plot_df.coarse_grained_variant_group.unique():
            continue
            
        subplot_df = pd.concat(
            [plot_df.assign(plot_group='density'), plot_df.assign(plot_group='rain')]
        )
        subplot_df = subplot_df[subplot_df.coarse_grained_variant_group == group]
        subplot_df = subplot_df[
            ~((subplot_df.plot_group == 'density') & (subplot_df.output))
        ]
        
        col_width = np.ptp(subplot_df.tal1_diff_in_cd34) / 200
        if col_width == 0:
            col_width = 0.01
        subplot_df['col_width'] = subplot_df['output'].map(
            {True: 1.5 * col_width, False: 1.25 * col_width}
        )
        
        title = f"chr1:47239296\n{group.split('_')[1]} bp ins." if 'MUTE' in group else group
        
        plt_ = (
            gg.ggplot(subplot_df)
            + gg.aes(x='tal1_diff_in_cd34')
            + gg.geom_col(
                gg.aes(
                    y=1,
                    width='col_width',
                    fill='output',
                    x='tal1_diff_in_cd34',
                    alpha='output',
                ),
                data=subplot_df[subplot_df['plot_group'] == 'rain'],
            )
            + gg.geom_density(
                gg.aes(
                    x='tal1_diff_in_cd34',
                    fill='output',
                ),
                data=subplot_df[subplot_df['plot_group'] == 'density'],
                color='white',
            )
            + gg.facet_wrap('~output + plot_group', nrow=1, scales='free_x')
            + gg.scale_alpha_manual({True: 1, False: 0.3})
            + gg.scale_fill_manual({True: '#FAA41A', False: 'gray'})
            + gg.labs(title=title)
            + gg.theme_minimal()
            + gg.geom_vline(xintercept=0, linetype='dotted')
            + gg.theme(
                figure_size=(1.2, 3),
                legend_position='none',
                axis_text_x=gg.element_blank(),
                panel_grid_major_x=gg.element_blank(),
                panel_grid_minor_x=gg.element_blank(),
                strip_text=gg.element_blank(),
                axis_title_y=gg.element_blank(),
                axis_title_x=gg.element_blank(),
                plot_title=gg.element_text(size=9),
            )
            + gg.scale_y_reverse()
            + gg.coord_flip()
        )
        
        comparison_path = OUTPUT_DIR / f"{out_prefix}_comparison_{group}.png"
        plt_.save(comparison_path, dpi=150)
        comparison_plots.append(str(comparison_path.resolve()))
    
    artifacts = [
        {
            "description": "TAL1 variant positions",
            "path": str(positions_path.resolve())
        },
        {
            "description": "First variant effects",
            "path": str(effects_path.resolve())
        },
        {
            "description": "All variant scores",
            "path": str(results_csv.resolve())
        }
    ]
    
    for comp_plot in comparison_plots:
        artifacts.append({
            "description": "Variant comparison plot",
            "path": comp_plot
        })
    
    return {
        "message": f"Completed TAL1 analysis with {len(oncogenic_variants)} oncogenic and {len(background_variants)} background variants",
        "artifacts": artifacts
    }