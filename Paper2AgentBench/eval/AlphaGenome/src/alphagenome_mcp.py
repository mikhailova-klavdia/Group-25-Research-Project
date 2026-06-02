"""
Model Context Protocol (MCP) for AlphaGenome

AlphaGenome is a suite of foundation models for genomics and variant prediction that enable high-resolution and cell-type-specific prediction of molecular and cellular phenotypes across the genome.
This platform provides comprehensive tools for variant scoring, genomic visualization, and functional genomics analysis.
It integrates multiple modalities including gene expression, chromatin accessibility, transcription factor binding, and chromatin organization.

This MCP Server contains the tools extracted from the following tutorials with their tools:
1. quick_start
    - predict_dna_sequence: Predict outputs for a DNA sequence
    - predict_genome_interval: Predict outputs for a genomic interval with visualization
    - predict_variant_effects: Predict variant effects with visualization
    - score_genetic_variant: Score the effect of a genetic variant
    - perform_ism_analysis: Perform in silico mutagenesis analysis with visualization
    - predict_mouse_sequences: Make predictions for mouse DNA sequences
2. essential_commands
    - create_genomic_interval: Create and manipulate a genomic interval with basic properties
    - resize_interval: Resize a genomic interval around its center point
    - compare_intervals: Compare two intervals for overlap, containment, and intersection
    - create_genomic_variant: Create genetic variants including SNPs and indels
    - variant_interval_overlap: Check variant-interval overlap for reference and alternate alleles
    - create_track_data: Create TrackData objects from values and metadata
    - change_track_resolution: Convert track data between different resolutions
    - filter_tracks_by_strand: Filter tracks by DNA strand orientation
    - slice_track_data: Slice track data by position or genomic interval
    - select_tracks: Select and reorder specific tracks by name
    - reverse_complement_tracks: Reverse complement track values in a strand-aware manner
3. tissue_ontology_mapping
    - get_output_metadata: Retrieve and explore output metadata for a given organism
    - count_tracks_by_output_type: Count the number of tracks per output type for human and mouse
4. visualization_modality_tour
    - visualize_gene_expression: Visualize RNA expression (RNA_SEQ, CAGE) for specified tissues
    - visualize_variant_expression_effect: Visualize the effect of a variant on gene expression
    - visualize_expression_with_polyadenylation: Visualize RNA expression with custom polyadenylation site annotations
    - visualize_chromatin_accessibility: Visualize chromatin accessibility (DNASE, ATAC) with annotations
    - visualize_splicing_effects: Visualize splicing predictions with variant effects
    - visualize_histone_modifications: Visualize ChIP-Histone predictions with TSS annotations
    - visualize_tf_binding: Visualize transcription factor binding patterns
    - visualize_contact_maps: Visualize DNA-DNA contact frequency predictions
5. variant_scoring_ui
    - score_single_variant: Score a single variant across different modalities and tissues
    - visualize_variant_effects: Visualize variant effects with gene annotations and various tracks
6. batch_variant_scoring
    - score_batch_variants: Score multiple genetic variants across multiple regulatory modalities
7. example_analysis_workflow
    - visualize_variant_positions: Visualize genomic context and positions of variants near a gene
    - predict_variant_effects: Predict functional impact of a variant on gene expression, accessibility and histone marks
    - compare_variant_effects: Compare predicted effects of disease variants versus background variants
    - analyze_tal1_variants: Complete TAL1 variant analysis workflow with oncogenic and background variants
"""

import sys
from pathlib import Path
from fastmcp import FastMCP

# Import the MCP tools from the tools folder
from tools.batch_variant_scoring import batch_variant_scoring_mcp
from tools.essential_commands import essential_commands_mcp
from tools.example_analysis_workflow import example_analysis_workflow_mcp
from tools.quick_start import quick_start_mcp
from tools.tissue_ontology_mapping import tissue_ontology_mapping_mcp
from tools.variant_scoring_ui import variant_scoring_ui_mcp
from tools.visualization_modality_tour import visualization_modality_tour_mcp

# Define the MCP server
mcp = FastMCP(name = "alphagenome")

# Mount the tools
mcp.mount(batch_variant_scoring_mcp)
mcp.mount(essential_commands_mcp)
mcp.mount(example_analysis_workflow_mcp)
mcp.mount(quick_start_mcp)
mcp.mount(tissue_ontology_mapping_mcp)
mcp.mount(variant_scoring_ui_mcp)
mcp.mount(visualization_modality_tour_mcp)

# Run the MCP server
if __name__ == "__main__":
  mcp.run(transport="http", host="127.0.0.1", port=8003)