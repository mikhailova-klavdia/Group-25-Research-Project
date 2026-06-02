"""
Visualize AlphaGenome predictions across multiple modalities.

This MCP Server provides 8 tools:
1. visualize_gene_expression: Visualize RNA expression (RNA_SEQ, CAGE) for specified tissues
2. visualize_variant_expression_effect: Visualize the effect of a variant on gene expression
3. visualize_expression_with_polyadenylation: Visualize RNA expression with custom polyadenylation site annotations
4. visualize_chromatin_accessibility: Visualize chromatin accessibility (DNASE, ATAC) with annotations
5. visualize_splicing_effects: Visualize splicing predictions with variant effects
6. visualize_histone_modifications: Visualize ChIP-Histone predictions with TSS annotations
7. visualize_tf_binding: Visualize transcription factor binding patterns
8. visualize_contact_maps: Visualize DNA-DNA contact frequency predictions

All tools were extracted from `alphagenome/colabs/visualization_modality_tour.ipynb`.
"""

# Define the MCP server and import required packages
from alphagenome import colab_utils
from alphagenome.data import gene_annotation, genome, track_data, transcript
from alphagenome.models import dna_client
from alphagenome.visualization import plot_components
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
from pathlib import Path
from fastmcp import FastMCP
from datetime import datetime
from typing import Annotated, Optional

# Define the INPUT_DIR and OUTPUT_DIR
# Project root is two levels up from this file (src/tools/visualization_modality_tour.py)
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
DEFAULT_INPUT_DIR = PROJECT_ROOT / "tmp_inputs" / "visualization_modality_tour"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "tmp_outputs" / "visualization_modality_tour"

INPUT_DIR = Path(os.environ.get("VISUALIZATION_MODALITY_TOUR_INPUT_DIR", DEFAULT_INPUT_DIR))
OUTPUT_DIR = Path(os.environ.get("VISUALIZATION_MODALITY_TOUR_OUTPUT_DIR", DEFAULT_OUTPUT_DIR))

# Mkdir if not exist
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Define the timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Define the MCP server
visualization_modality_tour_mcp = FastMCP(name="visualization_modality_tour")


@visualization_modality_tour_mcp.tool
def visualize_gene_expression(
    api_key: Annotated[str, "API key for AlphaGenome model"],
    chromosome: Annotated[str, "Chromosome (e.g., 'chr22')"] = "chr22",
    start: Annotated[int, "Start position"] = 36150498,
    end: Annotated[int, "End position"] = 36252898,
    ontology_terms: Annotated[list[str], "List of tissue/cell-type ontology terms"] = ["UBERON:0001159", "UBERON:0001155"],
    gtf_url: Annotated[str, "URL to GENCODE GTF annotation file"] = "https://storage.googleapis.com/alphagenome/reference/gencode/hg38/gencode.v46.annotation.gtf.gz.feather",
    out_prefix: Annotated[Optional[str], "Output file prefix (defaults to timestamp)"] = None,
) -> dict:
    """
    Visualize RNA expression (RNA_SEQ, CAGE) for specified tissues in a genomic interval.
    """
    if out_prefix is None:
        out_prefix = f"gene_expression_{timestamp}"
    
    # Initialize model
    dna_model = dna_client.create(api_key)
    
    # Load gene annotations
    gtf = pd.read_feather(gtf_url)
    gtf_transcript = gene_annotation.filter_transcript_support_level(
        gene_annotation.filter_protein_coding(gtf), ['1']
    )
    gtf_longest_transcript = gene_annotation.filter_to_longest_transcript(gtf_transcript)
    longest_transcript_extractor = transcript.TranscriptExtractor(gtf_longest_transcript)
    
    # Define interval
    interval = genome.Interval(chromosome, start, end).resize(dna_client.SEQUENCE_LENGTH_1MB)
    
    # Make predictions
    output = dna_model.predict_interval(
        interval=interval,
        requested_outputs={
            dna_client.OutputType.RNA_SEQ,
            dna_client.OutputType.CAGE,
        },
        ontology_terms=ontology_terms,
    )
    
    # Extract transcripts
    longest_transcripts = longest_transcript_extractor.extract(interval)
    
    # Build plot
    plot = plot_components.plot(
        [
            plot_components.TranscriptAnnotation(longest_transcripts),
            plot_components.Tracks(
                tdata=output.rna_seq,
                ylabel_template='RNA_SEQ: {biosample_name} ({strand})\n{name}',
            ),
            plot_components.Tracks(
                tdata=output.cage,
                ylabel_template='CAGE: {biosample_name} ({strand})\n{name}',
            ),
        ],
        interval=interval,
        title='Predicted RNA Expression (RNA_SEQ, CAGE) for colon tissue',
    )
    
    # Save figure
    fig_path = OUTPUT_DIR / f"{out_prefix}.png"
    plt.savefig(fig_path.resolve(), dpi=150, bbox_inches='tight')
    plt.close()
    
    return {
        "message": "Saved gene expression visualization",
        "artifacts": [
            {
                "description": "Gene expression visualization",
                "path": str(fig_path.resolve())
            }
        ]
    }


@visualization_modality_tour_mcp.tool
def visualize_variant_expression_effect(
    api_key: Annotated[str, "API key for AlphaGenome model"],
    variant_string: Annotated[str, "Variant string (e.g., 'chr22:36201698:A>C')"] = "chr22:36201698:A>C",
    chromosome: Annotated[str, "Chromosome"] = "chr22",
    start: Annotated[int, "Start position"] = 36150498,
    end: Annotated[int, "End position"] = 36252898,
    gene_symbol: Annotated[str, "Gene symbol to focus on"] = "APOL4",
    ontology_terms: Annotated[list[str], "Tissue/cell-type ontology terms"] = ["UBERON:0001159", "UBERON:0001155"],
    gtf_url: Annotated[str, "URL to GENCODE GTF annotation"] = "https://storage.googleapis.com/alphagenome/reference/gencode/hg38/gencode.v46.annotation.gtf.gz.feather",
    out_prefix: Annotated[Optional[str], "Output file prefix"] = None,
) -> dict:
    """
    Visualize the effect of a variant on gene expression using REF vs ALT predictions.
    """
    if out_prefix is None:
        out_prefix = f"variant_expression_effect_{timestamp}"
    
    # Initialize model
    dna_model = dna_client.create(api_key)
    
    # Load gene annotations
    gtf = pd.read_feather(gtf_url)
    gtf_transcript = gene_annotation.filter_transcript_support_level(
        gene_annotation.filter_protein_coding(gtf), ['1']
    )
    gtf_longest_transcript = gene_annotation.filter_to_longest_transcript(gtf_transcript)
    longest_transcript_extractor = transcript.TranscriptExtractor(gtf_longest_transcript)
    
    # Define interval and variant
    interval = genome.Interval(chromosome, start, end).resize(dna_client.SEQUENCE_LENGTH_1MB)
    variant = genome.Variant.from_str(variant_string)
    
    # Make predictions
    output = dna_model.predict_variant(
        interval=interval,
        variant=variant,
        requested_outputs={
            dna_client.OutputType.RNA_SEQ,
            dna_client.OutputType.CAGE,
        },
        ontology_terms=ontology_terms,
    )
    
    # Get gene interval
    apol4_interval = gene_annotation.get_gene_interval(gtf, gene_symbol=gene_symbol)
    apol4_interval.resize_inplace(apol4_interval.width + 1000)
    
    # Extract transcripts
    longest_transcripts = longest_transcript_extractor.extract(interval)
    
    # Define colors
    ref_alt_colors = {'REF': 'dimgrey', 'ALT': 'red'}
    
    # Build plot
    plot = plot_components.plot(
        [
            plot_components.TranscriptAnnotation(longest_transcripts),
            plot_components.OverlaidTracks(
                tdata={
                    'REF': output.reference.rna_seq.filter_to_nonpositive_strand(),
                    'ALT': output.alternate.rna_seq.filter_to_nonpositive_strand(),
                },
                colors=ref_alt_colors,
                ylabel_template='{biosample_name} ({strand})\n{name}',
            ),
            plot_components.OverlaidTracks(
                tdata={
                    'REF': output.reference.cage.filter_to_nonpositive_strand(),
                    'ALT': output.alternate.cage.filter_to_nonpositive_strand(),
                },
                colors=ref_alt_colors,
                ylabel_template='{biosample_name} ({strand})\n{name}',
            ),
        ],
        annotations=[plot_components.VariantAnnotation([variant])],
        interval=apol4_interval,
        title='Effect of variant on predicted RNA Expression in colon tissue',
    )
    
    # Save figure
    fig_path = OUTPUT_DIR / f"{out_prefix}.png"
    plt.savefig(fig_path.resolve(), dpi=150, bbox_inches='tight')
    plt.close()
    
    return {
        "message": "Saved variant expression effect visualization",
        "artifacts": [
            {
                "description": "Variant expression effect plot",
                "path": str(fig_path.resolve())
            }
        ]
    }


@visualization_modality_tour_mcp.tool
def visualize_chromatin_accessibility(
    api_key: Annotated[str, "API key for AlphaGenome model"],
    chromosome: Annotated[str, "Chromosome"] = "chr22",
    start: Annotated[int, "Start position"] = 36150498,
    end: Annotated[int, "End position"] = 36252898,
    variant_string: Annotated[str, "Variant string for annotation"] = "chr22:36201698:A>C",
    ontology_terms: Annotated[list[str], "Tissue ontology terms"] = ["UBERON:0000317", "UBERON:0001155", "UBERON:0001157", "UBERON:0001159", "UBERON:0004992", "UBERON:0008971"],
    gtf_url: Annotated[str, "URL to GENCODE GTF annotation"] = "https://storage.googleapis.com/alphagenome/reference/gencode/hg38/gencode.v46.annotation.gtf.gz.feather",
    out_prefix: Annotated[Optional[str], "Output file prefix"] = None,
) -> dict:
    """
    Visualize chromatin accessibility (DNASE, ATAC) with promoter annotations.
    """
    if out_prefix is None:
        out_prefix = f"chromatin_accessibility_{timestamp}"
    
    # Initialize model
    dna_model = dna_client.create(api_key)
    
    # Load gene annotations
    gtf = pd.read_feather(gtf_url)
    gtf_transcript = gene_annotation.filter_transcript_support_level(
        gene_annotation.filter_protein_coding(gtf), ['1']
    )
    gtf_longest_transcript = gene_annotation.filter_to_longest_transcript(gtf_transcript)
    longest_transcript_extractor = transcript.TranscriptExtractor(gtf_longest_transcript)
    
    # Define interval and variant
    interval = genome.Interval(chromosome, start, end).resize(dna_client.SEQUENCE_LENGTH_1MB)
    variant = genome.Variant.from_str(variant_string)
    
    # Make predictions
    output = dna_model.predict_interval(
        interval,
        requested_outputs={
            dna_client.OutputType.DNASE,
            dna_client.OutputType.ATAC,
        },
        ontology_terms=ontology_terms,
    )
    
    # Extract transcripts
    longest_transcripts = longest_transcript_extractor.extract(interval)
    
    # Define promoter intervals
    promoter_intervals = [
        genome.Interval('chr22', 36201799, 36202681, name='Ensembl_promoter:ENSR00001367790'),
        genome.Interval('chr22', 36204705, 36205330, name='Ensembl_promoter:ENSR00001367792'),
    ]
    
    # Build plot
    plot = plot_components.plot(
        [
            plot_components.TranscriptAnnotation(longest_transcripts),
            plot_components.Tracks(
                tdata=output.dnase,
                ylabel_template='DNASE: {biosample_name} ({strand})\n{name}',
            ),
            plot_components.Tracks(
                tdata=output.atac,
                ylabel_template='ATAC: {biosample_name} ({strand})\n{name}',
            ),
        ],
        interval=variant.reference_interval.resize(8000),
        annotations=[
            plot_components.VariantAnnotation([variant]),
            plot_components.IntervalAnnotation(promoter_intervals),
        ],
        title='Predicted chromatin accessibility (DNASE, ATAC) for colon tissue',
    )
    
    # Save figure
    fig_path = OUTPUT_DIR / f"{out_prefix}.png"
    plt.savefig(fig_path.resolve(), dpi=150, bbox_inches='tight')
    plt.close()
    
    return {
        "message": "Saved chromatin accessibility visualization",
        "artifacts": [
            {
                "description": "Chromatin accessibility plot",
                "path": str(fig_path.resolve())
            }
        ]
    }


@visualization_modality_tour_mcp.tool
def visualize_splicing_effects(
    api_key: Annotated[str, "API key for AlphaGenome model"],
    variant_string: Annotated[str, "Variant string"] = "chr22:36201698:A>C",
    chromosome: Annotated[str, "Chromosome"] = "chr22",
    start: Annotated[int, "Start position"] = 36150498,
    end: Annotated[int, "End position"] = 36252898,
    gene_symbol: Annotated[str, "Gene symbol"] = "APOL4",
    ontology_terms: Annotated[list[str], "Tissue ontology terms"] = ["UBERON:0001157", "UBERON:0001159"],
    gtf_url: Annotated[str, "URL to GENCODE GTF annotation"] = "https://storage.googleapis.com/alphagenome/reference/gencode/hg38/gencode.v46.annotation.gtf.gz.feather",
    out_prefix: Annotated[Optional[str], "Output file prefix"] = None,
) -> dict:
    """
    Visualize splicing predictions with variant effects using sashimi plots.
    """
    if out_prefix is None:
        out_prefix = f"splicing_effects_{timestamp}"
    
    # Initialize model
    dna_model = dna_client.create(api_key)
    
    # Load gene annotations
    gtf = pd.read_feather(gtf_url)
    gtf_transcript = gene_annotation.filter_transcript_support_level(
        gene_annotation.filter_protein_coding(gtf), ['1']
    )
    transcript_extractor = transcript.TranscriptExtractor(gtf_transcript)
    
    # Define interval and variant
    interval = genome.Interval(chromosome, start, end).resize(dna_client.SEQUENCE_LENGTH_1MB)
    variant = genome.Variant.from_str(variant_string)
    
    # Make predictions
    output = dna_model.predict_variant(
        interval=interval,
        variant=variant,
        requested_outputs={
            dna_client.OutputType.RNA_SEQ,
            dna_client.OutputType.SPLICE_SITES,
            dna_client.OutputType.SPLICE_SITE_USAGE,
            dna_client.OutputType.SPLICE_JUNCTIONS,
        },
        ontology_terms=ontology_terms,
    )
    
    # Get gene interval
    apol4_interval = gene_annotation.get_gene_interval(gtf, gene_symbol=gene_symbol)
    apol4_interval.resize_inplace(apol4_interval.width + 1000)
    
    # Extract all transcripts
    transcripts = transcript_extractor.extract(interval)
    
    ref_output = output.reference
    alt_output = output.alternate
    ref_alt_colors = {'REF': 'dimgrey', 'ALT': 'red'}
    
    # Build plot
    plot = plot_components.plot(
        [
            plot_components.TranscriptAnnotation(transcripts),
            plot_components.Sashimi(
                ref_output.splice_junctions
                .filter_to_strand('-')
                .filter_by_tissue('Colon_Transverse'),
                ylabel_template='Reference {biosample_name} ({strand})\n{name}',
            ),
            plot_components.Sashimi(
                alt_output.splice_junctions
                .filter_to_strand('-')
                .filter_by_tissue('Colon_Transverse'),
                ylabel_template='Alternate {biosample_name} ({strand})\n{name}',
            ),
            plot_components.OverlaidTracks(
                tdata={
                    'REF': ref_output.rna_seq.filter_to_nonpositive_strand(),
                    'ALT': alt_output.rna_seq.filter_to_nonpositive_strand(),
                },
                colors=ref_alt_colors,
                ylabel_template='RNA_SEQ: {biosample_name} ({strand})\n{name}',
            ),
            plot_components.OverlaidTracks(
                tdata={
                    'REF': ref_output.splice_sites.filter_to_nonpositive_strand(),
                    'ALT': alt_output.splice_sites.filter_to_nonpositive_strand(),
                },
                colors=ref_alt_colors,
                ylabel_template='SPLICE SITES: {name} ({strand})',
            ),
            plot_components.OverlaidTracks(
                tdata={
                    'REF': ref_output.splice_site_usage.filter_to_nonpositive_strand(),
                    'ALT': alt_output.splice_site_usage.filter_to_nonpositive_strand(),
                },
                colors=ref_alt_colors,
                ylabel_template='SPLICE SITE USAGE: {biosample_name} ({strand})\n{name}',
            ),
        ],
        interval=apol4_interval,
        annotations=[plot_components.VariantAnnotation([variant])],
        title='Predicted REF vs. ALT effects of variant in colon tissue',
    )
    
    # Save figure
    fig_path = OUTPUT_DIR / f"{out_prefix}.png"
    plt.savefig(fig_path.resolve(), dpi=150, bbox_inches='tight')
    plt.close()
    
    return {
        "message": "Saved splicing effects visualization",
        "artifacts": [
            {
                "description": "Splicing effects plot",
                "path": str(fig_path.resolve())
            }
        ]
    }


@visualization_modality_tour_mcp.tool
def visualize_histone_modifications(
    api_key: Annotated[str, "API key for AlphaGenome model"],
    chromosome: Annotated[str, "Chromosome"] = "chr22",
    start: Annotated[int, "Start position"] = 36150498,
    end: Annotated[int, "End position"] = 36252898,
    ontology_terms: Annotated[list[str], "Tissue ontology terms"] = ["UBERON:0000317", "UBERON:0001155", "UBERON:0001157", "UBERON:0001159"],
    gtf_url: Annotated[str, "URL to GENCODE GTF annotation"] = "https://storage.googleapis.com/alphagenome/reference/gencode/hg38/gencode.v46.annotation.gtf.gz.feather",
    out_prefix: Annotated[Optional[str], "Output file prefix"] = None,
) -> dict:
    """
    Visualize ChIP-Histone predictions with TSS annotations and histone-specific colors.
    """
    if out_prefix is None:
        out_prefix = f"histone_modifications_{timestamp}"
    
    # Initialize model
    dna_model = dna_client.create(api_key)
    
    # Load gene annotations
    gtf = pd.read_feather(gtf_url)
    gtf_transcript = gene_annotation.filter_transcript_support_level(
        gene_annotation.filter_protein_coding(gtf), ['1']
    )
    gtf_longest_transcript = gene_annotation.filter_to_longest_transcript(gtf_transcript)
    longest_transcript_extractor = transcript.TranscriptExtractor(gtf_longest_transcript)
    
    # Define interval
    interval = genome.Interval(chromosome, start, end).resize(dna_client.SEQUENCE_LENGTH_1MB)
    
    # Make predictions
    output = dna_model.predict_interval(
        interval=interval,
        requested_outputs={dna_client.OutputType.CHIP_HISTONE},
        ontology_terms=ontology_terms,
    )
    
    # Extract transcripts and TSS
    longest_transcripts = longest_transcript_extractor.extract(interval)
    gtf_tss = gene_annotation.extract_tss(gtf_longest_transcript)
    
    tss_as_intervals = [
        genome.Interval(
            chromosome=row.Chromosome,
            start=row.Start,
            end=row.End + 1000,
            name=row.gene_name,
        )
        for _, row in gtf_tss.iterrows()
    ]
    
    # Reorder tracks by histone mark
    reordered_chip_histone = output.chip_histone.select_tracks_by_index(
        output.chip_histone.metadata.sort_values('histone_mark').index
    )
    
    # Define histone colors
    histone_to_color = {
        'H3K27AC': '#e41a1c',
        'H3K36ME3': '#ff7f00',
        'H3K4ME1': '#377eb8',
        'H3K4ME3': '#984ea3',
        'H3K9AC': '#4daf4a',
        'H3K27ME3': '#ffc0cb',
    }
    
    track_colors = (
        reordered_chip_histone.metadata['histone_mark']
        .map(lambda x: histone_to_color.get(x.upper(), '#000000'))
        .values
    )
    
    # Build plot
    plot = plot_components.plot(
        [
            plot_components.TranscriptAnnotation(longest_transcripts),
            plot_components.Tracks(
                tdata=reordered_chip_histone,
                ylabel_template='CHIP HISTONE: {biosample_name} ({strand})\n{histone_mark}',
                filled=True,
                track_colors=track_colors,
            ),
        ],
        interval=interval,
        annotations=[
            plot_components.IntervalAnnotation(tss_as_intervals, alpha=0.5, colors='blue')
        ],
        despine_keep_bottom=True,
        title='Predicted histone modification markers in colon tissue',
    )
    
    # Save figure
    fig_path = OUTPUT_DIR / f"{out_prefix}.png"
    plt.savefig(fig_path.resolve(), dpi=150, bbox_inches='tight')
    plt.close()
    
    return {
        "message": "Saved histone modifications visualization",
        "artifacts": [
            {
                "description": "Histone modifications plot",
                "path": str(fig_path.resolve())
            }
        ]
    }


@visualization_modality_tour_mcp.tool
def visualize_tf_binding(
    api_key: Annotated[str, "API key for AlphaGenome model"],
    chromosome: Annotated[str, "Chromosome"] = "chr22",
    start: Annotated[int, "Start position"] = 36150498,
    end: Annotated[int, "End position"] = 36252898,
    gene_symbol: Annotated[str, "Gene symbol to focus on"] = "APOL4",
    ontology_terms: Annotated[list[str], "Cell-type ontology terms"] = ["UBERON:0001159", "UBERON:0001157", "EFO:0002067", "EFO:0001187"],
    min_peak_value: Annotated[int, "Minimum peak value for TF binding"] = 8000,
    gtf_url: Annotated[str, "URL to GENCODE GTF annotation"] = "https://storage.googleapis.com/alphagenome/reference/gencode/hg38/gencode.v46.annotation.gtf.gz.feather",
    out_prefix: Annotated[Optional[str], "Output file prefix"] = None,
) -> dict:
    """
    Visualize transcription factor binding patterns with promoter annotations.
    """
    if out_prefix is None:
        out_prefix = f"tf_binding_{timestamp}"
    
    # Initialize model
    dna_model = dna_client.create(api_key)
    
    # Load gene annotations
    gtf = pd.read_feather(gtf_url)
    gtf_transcript = gene_annotation.filter_transcript_support_level(
        gene_annotation.filter_protein_coding(gtf), ['1']
    )
    gtf_longest_transcript = gene_annotation.filter_to_longest_transcript(gtf_transcript)
    longest_transcript_extractor = transcript.TranscriptExtractor(gtf_longest_transcript)
    transcript_extractor = transcript.TranscriptExtractor(gtf_transcript)
    
    # Define interval
    interval = genome.Interval(chromosome, start, end).resize(dna_client.SEQUENCE_LENGTH_1MB)
    
    # Make predictions
    output = dna_model.predict_interval(
        interval=interval,
        requested_outputs={dna_client.OutputType.CHIP_TF},
        ontology_terms=ontology_terms,
    )
    
    # Get gene interval
    apol4_interval = gene_annotation.get_gene_interval(gtf, gene_symbol=gene_symbol)
    apol4_interval.resize_inplace(apol4_interval.width + 1000)
    
    # Extract transcripts
    transcripts = transcript_extractor.extract(interval)
    
    # Filter to high-value tracks in the gene interval
    max_predictions = output.chip_tf.slice_by_interval(
        apol4_interval, match_resolution=True
    ).values.max(axis=0)
    
    # Filter to the 10 tracks with the highest predictions
    output_filtered = output.chip_tf.filter_tracks(
        (max_predictions >= np.sort(max_predictions)[-10])
    )
    
    # Define promoter intervals
    promoter_intervals = [
        genome.Interval('chr22', 36201799, 36202681, name='Ensembl_promoter:ENSR00001367790'),
        genome.Interval('chr22', 36204705, 36205330, name='Ensembl_promoter:ENSR00001367792'),
    ]
    
    # Build first plot - top TF binding sites
    plot1 = plot_components.plot(
        [
            plot_components.TranscriptAnnotation(transcripts),
            plot_components.Tracks(
                tdata=output_filtered,
                ylabel_template='CHIP TF: {biosample_name} ({strand})\n{transcription_factor}',
                filled=True,
            ),
        ],
        interval=apol4_interval,
        annotations=[plot_components.IntervalAnnotation(promoter_intervals)],
        despine_keep_bottom=True,
        title='Predicted TF-binding in K562, HepG2, and sigmoid colon.',
    )
    
    # Save first figure
    fig1_path = OUTPUT_DIR / f"{out_prefix}_top_tfs.png"
    plt.savefig(fig1_path.resolve(), dpi=150, bbox_inches='tight')
    plt.close()
    
    # Create mean CTCF plot
    mean_ctcf = output_filtered.values[
        :, output_filtered.metadata['transcription_factor'] == 'CTCF'
    ].mean(axis=1)
    
    tdata_mean_ctcf = track_data.TrackData(
        values=mean_ctcf[:, None],
        metadata=pd.DataFrame(
            {'transcription_factor': ['CTCF'], 'name': ['mean'], 'strand': ['.']}
        ),
        interval=output_filtered.interval,
        resolution=output_filtered.resolution,
    )
    
    # Build second plot - mean CTCF
    plot2 = plot_components.plot(
        [
            plot_components.TranscriptAnnotation(transcripts),
            plot_components.Tracks(
                tdata=tdata_mean_ctcf,
                ylabel_template='{name} {transcription_factor}',
                filled=True,
            ),
        ],
        interval=apol4_interval,
        annotations=[plot_components.IntervalAnnotation(promoter_intervals)],
        despine_keep_bottom=True,
        title='Predicted CTCF binding (mean across cell types)',
    )
    
    # Save second figure
    fig2_path = OUTPUT_DIR / f"{out_prefix}_mean_ctcf.png"
    plt.savefig(fig2_path.resolve(), dpi=150, bbox_inches='tight')
    plt.close()
    
    return {
        "message": "Saved 2 TF binding visualizations",
        "artifacts": [
            {
                "description": "Top TF binding sites plot",
                "path": str(fig1_path.resolve())
            },
            {
                "description": "Mean CTCF binding plot",
                "path": str(fig2_path.resolve())
            }
        ]
    }


@visualization_modality_tour_mcp.tool
def visualize_expression_with_polyadenylation(
    api_key: Annotated[str, "API key for AlphaGenome model"],
    chromosome: Annotated[str, "Chromosome"] = "chr22",
    start: Annotated[int, "Start position"] = 36150498,
    end: Annotated[int, "End position"] = 36252898,
    ontology_terms: Annotated[list[str], "Tissue ontology terms"] = ["UBERON:0001159", "UBERON:0002048"],
    gtf_url: Annotated[str, "URL to GENCODE GTF annotation"] = "https://storage.googleapis.com/alphagenome/reference/gencode/hg38/gencode.v46.annotation.gtf.gz.feather",
    out_prefix: Annotated[Optional[str], "Output file prefix"] = None,
) -> dict:
    """
    Visualize RNA expression with custom polyadenylation site annotations for APOL4.
    """
    if out_prefix is None:
        out_prefix = f"expression_polyadenylation_{timestamp}"
    
    # Initialize model
    dna_model = dna_client.create(api_key)
    
    # Load gene annotations
    gtf = pd.read_feather(gtf_url)
    gtf_transcript = gene_annotation.filter_transcript_support_level(
        gene_annotation.filter_protein_coding(gtf), ['1']
    )
    gtf_longest_transcript = gene_annotation.filter_to_longest_transcript(gtf_transcript)
    longest_transcript_extractor = transcript.TranscriptExtractor(gtf_longest_transcript)
    
    # Define interval
    interval = genome.Interval(chromosome, start, end).resize(dna_client.SEQUENCE_LENGTH_1MB)
    
    # Make predictions
    output = dna_model.predict_interval(
        interval=interval,
        requested_outputs={
            dna_client.OutputType.RNA_SEQ,
        },
        ontology_terms=ontology_terms,
    )
    
    # Extract transcripts
    longest_transcripts = longest_transcript_extractor.extract(interval)
    
    # Define pA sites in hg38 coordinates
    apol4_pAs = [
        genome.Interval('chr22', 36189128, 36189129, '-'),
        genome.Interval('chr22', 36190089, 36190090, '-'),
        genome.Interval('chr22', 36190144, 36190145, '-')
    ]
    
    # Define plotting interval
    offset = 200
    pA_interval = genome.Interval(
        'chr22',
        36189128 - offset,
        36190145 + offset,
        '-'
    )
    
    # Define intervals annotation
    pA_labels = ['pA_3', 'pA_2', 'pA_1']
    
    # Build plot
    plot = plot_components.plot(
        [
            plot_components.TranscriptAnnotation(longest_transcripts),
            plot_components.Tracks(
                tdata=output.rna_seq.filter_to_negative_strand(),
                ylabel_template='RNA_SEQ: {biosample_name} ({strand})\n{name}',
                shared_y_scale=True,
            )
        ],
        annotations=[
            plot_components.IntervalAnnotation(
                apol4_pAs,
                alpha=1,
                labels=pA_labels,
                label_angle=90
            )
        ],
        interval=pA_interval,
        title='APOL4 polyadenylation sites annotation',
    )
    
    # Save figure
    fig_path = OUTPUT_DIR / f"{out_prefix}.png"
    plt.savefig(fig_path.resolve(), dpi=150, bbox_inches='tight')
    plt.close()
    
    return {
        "message": "Saved expression with polyadenylation sites visualization",
        "artifacts": [
            {
                "description": "Expression with pA sites plot",
                "path": str(fig_path.resolve())
            }
        ]
    }


@visualization_modality_tour_mcp.tool
def visualize_contact_maps(
    api_key: Annotated[str, "API key for AlphaGenome model"],
    chromosome: Annotated[str, "Chromosome"] = "chr22",
    start: Annotated[int, "Start position"] = 36150498,
    end: Annotated[int, "End position"] = 36252898,
    ontology_terms: Annotated[list[str], "Cell-type ontology terms"] = ["EFO:0002824"],
    gtf_url: Annotated[str, "URL to GENCODE GTF annotation"] = "https://storage.googleapis.com/alphagenome/reference/gencode/hg38/gencode.v46.annotation.gtf.gz.feather",
    out_prefix: Annotated[Optional[str], "Output file prefix"] = None,
) -> dict:
    """
    Visualize DNA-DNA contact frequency predictions as contact maps.
    """
    if out_prefix is None:
        out_prefix = f"contact_maps_{timestamp}"
    
    # Initialize model
    dna_model = dna_client.create(api_key)
    
    # Load gene annotations
    gtf = pd.read_feather(gtf_url)
    gtf_transcript = gene_annotation.filter_transcript_support_level(
        gene_annotation.filter_protein_coding(gtf), ['1']
    )
    gtf_longest_transcript = gene_annotation.filter_to_longest_transcript(gtf_transcript)
    longest_transcript_extractor = transcript.TranscriptExtractor(gtf_longest_transcript)
    
    # Define interval
    interval = genome.Interval(chromosome, start, end).resize(dna_client.SEQUENCE_LENGTH_1MB)
    
    # Make predictions
    output = dna_model.predict_interval(
        interval=interval,
        requested_outputs={dna_client.OutputType.CONTACT_MAPS},
        ontology_terms=ontology_terms,
    )
    
    # Extract transcripts
    longest_transcripts = longest_transcript_extractor.extract(interval)
    
    # Build plot
    plot = plot_components.plot(
        [
            plot_components.TranscriptAnnotation(longest_transcripts),
            plot_components.ContactMaps(
                tdata=output.contact_maps,
                ylabel_template='{biosample_name}\n{name}',
                cmap='autumn_r',
                vmax=1.0,
            ),
        ],
        interval=interval,
        title='Predicted contact maps',
    )
    
    # Save figure
    fig_path = OUTPUT_DIR / f"{out_prefix}.png"
    plt.savefig(fig_path.resolve(), dpi=150, bbox_inches='tight')
    plt.close()
    
    return {
        "message": "Saved contact maps visualization",
        "artifacts": [
            {
                "description": "Contact maps plot",
                "path": str(fig_path.resolve())
            }
        ]
    }