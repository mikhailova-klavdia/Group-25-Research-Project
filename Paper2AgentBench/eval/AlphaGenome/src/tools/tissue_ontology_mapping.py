"""
Tools for navigating and analyzing AlphaGenome data ontologies.

This MCP Server provides 2 tools:
1. get_output_metadata: Retrieve and explore output metadata for a given organism
2. count_tracks_by_output_type: Count the number of tracks per output type for human and mouse

All tools were extracted from `alphagenome/colabs/tissue_ontology_mapping.ipynb`.
"""

# Define the MCP server and import required packages
from alphagenome.models import dna_client
import pandas as pd
import os
from pathlib import Path
from fastmcp import FastMCP
from datetime import datetime
from typing import Annotated, Optional

# Define the INPUT_DIR and OUTPUT_DIR
# Project root is two levels up from this file (src/tools/tissue_ontology_mapping.py)
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
DEFAULT_INPUT_DIR = PROJECT_ROOT / "tmp_inputs" / "tissue_ontology_mapping"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "tmp_outputs" / "tissue_ontology_mapping"

INPUT_DIR = Path(os.environ.get("TISSUE_ONTOLOGY_MAPPING_INPUT_DIR", DEFAULT_INPUT_DIR))
OUTPUT_DIR = Path(os.environ.get("TISSUE_ONTOLOGY_MAPPING_OUTPUT_DIR", DEFAULT_OUTPUT_DIR))

# Mkdir if not exist
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Define the timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Define the MCP server
tissue_ontology_mapping_mcp = FastMCP(name="tissue_ontology_mapping")

# No Private functions

# Public tools blocks that are used in the tutorial and will be exposed to the user
@tissue_ontology_mapping_mcp.tool
def get_output_metadata(
    api_key: Annotated[str, "API key for AlphaGenome model"],
    organism: Annotated[str, "Organism to get metadata for: 'human' or 'mouse'"] = "human",
    out_prefix: Annotated[str, "Output file prefix"] = f"output_metadata_{timestamp}",
) -> dict:
    """
    Retrieve and explore output metadata for a given organism.
    """
    # Create DNA model client
    dna_model = dna_client.create(api_key)
    
    # Map organism string to enum
    if organism.lower() == "human":
        organism_enum = dna_client.Organism.HOMO_SAPIENS
    elif organism.lower() == "mouse":
        organism_enum = dna_client.Organism.MUS_MUSCULUS
    else:
        raise ValueError(f"Invalid organism: {organism}. Must be 'human' or 'mouse'.")
    
    # Get output metadata
    output_metadata = dna_model.output_metadata(organism_enum).concatenate()
    
    # Save to CSV
    output_file = OUTPUT_DIR / f"{out_prefix}.csv"
    output_metadata.to_csv(output_file, index=False)
    
    return {
        "message": f"Saved metadata for {organism} with {len(output_metadata)} tracks",
        "artifacts": [
            {
                "description": f"{organism.capitalize()} output metadata",
                "path": str(output_file.resolve())
            }
        ]
    }


@tissue_ontology_mapping_mcp.tool
def count_tracks_by_output_type(
    api_key: Annotated[str, "API key for AlphaGenome model"],
    out_prefix: Annotated[str, "Output file prefix"] = f"track_counts_{timestamp}",
) -> dict:
    """
    Count the number of tracks per output type for human and mouse organisms.
    """
    # Create DNA model client
    dna_model = dna_client.create(api_key)
    
    # Count human tracks
    human_tracks = (
        dna_model.output_metadata(dna_client.Organism.HOMO_SAPIENS)
        .concatenate()
        .groupby('output_type')
        .size()
        .rename('# Human tracks')
    )
    
    # Count mouse tracks
    mouse_tracks = (
        dna_model.output_metadata(dna_client.Organism.MUS_MUSCULUS)
        .concatenate()
        .groupby('output_type')
        .size()
        .rename('# Mouse tracks')
    )
    
    # Combine and format the results
    track_counts = pd.concat([human_tracks, mouse_tracks], axis=1).astype(pd.Int64Dtype())
    
    # Save to CSV
    output_file = OUTPUT_DIR / f"{out_prefix}.csv"
    track_counts.to_csv(output_file)
    
    return {
        "message": f"Saved track counts for {len(track_counts)} output types",
        "artifacts": [
            {
                "description": "Track counts by output type",
                "path": str(output_file.resolve())
            }
        ]
    }