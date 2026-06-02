"""
Variant scoring and visualization tools for AlphaGenome.

This MCP Server provides 2 tools:
1. score_single_variant: Score a single variant across different modalities and tissues
2. visualize_variant_effects: Visualize variant effects with gene annotations and various tracks

All tools were extracted from `alphagenome/colabs/variant_scoring_ui.ipynb`.
"""

# Define the MCP server and import required packages
from alphagenome import colab_utils
from alphagenome.data import gene_annotation, genome, transcript
from alphagenome.models import dna_client, variant_scorers
from alphagenome.visualization import plot_components
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from fastmcp import FastMCP
from datetime import datetime
from typing import Annotated, Optional
import os

# Define the INPUT_DIR and OUTPUT_DIR
# Project root is two levels up from this file (src/tools/variant_scoring_ui.py)
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
DEFAULT_INPUT_DIR = PROJECT_ROOT / "tmp_inputs" / "variant_scoring_ui"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "tmp_outputs" / "variant_scoring_ui"

INPUT_DIR = Path(os.environ.get("VARIANT_SCORING_UI_INPUT_DIR", DEFAULT_INPUT_DIR))
OUTPUT_DIR = Path(os.environ.get("VARIANT_SCORING_UI_OUTPUT_DIR", DEFAULT_OUTPUT_DIR))

# Mkdir if not exist
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Define the timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Define the MCP server
variant_scoring_ui_mcp = FastMCP(name="variant_scoring_ui")

# Initialize caches
_prediction_cache = {}
_transcript_extractor_cache = {}

# Reference GTF files
HG38_GTF_FEATHER = (
    'https://storage.googleapis.com/alphagenome/reference/gencode/'
    'hg38/gencode.v46.annotation.gtf.gz.feather'
)
MM10_GTF_FEATHER = (
    'https://storage.googleapis.com/alphagenome/reference/gencode/'
    'mm10/gencode.vM23.annotation.gtf.gz.feather'
)

# Public tools blocks that are used in the tutorial and will be exposed to the user
@variant_scoring_ui_mcp.tool
def score_single_variant(
    api_key: Annotated[str, "API key for AlphaGenome model"],
    variant_chromosome: Annotated[str, "Chromosome of the variant"] = 'chr22',
    variant_position: Annotated[int, "Position of the variant"] = 36201698,
    variant_reference_bases: Annotated[str, "Reference allele"] = 'A',
    variant_alternate_bases: Annotated[str, "Alternate allele"] = 'C',
    organism: Annotated[str, "Organism: 'human' or 'mouse'"] = 'human',
    sequence_length: Annotated[str, "Sequence length: '2KB', '16KB', '100KB', '500KB', or '1MB'"] = '1MB',
    out_prefix: Annotated[Optional[str], "Output file prefix"] = None,
) -> dict:
    """
    Score a single variant across different modalities and tissues using AlphaGenome.
    """
    if out_prefix is None:
        out_prefix = f"variant_scoring_{timestamp}"
    
    # Load the model
    dna_model = dna_client.create(api_key)
    
    # Map organism string to enum
    organism_map = {
        'human': dna_client.Organism.HOMO_SAPIENS,
        'mouse': dna_client.Organism.MUS_MUSCULUS,
    }
    organism_enum = organism_map[organism]
    
    # Create variant object
    variant = genome.Variant(
        chromosome=variant_chromosome,
        position=variant_position,
        reference_bases=variant_reference_bases,
        alternate_bases=variant_alternate_bases,
    )
    
    # Map sequence length
    sequence_length_enum = dna_client.SUPPORTED_SEQUENCE_LENGTHS[
        f'SEQUENCE_LENGTH_{sequence_length}'
    ]
    
    # The input interval is derived from the variant (centered on it)
    interval = variant.reference_interval.resize(sequence_length_enum)
    
    # Score the variant
    variant_scores = dna_model.score_variant(
        interval=interval,
        variant=variant,
        variant_scorers=list(variant_scorers.RECOMMENDED_VARIANT_SCORERS.values()),
    )
    
    # Tidy the scores
    df_scores = variant_scorers.tidy_scores(variant_scores)
    
    # Save the scores
    output_file = OUTPUT_DIR / f"{out_prefix}_scores.csv"
    df_scores.to_csv(output_file, index=False)
    
    return {
        "message": f"Scored variant {variant} and saved results",
        "artifacts": [
            {
                "description": "Variant scores table",
                "path": str(output_file.resolve())
            }
        ]
    }


@variant_scoring_ui_mcp.tool
def visualize_variant_effects(
    api_key: Annotated[str, "API key for AlphaGenome model"],
    variant_chromosome: Annotated[str, "Chromosome of the variant"] = 'chr22',
    variant_position: Annotated[int, "Position of the variant"] = 36201698,
    variant_reference_bases: Annotated[str, "Reference allele"] = 'A',
    variant_alternate_bases: Annotated[str, "Alternate allele"] = 'C',
    organism: Annotated[str, "Organism: 'human' or 'mouse'"] = 'human',
    sequence_length: Annotated[str, "Sequence length: '2KB', '16KB', '100KB', '500KB', or '1MB'"] = '1MB',
    ontology_terms: Annotated[str, "Comma-separated list of cell/tissue ontology terms"] = 'EFO:0001187,EFO:0002067,EFO:0002784',
    plot_gene_annotation: Annotated[bool, "Plot gene annotations"] = True,
    plot_longest_transcript_only: Annotated[bool, "Plot only longest transcript per gene"] = True,
    plot_rna_seq: Annotated[bool, "Plot RNA-seq tracks"] = True,
    plot_cage: Annotated[bool, "Plot CAGE tracks"] = True,
    plot_atac: Annotated[bool, "Plot ATAC tracks"] = False,
    plot_dnase: Annotated[bool, "Plot DNase tracks"] = False,
    plot_chip_histone: Annotated[bool, "Plot ChIP-histone tracks"] = False,
    plot_chip_tf: Annotated[bool, "Plot ChIP-TF tracks"] = False,
    plot_splice_sites: Annotated[bool, "Plot splice sites"] = True,
    plot_splice_site_usage: Annotated[bool, "Plot splice site usage"] = False,
    plot_contact_maps: Annotated[bool, "Plot contact maps"] = False,
    plot_splice_junctions: Annotated[bool, "Plot splice junctions"] = False,
    filter_to_positive_strand: Annotated[bool, "Filter to positive strand only"] = False,
    filter_to_negative_strand: Annotated[bool, "Filter to negative strand only"] = True,
    ref_color: Annotated[str, "Color for reference allele"] = 'dimgrey',
    alt_color: Annotated[str, "Color for alternate allele"] = 'red',
    plot_interval_width: Annotated[int, "Width of plot interval"] = 43008,
    plot_interval_shift: Annotated[int, "Shift of plot interval"] = 0,
    out_prefix: Annotated[Optional[str], "Output file prefix"] = None,
) -> dict:
    """
    Visualize variant effects with gene annotations and various genomic tracks.
    """
    if out_prefix is None:
        out_prefix = f"variant_effects_{timestamp}"
    
    # Parse ontology terms
    ontology_terms_list = [term.strip() for term in ontology_terms.split(',')]
    
    # Validate strand filtering
    if filter_to_positive_strand and filter_to_negative_strand:
        raise ValueError(
            'Cannot specify both filter_to_positive_strand and '
            'filter_to_negative_strand.'
        )
    
    # Load the model
    dna_model = dna_client.create(api_key)
    
    # Map organism string to enum
    organism_map = {
        'human': dna_client.Organism.HOMO_SAPIENS,
        'mouse': dna_client.Organism.MUS_MUSCULUS,
    }
    organism_enum = organism_map[organism]
    
    # Create variant object
    variant = genome.Variant(
        chromosome=variant_chromosome,
        position=variant_position,
        reference_bases=variant_reference_bases,
        alternate_bases=variant_alternate_bases,
    )
    
    # Map sequence length
    sequence_length_enum = dna_client.SUPPORTED_SEQUENCE_LENGTHS[
        f'SEQUENCE_LENGTH_{sequence_length}'
    ]
    
    # The input interval is derived from the variant (centered on it)
    interval = variant.reference_interval.resize(sequence_length_enum)
    
    # Load gene annotation
    global _transcript_extractor_cache
    if organism_enum in _transcript_extractor_cache:
        transcript_extractor, longest_transcript_extractor = (
            _transcript_extractor_cache[organism_enum]
        )
    else:
        match organism_enum:
            case dna_client.Organism.HOMO_SAPIENS:
                gtf_path = HG38_GTF_FEATHER
            case dna_client.Organism.MUS_MUSCULUS:
                gtf_path = MM10_GTF_FEATHER
            case _:
                raise ValueError(f'Unsupported organism: {organism_enum}')
        
        gtf = pd.read_feather(gtf_path)
        
        # Filter to protein-coding genes and highly supported transcripts
        gtf_transcript = gene_annotation.filter_transcript_support_level(
            gene_annotation.filter_protein_coding(gtf), ['1']
        )
        
        # Extractor for identifying transcripts in a region
        transcript_extractor = transcript.TranscriptExtractor(gtf_transcript)
        
        # Also define an extractor that fetches only the longest transcript per gene
        gtf_longest_transcript = gene_annotation.filter_to_longest_transcript(
            gtf_transcript
        )
        longest_transcript_extractor = transcript.TranscriptExtractor(
            gtf_longest_transcript
        )
        _transcript_extractor_cache[organism_enum] = (
            transcript_extractor,
            longest_transcript_extractor,
        )
    
    # Predict variant effects (with caching)
    def _predict_variant_cached(
        interval, variant, organism, requested_outputs, ontology_terms
    ):
        """Cache wrapper of dna_model.predict_variant."""
        global _prediction_cache
        # Create a unique key from the function arguments
        cache_key = (
            str(interval),
            str(variant),
            str(organism),
            tuple(requested_outputs),
            tuple(ontology_terms),
        )
        
        # Check if the result is already in the cache
        if cache_key in _prediction_cache:
            return _prediction_cache[cache_key]
        
        # If not, compute the prediction and store it in the cache
        result = dna_model.predict_variant(
            interval=interval,
            variant=variant,
            organism=organism,
            requested_outputs=requested_outputs,
            ontology_terms=ontology_terms,
        )
        _prediction_cache[cache_key] = result
        return result
    
    output = _predict_variant_cached(
        interval=interval,
        variant=variant,
        organism=organism_enum,
        requested_outputs=[*dna_client.OutputType],
        ontology_terms=ontology_terms_list,
    )
    
    # Filter to DNA strand if requested
    ref, alt = output.reference, output.alternate
    
    if filter_to_positive_strand:
        ref = ref.filter_to_strand(strand='+')
        alt = alt.filter_to_strand(strand='+')
    elif filter_to_negative_strand:
        ref = ref.filter_to_strand(strand='-')
        alt = alt.filter_to_strand(strand='-')
    
    # Build plot components
    components = []
    ref_alt_colors = {'REF': ref_color, 'ALT': alt_color}
    
    # Gene and transcript annotation
    if plot_gene_annotation:
        if plot_longest_transcript_only:
            transcripts = longest_transcript_extractor.extract(interval)
        else:
            transcripts = transcript_extractor.extract(interval)
        components.append(plot_components.TranscriptAnnotation(transcripts))
    
    # Individual output type plots
    plot_map = {
        'plot_atac': (ref.atac, alt.atac, 'ATAC'),
        'plot_cage': (ref.cage, alt.cage, 'CAGE'),
        'plot_chip_histone': (ref.chip_histone, alt.chip_histone, 'CHIP_HISTONE'),
        'plot_chip_tf': (ref.chip_tf, alt.chip_tf, 'CHIP_TF'),
        'plot_contact_maps': (ref.contact_maps, alt.contact_maps, 'CONTACT_MAPS'),
        'plot_dnase': (ref.dnase, alt.dnase, 'DNASE'),
        'plot_rna_seq': (ref.rna_seq, alt.rna_seq, 'RNA_SEQ'),
        'plot_splice_junctions': (
            ref.splice_junctions,
            alt.splice_junctions,
            'SPLICE_JUNCTIONS',
        ),
        'plot_splice_sites': (ref.splice_sites, alt.splice_sites, 'SPLICE_SITES'),
        'plot_splice_site_usage': (
            ref.splice_site_usage,
            alt.splice_site_usage,
            'SPLICE_SITE_USAGE',
        ),
    }
    
    for key, (ref_data, alt_data, output_type) in plot_map.items():
        if eval(key) and ref_data is not None and ref_data.values.shape[-1] == 0:
            print(
                f'Requested plot for output {output_type} but no tracks exist in'
                ' output. This is likely because this output does not exist for your'
                ' ontologies or requested DNA strand.'
            )
        if eval(key) and ref_data and alt_data:
            match output_type:
                case 'CHIP_HISTONE':
                    ylabel_template = (
                        f'{output_type}: {{biosample_name}} ({{strand}})\n{{histone_mark}}'
                    )
                case 'CHIP_TF':
                    ylabel_template = (
                        f'{output_type}: {{biosample_name}}'
                        ' ({strand})\n{transcription_factor}'
                    )
                case 'CONTACT_MAPS':
                    ylabel_template = f'{output_type}: {{biosample_name}} ({{strand}})'
                case 'SPLICE_SITES':
                    ylabel_template = f'{output_type}: {{name}} ({{strand}})'
                case _:
                    ylabel_template = (
                        f'{output_type}: {{biosample_name}} ({{strand}})\n{{name}}'
                    )
            
            if output_type == 'CONTACT_MAPS':
                component = plot_components.ContactMapsDiff(
                    tdata=alt_data - ref_data,
                    ylabel_template=ylabel_template,
                )
                components.append(component)
            elif output_type == 'SPLICE_JUNCTIONS':
                ref_plot = plot_components.Sashimi(
                    ref_data,
                    ylabel_template='REF: ' + ylabel_template,
                )
                alt_plot = plot_components.Sashimi(
                    alt_data,
                    ylabel_template='ALT: ' + ylabel_template,
                )
                components.extend([ref_plot, alt_plot])
            else:
                component = plot_components.OverlaidTracks(
                    tdata={'REF': ref_data, 'ALT': alt_data},
                    colors=ref_alt_colors,
                    ylabel_template=ylabel_template,
                )
                components.append(component)
    
    if plot_interval_width > interval.width:
        raise ValueError(
            f'plot_interval_width ({plot_interval_width}) must be less than '
            f'interval.width ({interval.width}).'
        )
    
    plot = plot_components.plot(
        components=components,
        interval=interval.shift(plot_interval_shift).resize(plot_interval_width),
        annotations=[
            plot_components.VariantAnnotation([variant]),
        ],
    )
    
    # Save the plot
    output_file = OUTPUT_DIR / f"{out_prefix}_visualization.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    return {
        "message": f"Visualized variant effects for {variant}",
        "artifacts": [
            {
                "description": "Variant effects visualization",
                "path": str(output_file.resolve())
            }
        ]
    }