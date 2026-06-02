"""
Essential commands for interacting with the AlphaGenome API.

This MCP Server provides 11 tools:
1. create_genomic_interval: Create and manipulate a genomic interval with basic properties
2. resize_interval: Resize a genomic interval around its center point
3. compare_intervals: Compare two intervals for overlap, containment, and intersection
4. create_genomic_variant: Create genetic variants including SNPs and indels
5. variant_interval_overlap: Check variant-interval overlap for reference and alternate alleles
6. create_track_data: Create TrackData objects from values and metadata
7. change_track_resolution: Convert track data between different resolutions
8. filter_tracks_by_strand: Filter tracks by DNA strand orientation
9. slice_track_data: Slice track data by position or genomic interval
10. select_tracks: Select and reorder specific tracks by name
11. reverse_complement_tracks: Reverse complement track values in a strand-aware manner

All tools were extracted from `alphagenome/colabs/essential_commands.ipynb`.
"""

# Define the MCP server and import required packages
from alphagenome.data import genome, track_data
from alphagenome.models import dna_client
import anndata
import numpy as np
import pandas as pd
import os
from pathlib import Path
from fastmcp import FastMCP
from datetime import datetime
from typing import Annotated, Optional, List, Dict, Any, Union

# Define the INPUT_DIR and OUTPUT_DIR
# Project root is two levels up from this file (src/tools/essential_commands.py)
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
DEFAULT_INPUT_DIR = PROJECT_ROOT / "tmp_inputs" / "essential_commands"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "tmp_outputs" / "essential_commands"

INPUT_DIR = Path(os.environ.get("ESSENTIAL_COMMANDS_INPUT_DIR", DEFAULT_INPUT_DIR))
OUTPUT_DIR = Path(os.environ.get("ESSENTIAL_COMMANDS_OUTPUT_DIR", DEFAULT_OUTPUT_DIR))

# Mkdir if not exist
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Define the timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Define the MCP server
essential_commands_mcp = FastMCP(name="essential_commands")


@essential_commands_mcp.tool
def create_genomic_interval(
    chromosome: Annotated[str, "Chromosome name (e.g., 'chr1')"] = "chr1",
    start: Annotated[int, "Start position (0-based)"] = 1000,
    end: Annotated[int, "End position (0-based, exclusive)"] = 1010,
    out_prefix: Annotated[Optional[str], "Output file prefix"] = None,
) -> Dict[str, Any]:
    """
    Create a genomic interval and demonstrate its basic properties including center and width.
    """
    if out_prefix is None:
        out_prefix = f"genomic_interval_{timestamp}"
    
    # Create interval exactly as in tutorial
    interval = genome.Interval(chromosome=chromosome, start=start, end=end)
    
    # Get properties as shown in tutorial
    center_pos = interval.center()
    width = interval.width
    
    # Save results to CSV
    results_df = pd.DataFrame({
        'chromosome': [interval.chromosome],
        'start': [interval.start],
        'end': [interval.end],
        'center': [center_pos],
        'width': [width],
        'strand': [interval.strand],
        'name': [interval.name]
    })
    
    output_path = OUTPUT_DIR / f"{out_prefix}.csv"
    results_df.to_csv(output_path, index=False)
    
    return {
        "message": f"Created genomic interval with center {center_pos} and width {width}",
        "artifacts": [
            {
                "description": "Genomic interval properties",
                "path": str(output_path.resolve())
            }
        ]
    }


@essential_commands_mcp.tool
def resize_interval(
    chromosome: Annotated[str, "Chromosome name"] = "chr1",
    start: Annotated[int, "Original start position"] = 1000,
    end: Annotated[int, "Original end position"] = 1010,
    new_width: Annotated[int, "New width for resizing"] = 100,
    out_prefix: Annotated[Optional[str], "Output file prefix"] = None,
) -> Dict[str, Any]:
    """
    Resize a genomic interval around its center point to a specified width.
    """
    if out_prefix is None:
        out_prefix = f"resize_interval_{timestamp}"
    
    # Create original interval
    interval = genome.Interval(chromosome=chromosome, start=start, end=end)
    
    # Resize as shown in tutorial
    resized = interval.resize(new_width)
    
    # Save both original and resized
    results_df = pd.DataFrame([
        {
            'type': 'original',
            'chromosome': interval.chromosome,
            'start': interval.start,
            'end': interval.end,
            'width': interval.width
        },
        {
            'type': 'resized',
            'chromosome': resized.chromosome,
            'start': resized.start,
            'end': resized.end,
            'width': resized.width
        }
    ])
    
    output_path = OUTPUT_DIR / f"{out_prefix}.csv"
    results_df.to_csv(output_path, index=False)
    
    return {
        "message": f"Resized interval from width {interval.width} to {resized.width}",
        "artifacts": [
            {
                "description": "Original and resized intervals",
                "path": str(output_path.resolve())
            }
        ]
    }


@essential_commands_mcp.tool
def compare_intervals(
    chr1: Annotated[str, "First interval chromosome"] = "chr1",
    start1: Annotated[int, "First interval start"] = 1000,
    end1: Annotated[int, "First interval end"] = 1010,
    chr2: Annotated[str, "Second interval chromosome"] = "chr1",
    start2: Annotated[int, "Second interval start"] = 1005,
    end2: Annotated[int, "Second interval end"] = 1015,
    out_prefix: Annotated[Optional[str], "Output file prefix"] = None,
) -> Dict[str, Any]:
    """
    Compare two genomic intervals for overlap, containment, and intersection relationships.
    """
    if out_prefix is None:
        out_prefix = f"compare_intervals_{timestamp}"
    
    # Create intervals as in tutorial
    interval = genome.Interval(chromosome=chr1, start=start1, end=end1)
    second_interval = genome.Interval(chromosome=chr2, start=start2, end=end2)
    
    # Check relationships
    overlaps = interval.overlaps(second_interval)
    contains = interval.contains(second_interval)
    
    # Get intersection
    if overlaps and interval.chromosome == second_interval.chromosome:
        intersection = interval.intersect(second_interval)
        intersect_data = {
            'chromosome': intersection.chromosome,
            'start': intersection.start,
            'end': intersection.end,
            'width': intersection.width
        }
    else:
        intersect_data = {
            'chromosome': None,
            'start': None,
            'end': None,
            'width': 0
        }
    
    # Save comparison results
    results_df = pd.DataFrame([{
        'interval1': f"{interval.chromosome}:{interval.start}-{interval.end}",
        'interval2': f"{second_interval.chromosome}:{second_interval.start}-{second_interval.end}",
        'overlaps': overlaps,
        'interval1_contains_interval2': contains,
        'intersection': f"{intersect_data['chromosome']}:{intersect_data['start']}-{intersect_data['end']}" if intersect_data['chromosome'] else "None",
        'intersection_width': intersect_data['width']
    }])
    
    output_path = OUTPUT_DIR / f"{out_prefix}.csv"
    results_df.to_csv(output_path, index=False)
    
    return {
        "message": f"Intervals overlap: {overlaps}, contains: {contains}",
        "artifacts": [
            {
                "description": "Interval comparison results",
                "path": str(output_path.resolve())
            }
        ]
    }


@essential_commands_mcp.tool
def create_genomic_variant(
    chromosome: Annotated[str, "Chromosome name"] = "chr3",
    position: Annotated[int, "Variant position (1-based)"] = 10000,
    reference_bases: Annotated[str, "Reference allele sequence"] = "A",
    alternate_bases: Annotated[str, "Alternate allele sequence"] = "C",
    variant_type: Annotated[str, "Type of variant: 'snp', 'insertion', or 'deletion'"] = "snp",
    out_prefix: Annotated[Optional[str], "Output file prefix"] = None,
) -> Dict[str, Any]:
    """
    Create genetic variants including SNPs, insertions, and deletions with reference interval calculation.
    """
    if out_prefix is None:
        out_prefix = f"genomic_variant_{timestamp}"
    
    # Handle different variant types as shown in tutorial
    if variant_type == "insertion":
        reference_bases = "T"
        alternate_bases = "CGTCAAT"
    elif variant_type == "deletion":
        reference_bases = "AGGGATC"
        alternate_bases = "C"
    
    # Create variant
    variant = genome.Variant(
        chromosome=chromosome,
        position=position,
        reference_bases=reference_bases,
        alternate_bases=alternate_bases
    )
    
    # Get reference interval
    ref_interval = variant.reference_interval
    
    # Resize to AlphaGenome compatible length
    input_interval = ref_interval.resize(dna_client.SEQUENCE_LENGTH_1MB)
    
    # Save variant information
    results_df = pd.DataFrame([{
        'chromosome': variant.chromosome,
        'position': variant.position,
        'reference_bases': variant.reference_bases,
        'alternate_bases': variant.alternate_bases,
        'variant_type': variant_type,
        'ref_interval_start': ref_interval.start,
        'ref_interval_end': ref_interval.end,
        'input_interval_width': input_interval.width
    }])
    
    output_path = OUTPUT_DIR / f"{out_prefix}.csv"
    results_df.to_csv(output_path, index=False)
    
    return {
        "message": f"Created {variant_type} variant at {chromosome}:{position}",
        "artifacts": [
            {
                "description": "Genomic variant details",
                "path": str(output_path.resolve())
            }
        ]
    }


@essential_commands_mcp.tool
def variant_interval_overlap(
    variant_chr: Annotated[str, "Variant chromosome"] = "chr3",
    variant_pos: Annotated[int, "Variant position (1-based)"] = 10000,
    variant_ref: Annotated[str, "Reference bases"] = "T",
    variant_alt: Annotated[str, "Alternate bases"] = "CGTCAAT",
    interval_chr: Annotated[str, "Interval chromosome"] = "chr3",
    interval_start: Annotated[int, "Interval start (0-based)"] = 10005,
    interval_end: Annotated[int, "Interval end (0-based)"] = 10010,
    out_prefix: Annotated[Optional[str], "Output file prefix"] = None,
) -> Dict[str, Any]:
    """
    Check if a variant's reference or alternate alleles overlap with a genomic interval.
    """
    if out_prefix is None:
        out_prefix = f"variant_interval_overlap_{timestamp}"
    
    # Create variant and interval as in tutorial
    variant = genome.Variant(
        chromosome=variant_chr,
        position=variant_pos,
        reference_bases=variant_ref,
        alternate_bases=variant_alt
    )
    
    interval = genome.Interval(
        chromosome=interval_chr,
        start=interval_start,
        end=interval_end
    )
    
    # Check overlaps
    ref_overlaps = variant.reference_overlaps(interval)
    alt_overlaps = variant.alternate_overlaps(interval)
    
    # Save overlap results
    results_df = pd.DataFrame([{
        'variant': f"{variant.chromosome}:{variant.position} {variant.reference_bases}>{variant.alternate_bases}",
        'interval': f"{interval.chromosome}:{interval.start}-{interval.end}",
        'reference_overlaps': ref_overlaps,
        'alternative_overlaps': alt_overlaps
    }])
    
    output_path = OUTPUT_DIR / f"{out_prefix}.csv"
    results_df.to_csv(output_path, index=False)
    
    return {
        "message": f"Reference overlaps: {ref_overlaps}, Alternative overlaps: {alt_overlaps}",
        "artifacts": [
            {
                "description": "Variant-interval overlap analysis",
                "path": str(output_path.resolve())
            }
        ]
    }


@essential_commands_mcp.tool
def create_track_data(
    sequence_length: Annotated[int, "Length of the sequence"] = 4,
    num_tracks: Annotated[int, "Number of tracks"] = 3,
    resolution: Annotated[int, "Track resolution in base pairs"] = 1,
    interval_chr: Annotated[str, "Interval chromosome"] = "chr1",
    interval_start: Annotated[int, "Interval start position"] = 1000,
    out_prefix: Annotated[Optional[str], "Output file prefix"] = None,
) -> Dict[str, Any]:
    """
    Create TrackData objects with values, metadata, and genomic intervals.
    """
    if out_prefix is None:
        out_prefix = f"track_data_{timestamp}"
    
    # Create values array as in tutorial
    values = np.arange(sequence_length * num_tracks).reshape(sequence_length, num_tracks).astype(np.float32)
    
    # Create metadata with track names and strands
    # Following the tutorial pattern: track1 has both strands, track2 is unstranded
    if num_tracks >= 3:
        metadata = pd.DataFrame({
            'name': ['track1', 'track1', 'track2'],
            'strand': ['+', '-', '.'],
        })
    else:
        metadata = pd.DataFrame({
            'name': [f'track{i+1}' for i in range(num_tracks)],
            'strand': ['+' if i == 0 else '-' if i == 1 else '.' for i in range(num_tracks)]
        })
    
    # Calculate interval end based on resolution
    interval_end = interval_start + (sequence_length * resolution)
    interval = genome.Interval(
        chromosome=interval_chr,
        start=interval_start,
        end=interval_end
    )
    
    # Create TrackData
    tdata = track_data.TrackData(
        values=values,
        metadata=metadata,
        resolution=resolution,
        interval=interval
    )
    
    # Save values and metadata
    values_df = pd.DataFrame(values, columns=[f'track_{i}' for i in range(num_tracks)])
    values_path = OUTPUT_DIR / f"{out_prefix}_values.csv"
    values_df.to_csv(values_path, index=False)
    
    metadata_path = OUTPUT_DIR / f"{out_prefix}_metadata.csv"
    metadata.to_csv(metadata_path, index=False)
    
    return {
        "message": f"Created TrackData with shape {values.shape} at resolution {resolution}bp",
        "artifacts": [
            {
                "description": "Track values matrix",
                "path": str(values_path.resolve())
            },
            {
                "description": "Track metadata",
                "path": str(metadata_path.resolve())
            }
        ]
    }


@essential_commands_mcp.tool
def change_track_resolution(
    original_resolution: Annotated[int, "Original resolution in base pairs"] = 1,
    target_resolution: Annotated[int, "Target resolution in base pairs"] = 2,
    sequence_length: Annotated[int, "Original sequence length"] = 4,
    num_tracks: Annotated[int, "Number of tracks"] = 3,
    out_prefix: Annotated[Optional[str], "Output file prefix"] = None,
) -> Dict[str, Any]:
    """
    Convert track data between different resolutions by downsampling or upsampling.
    """
    if out_prefix is None:
        out_prefix = f"change_resolution_{timestamp}"
    
    # Create initial track data as in tutorial
    values = np.array([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]]).astype(np.float32)
    metadata = pd.DataFrame({
        'name': ['track1', 'track1', 'track2'],
        'strand': ['+', '-', '.'],
    })
    
    interval = genome.Interval(
        chromosome='chr1',
        start=1000,
        end=1000 + sequence_length * original_resolution
    )
    
    tdata = track_data.TrackData(
        values=values,
        metadata=metadata,
        resolution=original_resolution,
        interval=interval
    )
    
    # Change resolution
    tdata_new = tdata.change_resolution(resolution=target_resolution)
    
    # Save original and new resolution data
    results_list = []
    
    # Original data
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            results_list.append({
                'resolution': original_resolution,
                'position': i,
                'track': j,
                'value': values[i, j]
            })
    
    # New resolution data
    for i in range(tdata_new.values.shape[0]):
        for j in range(tdata_new.values.shape[1]):
            results_list.append({
                'resolution': target_resolution,
                'position': i,
                'track': j,
                'value': tdata_new.values[i, j]
            })
    
    results_df = pd.DataFrame(results_list)
    
    # Also save summary
    summary_df = pd.DataFrame([
        {
            'type': 'original',
            'resolution': original_resolution,
            'shape': str(values.shape),
            'sum': values.sum()
        },
        {
            'type': 'new_resolution',
            'resolution': target_resolution,
            'shape': str(tdata_new.values.shape),
            'sum': tdata_new.values.sum()
        }
    ])
    
    output_path = OUTPUT_DIR / f"{out_prefix}.csv"
    results_df.to_csv(output_path, index=False)
    
    summary_path = OUTPUT_DIR / f"{out_prefix}_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    
    return {
        "message": f"Changed resolution from {original_resolution}bp to {target_resolution}bp",
        "artifacts": [
            {
                "description": "Resolution change details",
                "path": str(output_path.resolve())
            },
            {
                "description": "Resolution change summary",
                "path": str(summary_path.resolve())
            }
        ]
    }


@essential_commands_mcp.tool
def filter_tracks_by_strand(
    strand_filter: Annotated[str, "Strand to filter: 'positive', 'negative', or 'unstranded'"] = "positive",
    out_prefix: Annotated[Optional[str], "Output file prefix"] = None,
) -> Dict[str, Any]:
    """
    Filter track data by DNA strand orientation (positive, negative, or unstranded).
    """
    if out_prefix is None:
        out_prefix = f"filter_strand_{timestamp}"
    
    # Create track data as in tutorial
    values = np.array([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]]).astype(np.float32)
    metadata = pd.DataFrame({
        'name': ['track1', 'track1', 'track2'],
        'strand': ['+', '-', '.'],
    })
    
    interval = genome.Interval(chromosome='chr1', start=1000, end=1004)
    tdata = track_data.TrackData(
        values=values,
        metadata=metadata,
        resolution=1,
        interval=interval
    )
    
    # Filter by strand
    if strand_filter == "positive":
        filtered = tdata.filter_to_positive_strand()
    elif strand_filter == "negative":
        filtered = tdata.filter_to_negative_strand()
    else:  # unstranded
        filtered = tdata.filter_to_unstranded()
    
    # Save filtered results
    filtered_df = pd.DataFrame(
        filtered.values,
        columns=[f'track_{i}' for i in range(filtered.values.shape[1])]
    )
    filtered_path = OUTPUT_DIR / f"{out_prefix}_filtered.csv"
    filtered_df.to_csv(filtered_path, index=False)
    
    # Save filtered metadata
    metadata_path = OUTPUT_DIR / f"{out_prefix}_metadata.csv"
    filtered.metadata.to_csv(metadata_path, index=False)
    
    # Save summary
    summary_df = pd.DataFrame([
        {
            'filter': strand_filter,
            'original_tracks': len(metadata),
            'filtered_tracks': len(filtered.metadata),
            'track_names': ', '.join(filtered.metadata.name.values)
        }
    ])
    summary_path = OUTPUT_DIR / f"{out_prefix}_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    
    return {
        "message": f"Filtered to {strand_filter} strand: {len(filtered.metadata)} tracks",
        "artifacts": [
            {
                "description": "Filtered track values",
                "path": str(filtered_path.resolve())
            },
            {
                "description": "Filtered track metadata",
                "path": str(metadata_path.resolve())
            },
            {
                "description": "Filter summary",
                "path": str(summary_path.resolve())
            }
        ]
    }


@essential_commands_mcp.tool
def slice_track_data(
    slice_start: Annotated[int, "Start position for slicing"] = 2,
    slice_end: Annotated[int, "End position for slicing"] = 4,
    use_interval: Annotated[bool, "Use interval-based slicing instead of position"] = False,
    out_prefix: Annotated[Optional[str], "Output file prefix"] = None,
) -> Dict[str, Any]:
    """
    Slice track data by position or genomic interval to extract specific regions.
    """
    if out_prefix is None:
        out_prefix = f"slice_{timestamp}"
    
    # Create track data as in tutorial
    values = np.array([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]]).astype(np.float32)
    metadata = pd.DataFrame({
        'name': ['track1', 'track1', 'track2'],
        'strand': ['+', '-', '.'],
    })
    
    interval = genome.Interval(chromosome='chr1', start=1000, end=1004)
    tdata = track_data.TrackData(
        values=values,
        metadata=metadata,
        resolution=1,
        interval=interval
    )
    
    # Slice the data
    if use_interval:
        # Use interval-based slicing
        slice_interval = genome.Interval(
            chromosome='chr1',
            start=1000 + slice_start,
            end=1000 + slice_end
        )
        sliced = tdata.slice_by_interval(slice_interval)
        method = "interval"
    else:
        # Use position-based slicing
        sliced = tdata.slice_by_positions(start=slice_start, end=slice_end)
        method = "position"
    
    # Save original and sliced data
    original_df = pd.DataFrame(values, columns=[f'track_{i}' for i in range(values.shape[1])])
    original_path = OUTPUT_DIR / f"{out_prefix}_original.csv"
    original_df.to_csv(original_path, index=False)
    
    sliced_df = pd.DataFrame(
        sliced.values,
        columns=[f'track_{i}' for i in range(sliced.values.shape[1])]
    )
    sliced_path = OUTPUT_DIR / f"{out_prefix}_sliced.csv"
    sliced_df.to_csv(sliced_path, index=False)
    
    # Summary
    summary_df = pd.DataFrame([{
        'slice_method': method,
        'slice_start': slice_start,
        'slice_end': slice_end,
        'original_shape': str(values.shape),
        'sliced_shape': str(sliced.values.shape)
    }])
    summary_path = OUTPUT_DIR / f"{out_prefix}_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    
    return {
        "message": f"Sliced data from positions {slice_start} to {slice_end}",
        "artifacts": [
            {
                "description": "Original track data",
                "path": str(original_path.resolve())
            },
            {
                "description": "Sliced track data",
                "path": str(sliced_path.resolve())
            },
            {
                "description": "Slice summary",
                "path": str(summary_path.resolve())
            }
        ]
    }


@essential_commands_mcp.tool
def select_tracks(
    track_names: Annotated[str, "Track name to select (e.g., 'track1')"] = "track1",
    out_prefix: Annotated[Optional[str], "Output file prefix"] = None,
) -> Dict[str, Any]:
    """
    Select and reorder specific tracks by name from track data.
    """
    if out_prefix is None:
        out_prefix = f"select_tracks_{timestamp}"
    
    # Create track data as in tutorial
    values = np.array([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]]).astype(np.float32)
    metadata = pd.DataFrame({
        'name': ['track1', 'track1', 'track2'],
        'strand': ['+', '-', '.'],
    })
    
    interval = genome.Interval(chromosome='chr1', start=1000, end=1004)
    tdata = track_data.TrackData(
        values=values,
        metadata=metadata,
        resolution=1,
        interval=interval
    )
    
    # Select tracks by name
    selected = tdata.select_tracks_by_name(names=track_names)
    
    # Save original and selected data
    original_df = pd.DataFrame(values, columns=[f'track_{i}' for i in range(values.shape[1])])
    original_path = OUTPUT_DIR / f"{out_prefix}_original.csv"
    original_df.to_csv(original_path, index=False)
    
    selected_df = pd.DataFrame(
        selected.values,
        columns=[f'track_{i}' for i in range(selected.values.shape[1])]
    )
    selected_path = OUTPUT_DIR / f"{out_prefix}_selected.csv"
    selected_df.to_csv(selected_path, index=False)
    
    # Save metadata
    metadata_path = OUTPUT_DIR / f"{out_prefix}_metadata.csv"
    selected.metadata.to_csv(metadata_path, index=False)
    
    # Summary
    summary_df = pd.DataFrame([{
        'selected_track': track_names,
        'original_shape': str(values.shape),
        'selected_shape': str(selected.values.shape),
        'selected_track_names': ', '.join(selected.metadata.name.values)
    }])
    summary_path = OUTPUT_DIR / f"{out_prefix}_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    
    return {
        "message": f"Selected tracks: {', '.join(selected.metadata.name.values)}",
        "artifacts": [
            {
                "description": "Original track data",
                "path": str(original_path.resolve())
            },
            {
                "description": "Selected track data",
                "path": str(selected_path.resolve())
            },
            {
                "description": "Selected track metadata",
                "path": str(metadata_path.resolve())
            },
            {
                "description": "Selection summary",
                "path": str(summary_path.resolve())
            }
        ]
    }


@essential_commands_mcp.tool
def reverse_complement_tracks(
    strand: Annotated[str, "Strand orientation: '+' or '-'"] = "+",
    out_prefix: Annotated[Optional[str], "Output file prefix"] = None,
) -> Dict[str, Any]:
    """
    Reverse complement track values in a strand-aware manner for DNA sequence analysis.
    """
    if out_prefix is None:
        out_prefix = f"reverse_complement_{timestamp}"
    
    # Create track data with strand information as in tutorial
    values = np.array([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]]).astype(np.float32)
    metadata = pd.DataFrame({
        'name': ['track1', 'track1', 'track2'],
        'strand': ['+', '-', '.'],
    })
    
    interval = genome.Interval(
        chromosome='chr1',
        start=1000,
        end=1004,
        strand=strand
    )
    
    tdata = track_data.TrackData(
        values=values,
        metadata=metadata,
        resolution=1,
        interval=interval
    )
    
    # Reverse complement
    rc_tdata = tdata.reverse_complement()
    
    # Save original and reverse complement data
    original_df = pd.DataFrame(values, columns=[f'track_{i}' for i in range(values.shape[1])])
    original_path = OUTPUT_DIR / f"{out_prefix}_original.csv"
    original_df.to_csv(original_path, index=False)
    
    rc_df = pd.DataFrame(
        rc_tdata.values,
        columns=[f'track_{i}' for i in range(rc_tdata.values.shape[1])]
    )
    rc_path = OUTPUT_DIR / f"{out_prefix}_reverse_complement.csv"
    rc_df.to_csv(rc_path, index=False)
    
    # Summary
    summary_df = pd.DataFrame([{
        'interval_strand': strand,
        'original_shape': str(values.shape),
        'rc_shape': str(rc_tdata.values.shape),
        'transformation': 'reverse_complement'
    }])
    summary_path = OUTPUT_DIR / f"{out_prefix}_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    
    return {
        "message": f"Reverse complemented tracks for {strand} strand interval",
        "artifacts": [
            {
                "description": "Original track data",
                "path": str(original_path.resolve())
            },
            {
                "description": "Reverse complement track data",
                "path": str(rc_path.resolve())
            },
            {
                "description": "Transformation summary",
                "path": str(summary_path.resolve())
            }
        ]
    }