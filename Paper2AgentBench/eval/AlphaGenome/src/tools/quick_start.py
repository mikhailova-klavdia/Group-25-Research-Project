"""
Quick start tutorial tools for AlphaGenome predictions and variant scoring.

This MCP Server provides 6 tools:
1. predict_dna_sequence: Predict outputs for a DNA sequence
2. predict_genome_interval: Predict outputs for a genomic interval with visualization
3. predict_variant_effects: Predict variant effects with visualization
4. score_genetic_variant: Score the effect of a genetic variant
5. perform_ism_analysis: Perform in silico mutagenesis analysis with visualization
6. predict_mouse_sequences: Make predictions for mouse DNA sequences

All tools were extracted from `alphagenome/colabs/quick_start.ipynb`.
"""

# Define the MCP server and import required packages
from alphagenome.data import gene_annotation
from alphagenome.data import genome
from alphagenome.data import transcript as transcript_utils
from alphagenome.interpretation import ism
from alphagenome.models import dna_client
from alphagenome.models import variant_scorers
from alphagenome.visualization import plot_components
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
from pathlib import Path
from fastmcp import FastMCP
from datetime import datetime
from typing import Annotated, Optional, List, Dict, Any

# Define the INPUT_DIR and OUTPUT_DIR
# Project root is two levels up from this file (src/tools/quick_start.py)
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
DEFAULT_INPUT_DIR = PROJECT_ROOT / "tmp_inputs" / "quick_start"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "tmp_outputs" / "quick_start"

INPUT_DIR = Path(os.environ.get("QUICK_START_INPUT_DIR", DEFAULT_INPUT_DIR))
OUTPUT_DIR = Path(os.environ.get("QUICK_START_OUTPUT_DIR", DEFAULT_OUTPUT_DIR))

# Mkdir if not exist
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Define the timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Define the MCP server
quick_start_mcp = FastMCP(name="quick_start")

# Public tools blocks that are used in the tutorial and will be exposed to the user
@quick_start_mcp.tool
def predict_dna_sequence(
    api_key: Annotated[str, "API key for AlphaGenome model"],
    sequence: Annotated[str, "DNA sequence (if shorter than target length, will be padded with N)"],
    requested_outputs: Annotated[List[str], "Output types to predict (e.g., ['DNASE', 'CAGE', 'RNA_SEQ'])"],
    ontology_terms: Annotated[List[str], "Ontology terms for tissues/cell types (e.g., ['UBERON:0002048'])"],
    sequence_length: Annotated[int, "Target sequence length for padding"] = 2048,
    out_prefix: Annotated[str, "Output file prefix"] = f"dna_sequence_{timestamp}",
) -> Dict[str, Any]:
    """
    Predict outputs for a DNA sequence using AlphaGenome model.
    """
    # Create DNA model
    dna_model = dna_client.create(api_key)
    
    # Pad sequence to target length
    padded_sequence = sequence.center(sequence_length, 'N')
    
    # Convert string output types to enum
    output_enums = []
    for output_type in requested_outputs:
        output_enums.append(getattr(dna_client.OutputType, output_type))
    
    # Make predictions
    output = dna_model.predict_sequence(
        sequence=padded_sequence,
        requested_outputs=output_enums,
        ontology_terms=ontology_terms,
    )
    
    # Save results to CSV files
    artifacts = []
    for output_type in requested_outputs:
        output_data = getattr(output, output_type.lower())
        
        # Save predictions
        predictions_file = OUTPUT_DIR / f"{out_prefix}_{output_type.lower()}_predictions.csv"
        predictions_df = pd.DataFrame(output_data.values)
        predictions_df.to_csv(predictions_file, index=False)
        artifacts.append({
            "description": f"{output_type} predictions",
            "path": str(predictions_file.resolve())
        })
        
        # Save metadata
        metadata_file = OUTPUT_DIR / f"{out_prefix}_{output_type.lower()}_metadata.csv"
        output_data.metadata.to_csv(metadata_file, index=False)
        artifacts.append({
            "description": f"{output_type} metadata",
            "path": str(metadata_file.resolve())
        })
    
    return {
        "message": f"Predicted {len(requested_outputs)} output types for DNA sequence",
        "artifacts": artifacts
    }


@quick_start_mcp.tool
def predict_genome_interval(
    api_key: Annotated[str, "API key for AlphaGenome model"],
    chromosome: Annotated[str, "Chromosome (e.g., 'chr19')"],
    start: Annotated[int, "Start position"],
    end: Annotated[int, "End position"],
    requested_outputs: Annotated[List[str], "Output types to predict (e.g., ['RNA_SEQ'])"],
    ontology_terms: Annotated[List[str], "Ontology terms for tissues/cell types"],
    sequence_length: Annotated[str, "Model sequence length (e.g., '1MB', '500KB', '100KB', '16KB', '2KB')"] = "1MB",
    gtf_url: Annotated[str, "URL to GTF file for gene annotations"] = "https://storage.googleapis.com/alphagenome/reference/gencode/hg38/gencode.v46.annotation.gtf.gz.feather",
    gene_symbol: Annotated[Optional[str], "Gene symbol to center interval on"] = None,
    strand: Annotated[str, "DNA strand ('+', '-', or '.')"] = ".",
    out_prefix: Annotated[str, "Output file prefix"] = f"genome_interval_{timestamp}",
) -> Dict[str, Any]:
    """
    Predict outputs for a genomic interval and visualize with gene annotations.
    """
    # Create DNA model
    dna_model = dna_client.create(api_key)
    
    # Load GTF file for gene annotations
    gtf = pd.read_feather(gtf_url)
    gtf_transcripts = gene_annotation.filter_protein_coding(gtf)
    gtf_transcripts = gene_annotation.filter_to_longest_transcript(gtf_transcripts)
    transcript_extractor = transcript_utils.TranscriptExtractor(gtf_transcripts)
    
    # Create interval
    if gene_symbol:
        interval = gene_annotation.get_gene_interval(gtf, gene_symbol=gene_symbol)
    else:
        interval = genome.Interval(chromosome=chromosome, start=start, end=end, strand=strand)
    
    # Resize to model-compatible length
    sequence_length_map = {
        '2KB': dna_client.SEQUENCE_LENGTH_2KB,
        '16KB': dna_client.SEQUENCE_LENGTH_16KB,
        '100KB': dna_client.SEQUENCE_LENGTH_100KB,
        '500KB': dna_client.SEQUENCE_LENGTH_500KB,
        '1MB': dna_client.SEQUENCE_LENGTH_1MB,
    }
    interval = interval.resize(sequence_length_map[sequence_length])
    
    # Convert string output types to enum
    output_enums = []
    for output_type in requested_outputs:
        output_enums.append(getattr(dna_client.OutputType, output_type))
    
    # Make predictions
    output = dna_model.predict_interval(
        interval=interval,
        requested_outputs=output_enums,
        ontology_terms=ontology_terms,
    )
    
    # Extract transcripts for visualization
    longest_transcripts = transcript_extractor.extract(interval)
    
    # Create visualizations and save data
    artifacts = []
    
    for output_type in requested_outputs:
        output_data = getattr(output, output_type.lower())
        
        # Save predictions
        predictions_file = OUTPUT_DIR / f"{out_prefix}_{output_type.lower()}_predictions.csv"
        predictions_df = pd.DataFrame(output_data.values)
        predictions_df.to_csv(predictions_file, index=False)
        artifacts.append({
            "description": f"{output_type} predictions",
            "path": str(predictions_file.resolve())
        })
        
        # Save metadata
        metadata_file = OUTPUT_DIR / f"{out_prefix}_{output_type.lower()}_metadata.csv"
        output_data.metadata.to_csv(metadata_file, index=False)
        artifacts.append({
            "description": f"{output_type} metadata",
            "path": str(metadata_file.resolve())
        })
        
        # Create full interval visualization
        plt.figure(figsize=(12, 6))
        plot_components.plot(
            components=[
                plot_components.TranscriptAnnotation(longest_transcripts),
                plot_components.Tracks(output_data),
            ],
            interval=output_data.interval,
        )
        full_plot_file = OUTPUT_DIR / f"{out_prefix}_{output_type.lower()}_full.png"
        plt.savefig(full_plot_file, dpi=150, bbox_inches='tight')
        plt.close()
        artifacts.append({
            "description": f"{output_type} full interval visualization",
            "path": str(full_plot_file.resolve())
        })
        
        # Create zoomed visualization
        plt.figure(figsize=(12, 6))
        plot_components.plot(
            components=[
                plot_components.TranscriptAnnotation(longest_transcripts, fig_height=0.1),
                plot_components.Tracks(output_data),
            ],
            interval=output_data.interval.resize(2**15),
        )
        zoom_plot_file = OUTPUT_DIR / f"{out_prefix}_{output_type.lower()}_zoom.png"
        plt.savefig(zoom_plot_file, dpi=150, bbox_inches='tight')
        plt.close()
        artifacts.append({
            "description": f"{output_type} zoomed visualization",
            "path": str(zoom_plot_file.resolve())
        })
    
    return {
        "message": f"Predicted {len(requested_outputs)} output types for genomic interval",
        "artifacts": artifacts
    }


@quick_start_mcp.tool
def predict_variant_effects(
    api_key: Annotated[str, "API key for AlphaGenome model"],
    chromosome: Annotated[str, "Chromosome (e.g., 'chr22')"],
    position: Annotated[int, "Variant position"],
    reference_bases: Annotated[str, "Reference allele"],
    alternate_bases: Annotated[str, "Alternative allele"],
    requested_outputs: Annotated[List[str], "Output types to predict (e.g., ['RNA_SEQ'])"],
    ontology_terms: Annotated[List[str], "Ontology terms for tissues/cell types"],
    sequence_length: Annotated[str, "Model sequence length"] = "1MB",
    gtf_url: Annotated[str, "URL to GTF file"] = "https://storage.googleapis.com/alphagenome/reference/gencode/hg38/gencode.v46.annotation.gtf.gz.feather",
    zoom_window: Annotated[int, "Window size for zoomed visualization"] = 32768,
    out_prefix: Annotated[str, "Output file prefix"] = f"variant_effects_{timestamp}",
) -> Dict[str, Any]:
    """
    Predict variant effects and visualize REF vs ALT allele predictions.
    """
    # Create DNA model
    dna_model = dna_client.create(api_key)
    
    # Load GTF file for gene annotations
    gtf = pd.read_feather(gtf_url)
    gtf_transcripts = gene_annotation.filter_protein_coding(gtf)
    gtf_transcripts = gene_annotation.filter_to_longest_transcript(gtf_transcripts)
    transcript_extractor = transcript_utils.TranscriptExtractor(gtf_transcripts)
    
    # Create variant
    variant = genome.Variant(
        chromosome=chromosome,
        position=position,
        reference_bases=reference_bases,
        alternate_bases=alternate_bases,
    )
    
    # Get interval
    sequence_length_map = {
        '2KB': dna_client.SEQUENCE_LENGTH_2KB,
        '16KB': dna_client.SEQUENCE_LENGTH_16KB,
        '100KB': dna_client.SEQUENCE_LENGTH_100KB,
        '500KB': dna_client.SEQUENCE_LENGTH_500KB,
        '1MB': dna_client.SEQUENCE_LENGTH_1MB,
    }
    interval = variant.reference_interval.resize(sequence_length_map[sequence_length])
    
    # Convert string output types to enum
    output_enums = []
    for output_type in requested_outputs:
        output_enums.append(getattr(dna_client.OutputType, output_type))
    
    # Predict variant effects
    variant_output = dna_model.predict_variant(
        interval=interval,
        variant=variant,
        requested_outputs=output_enums,
        ontology_terms=ontology_terms,
    )
    
    # Extract transcripts
    longest_transcripts = transcript_extractor.extract(interval)
    
    # Create visualizations and save data
    artifacts = []
    
    # Save variant info
    variant_info_file = OUTPUT_DIR / f"{out_prefix}_variant_info.csv"
    variant_df = pd.DataFrame([{
        'chromosome': chromosome,
        'position': position,
        'reference': reference_bases,
        'alternate': alternate_bases,
        'variant_id': str(variant)
    }])
    variant_df.to_csv(variant_info_file, index=False)
    artifacts.append({
        "description": "Variant information",
        "path": str(variant_info_file.resolve())
    })
    
    for output_type in requested_outputs:
        output_type_lower = output_type.lower()
        ref_data = getattr(variant_output.reference, output_type_lower)
        alt_data = getattr(variant_output.alternate, output_type_lower)
        
        # Save REF predictions
        ref_file = OUTPUT_DIR / f"{out_prefix}_{output_type_lower}_ref.csv"
        ref_df = pd.DataFrame(ref_data.values)
        ref_df.to_csv(ref_file, index=False)
        artifacts.append({
            "description": f"{output_type} REF predictions",
            "path": str(ref_file.resolve())
        })
        
        # Save ALT predictions
        alt_file = OUTPUT_DIR / f"{out_prefix}_{output_type_lower}_alt.csv"
        alt_df = pd.DataFrame(alt_data.values)
        alt_df.to_csv(alt_file, index=False)
        artifacts.append({
            "description": f"{output_type} ALT predictions",
            "path": str(alt_file.resolve())
        })
        
        # Create comparison visualization
        plt.figure(figsize=(14, 8))
        plot_components.plot(
            [
                plot_components.TranscriptAnnotation(longest_transcripts),
                plot_components.OverlaidTracks(
                    tdata={
                        'REF': ref_data,
                        'ALT': alt_data,
                    },
                    colors={'REF': 'dimgrey', 'ALT': 'red'},
                ),
            ],
            interval=ref_data.interval.resize(zoom_window),
            annotations=[plot_components.VariantAnnotation([variant], alpha=0.8)],
        )
        plot_file = OUTPUT_DIR / f"{out_prefix}_{output_type_lower}_comparison.png"
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()
        artifacts.append({
            "description": f"{output_type} REF vs ALT comparison",
            "path": str(plot_file.resolve())
        })
    
    return {
        "message": f"Predicted variant effects for {len(requested_outputs)} output types",
        "artifacts": artifacts
    }


@quick_start_mcp.tool
def score_genetic_variant(
    api_key: Annotated[str, "API key for AlphaGenome model"],
    chromosome: Annotated[str, "Chromosome (e.g., 'chr22')"],
    position: Annotated[int, "Variant position"],
    reference_bases: Annotated[str, "Reference allele"],
    alternate_bases: Annotated[str, "Alternative allele"],
    scorer_types: Annotated[List[str], "Variant scorer types from RECOMMENDED_VARIANT_SCORERS (e.g., ['RNA_SEQ', 'DNASE'])"],
    sequence_length: Annotated[str, "Model sequence length"] = "1MB",
    match_gene_strand: Annotated[bool, "Match gene strand for scoring"] = True,
    out_prefix: Annotated[str, "Output file prefix"] = f"variant_scores_{timestamp}",
) -> Dict[str, Any]:
    """
    Score the effect of a genetic variant using recommended variant scorers.
    """
    # Create DNA model
    dna_model = dna_client.create(api_key)
    
    # Create variant
    variant = genome.Variant(
        chromosome=chromosome,
        position=position,
        reference_bases=reference_bases,
        alternate_bases=alternate_bases,
    )
    
    # Get interval
    sequence_length_map = {
        '2KB': dna_client.SEQUENCE_LENGTH_2KB,
        '16KB': dna_client.SEQUENCE_LENGTH_16KB,
        '100KB': dna_client.SEQUENCE_LENGTH_100KB,
        '500KB': dna_client.SEQUENCE_LENGTH_500KB,
        '1MB': dna_client.SEQUENCE_LENGTH_1MB,
    }
    interval = variant.reference_interval.resize(sequence_length_map[sequence_length])
    
    # Get variant scorers
    scorers = []
    for scorer_type in scorer_types:
        if scorer_type in variant_scorers.RECOMMENDED_VARIANT_SCORERS:
            scorers.append(variant_scorers.RECOMMENDED_VARIANT_SCORERS[scorer_type])
        else:
            raise ValueError(f"Unknown scorer type: {scorer_type}. Available: {list(variant_scorers.RECOMMENDED_VARIANT_SCORERS.keys())}")
    
    # Score variant
    variant_scores = dna_model.score_variant(
        interval=interval,
        variant=variant,
        variant_scorers=scorers
    )
    
    # Process and save scores
    artifacts = []
    
    # Save raw scores for each scorer
    for i, (scorer_type, scores) in enumerate(zip(scorer_types, variant_scores)):
        # Save raw scores matrix
        raw_scores_file = OUTPUT_DIR / f"{out_prefix}_{scorer_type}_raw_scores.csv"
        scores_df = pd.DataFrame(scores.X)
        scores_df.to_csv(raw_scores_file, index=False)
        artifacts.append({
            "description": f"{scorer_type} raw scores matrix",
            "path": str(raw_scores_file.resolve())
        })
        
        # Save gene metadata if available
        if scores.obs is not None and len(scores.obs) > 0:
            genes_file = OUTPUT_DIR / f"{out_prefix}_{scorer_type}_genes.csv"
            scores.obs.to_csv(genes_file, index=False)
            artifacts.append({
                "description": f"{scorer_type} gene metadata",
                "path": str(genes_file.resolve())
            })
        
        # Save track metadata
        tracks_file = OUTPUT_DIR / f"{out_prefix}_{scorer_type}_tracks.csv"
        scores.var.to_csv(tracks_file, index=False)
        artifacts.append({
            "description": f"{scorer_type} track metadata",
            "path": str(tracks_file.resolve())
        })
    
    # Create tidy scores dataframe
    tidy_df = variant_scorers.tidy_scores(variant_scores, match_gene_strand=match_gene_strand)
    tidy_file = OUTPUT_DIR / f"{out_prefix}_tidy_scores.csv"
    tidy_df.to_csv(tidy_file, index=False)
    artifacts.append({
        "description": "Tidy variant scores",
        "path": str(tidy_file.resolve())
    })
    
    return {
        "message": f"Scored variant with {len(scorer_types)} scorers",
        "artifacts": artifacts
    }


@quick_start_mcp.tool
def perform_ism_analysis(
    api_key: Annotated[str, "API key for AlphaGenome model"],
    chromosome: Annotated[str, "Chromosome"],
    center_position: Annotated[int, "Center position for the analysis"],
    sequence_length: Annotated[int, "Context sequence length"] = 2048,
    ism_width: Annotated[int, "Width of region to mutate"] = 256,
    scorer_output: Annotated[str, "Output type for scoring (e.g., 'DNASE')"] = "DNASE",
    scorer_width: Annotated[int, "Width for center mask scorer"] = 501,
    target_ontology: Annotated[Optional[str], "Specific ontology term to visualize (e.g., 'EFO:0002067' for K562)"] = "EFO:0002067",
    out_prefix: Annotated[str, "Output file prefix"] = f"ism_analysis_{timestamp}",
) -> Dict[str, Any]:
    """
    Perform in silico mutagenesis analysis to highlight important DNA regions.
    """
    # Create DNA model
    dna_model = dna_client.create(api_key)
    
    # Define intervals
    sequence_interval = genome.Interval(chromosome, center_position - sequence_length // 2, 
                                       center_position + sequence_length // 2)
    sequence_interval = sequence_interval.resize(dna_client.SEQUENCE_LENGTH_2KB)
    
    # Mutate central region
    ism_interval = sequence_interval.resize(ism_width)
    
    # Define scorer
    scorer_output_enum = getattr(dna_client.OutputType, scorer_output)
    dnase_variant_scorer = variant_scorers.CenterMaskScorer(
        requested_output=scorer_output_enum,
        width=scorer_width,
        aggregation_type=variant_scorers.AggregationType.DIFF_MEAN,
    )
    
    # Score all ISM variants
    variant_scores = dna_model.score_ism_variants(
        interval=sequence_interval,
        ism_interval=ism_interval,
        variant_scorers=[dnase_variant_scorer],
    )
    
    # Save all variant scores
    artifacts = []
    all_scores = []
    all_variants = []
    
    for i, v_scores in enumerate(variant_scores):
        variant_obj = v_scores[0].uns['variant']
        all_variants.append(str(variant_obj))
        
        # Extract score for target ontology if specified
        if target_ontology:
            adata = v_scores[0]
            values = adata.X[:, adata.var['ontology_curie'] == target_ontology]
            if values.size > 0:
                score = values.flatten()[0]
            else:
                # If target not found, use mean across all tracks
                score = np.mean(adata.X)
        else:
            # Use mean across all tracks
            score = np.mean(v_scores[0].X)
        all_scores.append(score)
    
    # Save variant scores to CSV
    scores_df = pd.DataFrame({
        'variant': all_variants,
        'score': all_scores
    })
    scores_file = OUTPUT_DIR / f"{out_prefix}_variant_scores.csv"
    scores_df.to_csv(scores_file, index=False)
    artifacts.append({
        "description": "ISM variant scores",
        "path": str(scores_file.resolve())
    })
    
    # Create ISM matrix
    if target_ontology:
        def extract_target(adata):
            values = adata.X[:, adata.var['ontology_curie'] == target_ontology]
            if values.size > 0:
                return values.flatten()[0]
            else:
                return np.mean(adata.X)
        
        ism_result = ism.ism_matrix(
            [extract_target(x[0]) for x in variant_scores],
            variants=[v[0].uns['variant'] for v in variant_scores],
        )
    else:
        ism_result = ism.ism_matrix(
            [np.mean(x[0].X) for x in variant_scores],
            variants=[v[0].uns['variant'] for v in variant_scores],
        )
    
    # Save ISM matrix
    matrix_file = OUTPUT_DIR / f"{out_prefix}_ism_matrix.csv"
    matrix_df = pd.DataFrame(ism_result, columns=['A', 'C', 'G', 'T'])
    matrix_df.to_csv(matrix_file, index=False)
    artifacts.append({
        "description": "ISM matrix",
        "path": str(matrix_file.resolve())
    })
    
    # Create sequence logo visualization
    plt.figure(figsize=(35, 6))
    plot_components.plot(
        [
            plot_components.SeqLogo(
                scores=ism_result,
                scores_interval=ism_interval,
                ylabel=f'ISM {scorer_output}',
            )
        ],
        interval=ism_interval,
        fig_width=35,
    )
    logo_file = OUTPUT_DIR / f"{out_prefix}_sequence_logo.png"
    plt.savefig(logo_file, dpi=150, bbox_inches='tight')
    plt.close()
    artifacts.append({
        "description": "ISM sequence logo",
        "path": str(logo_file.resolve())
    })
    
    return {
        "message": f"Completed ISM analysis for {len(variant_scores)} variants",
        "artifacts": artifacts
    }


@quick_start_mcp.tool
def predict_mouse_sequences(
    api_key: Annotated[str, "API key for AlphaGenome model"],
    prediction_type: Annotated[str, "Type of prediction: 'sequence' or 'interval'"],
    sequence: Annotated[Optional[str], "DNA sequence (required if prediction_type='sequence')"] = None,
    chromosome: Annotated[Optional[str], "Chromosome (required if prediction_type='interval')"] = None,
    start: Annotated[Optional[int], "Start position (required if prediction_type='interval')"] = None,
    end: Annotated[Optional[int], "End position (required if prediction_type='interval')"] = None,
    requested_outputs: Annotated[List[str], "Output types to predict"] = ["DNASE"],
    ontology_terms: Annotated[List[str], "Ontology terms for tissues/cell types"] = ["UBERON:0002048"],
    sequence_length: Annotated[str, "Model sequence length"] = "1MB",
    out_prefix: Annotated[str, "Output file prefix"] = f"mouse_predictions_{timestamp}",
) -> Dict[str, Any]:
    """
    Make predictions for mouse DNA sequences or genomic intervals.
    """
    # Create DNA model
    dna_model = dna_client.create(api_key)
    
    # Convert string output types to enum
    output_enums = []
    for output_type in requested_outputs:
        output_enums.append(getattr(dna_client.OutputType, output_type))
    
    artifacts = []
    
    if prediction_type == 'sequence':
        if not sequence:
            raise ValueError("sequence is required when prediction_type='sequence'")
        
        # Pad sequence
        padded_sequence = sequence.center(2048, 'N')
        
        # Make predictions for mouse
        output = dna_model.predict_sequence(
            sequence=padded_sequence,
            organism=dna_client.Organism.MUS_MUSCULUS,
            requested_outputs=output_enums,
            ontology_terms=ontology_terms,
        )
        
    elif prediction_type == 'interval':
        if not all([chromosome, start is not None, end is not None]):
            raise ValueError("chromosome, start, and end are required when prediction_type='interval'")
        
        # Create interval
        interval = genome.Interval(chromosome, start, end)
        
        # Resize to model-compatible length
        sequence_length_map = {
            '2KB': dna_client.SEQUENCE_LENGTH_2KB,
            '16KB': dna_client.SEQUENCE_LENGTH_16KB,
            '100KB': dna_client.SEQUENCE_LENGTH_100KB,
            '500KB': dna_client.SEQUENCE_LENGTH_500KB,
            '1MB': dna_client.SEQUENCE_LENGTH_1MB,
        }
        interval = interval.resize(sequence_length_map[sequence_length])
        
        # Make predictions for mouse
        output = dna_model.predict_interval(
            interval=interval,
            organism=dna_client.Organism.MUS_MUSCULUS,
            requested_outputs=output_enums,
            ontology_terms=ontology_terms,
        )
    else:
        raise ValueError(f"Invalid prediction_type: {prediction_type}. Must be 'sequence' or 'interval'")
    
    # Save results
    for output_type in requested_outputs:
        output_data = getattr(output, output_type.lower())
        
        # Save predictions
        predictions_file = OUTPUT_DIR / f"{out_prefix}_{output_type.lower()}_predictions.csv"
        predictions_df = pd.DataFrame(output_data.values)
        predictions_df.to_csv(predictions_file, index=False)
        artifacts.append({
            "description": f"Mouse {output_type} predictions",
            "path": str(predictions_file.resolve())
        })
        
        # Save metadata
        metadata_file = OUTPUT_DIR / f"{out_prefix}_{output_type.lower()}_metadata.csv"
        output_data.metadata.to_csv(metadata_file, index=False)
        artifacts.append({
            "description": f"Mouse {output_type} metadata",
            "path": str(metadata_file.resolve())
        })
    
    return {
        "message": f"Predicted {len(requested_outputs)} output types for mouse {prediction_type}",
        "artifacts": artifacts
    }