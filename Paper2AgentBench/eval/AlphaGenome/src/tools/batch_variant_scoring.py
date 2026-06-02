"""
Batch variant scoring tools extracted from AlphaGenome tutorial.

This MCP Server provides 1 tool:
1. score_batch_variants: Score multiple genetic variants across multiple regulatory modalities

All tools were extracted from `alphagenome/colabs/batch_variant_scoring.ipynb`.
"""

import os
from pathlib import Path
from io import StringIO
from typing import Optional, Dict, Any, List
import pandas as pd
from tqdm import tqdm
from datetime import datetime
from fastmcp import FastMCP

# AlphaGenome imports
from alphagenome import colab_utils
from alphagenome.data import genome
from alphagenome.models import dna_client, variant_scorers

# Define the INPUT_DIR and OUTPUT_DIR
# Project root is two levels up from this file (src/tools/batch_variant_scoring.py)
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
DEFAULT_INPUT_DIR = PROJECT_ROOT / "tmp_inputs" / "batch_variant_scoring"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "tmp_outputs" / "batch_variant_scoring"

INPUT_DIR = Path(os.environ.get("BATCH_VARIANT_SCORING_INPUT_DIR", DEFAULT_INPUT_DIR))
OUTPUT_DIR = Path(os.environ.get("BATCH_VARIANT_SCORING_OUTPUT_DIR", DEFAULT_OUTPUT_DIR))

# Mkdir if not exist
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Define the timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Define the MCP server
batch_variant_scoring_mcp = FastMCP(name="batch_variant_scoring")


@batch_variant_scoring_mcp.tool
def score_batch_variants(
    api_key: str,
    vcf_file: Optional[str] = None,
    organism: str = "human",
    sequence_length: str = "1MB",
    score_rna_seq: bool = True,
    score_cage: bool = True,
    score_procap: bool = True,
    score_atac: bool = True,
    score_dnase: bool = True,
    score_chip_histone: bool = True,
    score_chip_tf: bool = True,
    score_polyadenylation: bool = True,
    score_splice_sites: bool = True,
    score_splice_site_usage: bool = True,
    score_splice_junctions: bool = True,
    out_prefix: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Score multiple genetic variants across multiple regulatory modalities using AlphaGenome.
    
    This tool processes a batch of variants and scores their effects on various genomic
    features including gene expression, chromatin accessibility, and splicing.
    
    Args:
        api_key: API key for AlphaGenome model access
        vcf_file: Path to VCF/TSV/CSV file containing columns: variant_id, CHROM, POS, REF, ALT.
                 If None, uses tutorial example data.
        organism: Organism to score against ('human' or 'mouse')
        sequence_length: Context window size ('2KB', '16KB', '100KB', '500KB', or '1MB')
        score_rna_seq: Include RNA-seq signal prediction
        score_cage: Include CAGE (Cap Analysis of Gene Expression)
        score_procap: Include PRO-cap (human only)
        score_atac: Include ATAC-seq (chromatin accessibility)
        score_dnase: Include DNase-seq hypersensitivity
        score_chip_histone: Include ChIP-seq histone modifications
        score_chip_tf: Include ChIP-seq transcription factors
        score_polyadenylation: Include polyadenylation sites
        score_splice_sites: Include splice site predictions
        score_splice_site_usage: Include splice site usage
        score_splice_junctions: Include splice junction predictions
        out_prefix: Optional output filename prefix
        
    Returns:
        Dictionary containing status message and paths to generated artifacts
    """
    
    # Load the model
    dna_model = dna_client.create(api_key)
    
    # Load VCF file or use example data
    if vcf_file is None:
        # Use tutorial example data
        vcf_data = """variant_id\tCHROM\tPOS\tREF\tALT
chr3_58394738_A_T_b38\tchr3\t58394738\tA\tT
chr8_28520_G_C_b38\tchr8\t28520\tG\tC
chr16_636337_G_A_b38\tchr16\t636337\tG\tA
chr16_1135446_G_T_b38\tchr16\t1135446\tG\tT
"""
        vcf = pd.read_csv(StringIO(vcf_data), sep='\t')
    else:
        # Read the provided VCF file
        file_path = Path(vcf_file)
        if not file_path.exists():
            # Try relative to INPUT_DIR
            file_path = INPUT_DIR / vcf_file
            if not file_path.exists():
                raise FileNotFoundError(f"VCF file not found: {vcf_file}")
        
        # Determine separator based on file extension
        if file_path.suffix.lower() in ['.vcf', '.tsv', '.txt']:
            vcf = pd.read_csv(file_path, sep='\t')
        elif file_path.suffix.lower() == '.csv':
            vcf = pd.read_csv(file_path)
        else:
            # Try tab-separated first
            try:
                vcf = pd.read_csv(file_path, sep='\t')
            except:
                vcf = pd.read_csv(file_path)
    
    # Validate required columns
    required_columns = ['variant_id', 'CHROM', 'POS', 'REF', 'ALT']
    for column in required_columns:
        if column not in vcf.columns:
            raise ValueError(f'VCF file is missing required column: {column}.')
    
    # Parse organism specification
    organism_map = {
        'human': dna_client.Organism.HOMO_SAPIENS,
        'mouse': dna_client.Organism.MUS_MUSCULUS,
    }
    organism_enum = organism_map[organism.lower()]
    
    # Parse sequence length
    sequence_length_enum = dna_client.SUPPORTED_SEQUENCE_LENGTHS[
        f'SEQUENCE_LENGTH_{sequence_length}'
    ]
    
    # Parse scorer specification
    scorer_selections = {
        'rna_seq': score_rna_seq,
        'cage': score_cage,
        'procap': score_procap,
        'atac': score_atac,
        'dnase': score_dnase,
        'chip_histone': score_chip_histone,
        'chip_tf': score_chip_tf,
        'polyadenylation': score_polyadenylation,
        'splice_sites': score_splice_sites,
        'splice_site_usage': score_splice_site_usage,
        'splice_junctions': score_splice_junctions,
    }
    
    all_scorers = variant_scorers.RECOMMENDED_VARIANT_SCORERS
    selected_scorers = [
        all_scorers[key]
        for key in all_scorers
        if scorer_selections.get(key.lower(), False)
    ]
    
    # Remove any scorers that are not supported for the chosen organism
    unsupported_scorers = [
        scorer
        for scorer in selected_scorers
        if (
            organism_enum.value
            not in variant_scorers.SUPPORTED_ORGANISMS[scorer.base_variant_scorer]
        ) | (
            (scorer.requested_output == dna_client.OutputType.PROCAP)
            & (organism_enum == dna_client.Organism.MUS_MUSCULUS)
        )
    ]
    
    if len(unsupported_scorers) > 0:
        print(
            f'Excluding {unsupported_scorers} scorers as they are not supported for'
            f' {organism}.'
        )
        for unsupported_scorer in unsupported_scorers:
            selected_scorers.remove(unsupported_scorer)
    
    # Score variants in the VCF file
    results = []
    
    for i, vcf_row in tqdm(vcf.iterrows(), total=len(vcf), desc="Scoring variants"):
        variant = genome.Variant(
            chromosome=str(vcf_row.CHROM),
            position=int(vcf_row.POS),
            reference_bases=vcf_row.REF,
            alternate_bases=vcf_row.ALT,
            name=vcf_row.variant_id,
        )
        interval = variant.reference_interval.resize(sequence_length_enum)
        
        variant_scores = dna_model.score_variant(
            interval=interval,
            variant=variant,
            variant_scorers=selected_scorers,
            organism=organism_enum,
        )
        results.append(variant_scores)
    
    # Tidy the scores into a dataframe
    df_scores = variant_scorers.tidy_scores(results)
    
    # Generate output filename
    if out_prefix is None:
        out_prefix = f"batch_variant_scores_{timestamp}"
    
    # Save the results
    output_file = OUTPUT_DIR / f"{out_prefix}.csv"
    df_scores.to_csv(output_file, index=False)
    
    # Count variants and tracks scored
    num_variants = len(vcf)
    num_tracks = len(df_scores['ontology_name'].unique()) if 'ontology_name' in df_scores.columns else 0
    
    return {
        "message": f"Scored {num_variants} variants across {num_tracks} tracks",
        "artifacts": [
            {
                "description": "Variant scores table",
                "path": str(output_file.resolve())
            }
        ]
    }


# Entry point for MCP server
if __name__ == "__main__":
    batch_variant_scoring_mcp.run()