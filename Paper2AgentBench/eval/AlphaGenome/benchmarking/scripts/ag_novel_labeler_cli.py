#!/usr/bin/env python3
"""
AG Novel Labeler CLI - Command-line executable script

This script extracts all questions and answers from the AG novel benchmarking
and outputs them in CSV format with additional columns for agent responses,
grading, and comments.
"""

import os
import sys
import argparse
from datetime import datetime
from io import StringIO
from tqdm import tqdm
import pandas as pd
import contextlib

from alphagenome.data import genome
from alphagenome.interpretation import ism
from alphagenome.models import dna_client
from alphagenome.models import variant_scorers
import numpy as np

from dotenv import load_dotenv

load_dotenv(".env")


@contextlib.contextmanager
def safe_question_block(name):
    """
    Context manager to safely execute a question block.
    Prints status and catches exceptions to prevent script termination.
    """
    print(f"Starting {name}...", flush=True)
    try:
        yield
        print(f"Finished {name}", flush=True)
    except Exception as e:
        print(f"Warning: {name} failed: {e}", file=sys.stderr)


def get_ground_truth_labels_novel_ag():
    """
    Extract all questions and answers from the AG novel benchmarking.
    Returns a list of dictionaries with question data.
    """
    questions = []

    # Initialize DNA model
    dna_model = dna_client.create(os.getenv("ALPHAGENOME_API_KEY"))

    with safe_question_block("Q1"):
        # Q1: Make RNA-seq and CAGE predictions for sequence 'ATCGATCG' (padded to
        # 16384 length) for heart (UBERON:0000948) and liver (UBERON:0002107) tissues.
        # What is the nonzero_mean value for heart tissue in the RNA-seq metadata for
        # polyA plus and positive strand?
        q1_scores = dna_model.predict_sequence(
            sequence="ATCGATCG".center(16384, "N"),  # Pad to valid sequence length.
            requested_outputs=[
                dna_client.OutputType.RNA_SEQ,
                dna_client.OutputType.CAGE,
            ],
            ontology_terms=["UBERON:0000948", "UBERON:0002107"],
        )
        q1_answer = q1_scores.rna_seq.metadata
        q1_answer = q1_answer[q1_answer["name"] == "UBERON:0000948 polyA plus RNA-seq"]
        q1_answer = q1_answer[q1_answer["strand"] == "+"]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/quick_start.ipynb",
                "type": "novel",
                "question": "Make RNA-seq and CAGE predictions for sequence 'ATCGATCG' (padded to 16384 length) for heart (UBERON:0000948) and liver (UBERON:0002107) tissues. What is the nonzero_mean value for heart tissue in the RNA-seq metadata for polyA plus and positive strand?",
                "answer": q1_answer.nonzero_mean.values[0],
            }
        )

    with safe_question_block("Q2"):
        # Q2: Create intervals chr7:1500000-1500050 and chr7:1500025-1500075 and find
        # their intersection. What is the width of the intersected interval?
        interval1 = genome.Interval(chromosome="chr7", start=1500000, end=1500050)
        interval2 = genome.Interval(chromosome="chr7", start=1500025, end=1500075)
        interval_intersect = interval1.intersect(interval2)
        q2_answer = interval_intersect.width

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/essential_commands.ipynb",
                "type": "novel",
                "question": "Create intervals chr7:1500000-1500050 and chr7:1500025-1500075 and find their intersection. What is the width of the intersected interval?",
                "answer": q2_answer,
            }
        )

    with safe_question_block("Q3"):
        # Q3: Score variant chr10:12345678:G>A using DNASE predictions for hepatocytes
        # (CL:0000182). What is the quantile_score for this cell type?
        sequence_length = "1MB"
        sequence_length = dna_client.SUPPORTED_SEQUENCE_LENGTHS[
            f"SEQUENCE_LENGTH_{sequence_length}"
        ]
        variant = genome.Variant(
            chromosome="chr10",
            position=12345678,
            reference_bases="G",
            alternate_bases="A",
            name="chr10:12345678:G>A",
        )
        interval = variant.reference_interval.resize(sequence_length)
        variant_scores = dna_model.score_variant(
            interval=interval,
            variant=variant,
            variant_scorers=[variant_scorers.RECOMMENDED_VARIANT_SCORERS["DNASE"]],
            organism=dna_client.Organism.HOMO_SAPIENS,
        )
        df_scores = variant_scorers.tidy_scores(variant_scores)
        q3_answer = df_scores[df_scores["ontology_curie"] == "CL:0000182"]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/batch_variant_scoring.ipynb",
                "type": "novel",
                "question": "Score variant chr10:12345678:G>A using DNASE predictions for hepatocytes (CL:0000182). What is the quantile_score for this cell type?",
                "answer": q3_answer.quantile_score.values[0],
            }
        )

    with safe_question_block("Q4"):
        # Q4: Create a VCF with variants chr1:1000000:A>T, chr2:2000000:C>G,
        # chr3:3000000:T>A. Score using 500KB sequence length with RNA-seq and ATAC
        # scorers. How many total scoring results are generated?
        vcf_file = """variant_id\tCHROM\tPOS\tREF\tALT
chr1_1000000_A_T\tchr1\t1000000\tA\tT
chr2_2000000_C_G\tchr2\t2000000\tC\tG
chr3_3000000_T_A\tchr3\t3000000\tT\tA
"""
        vcf = pd.read_csv(StringIO(vcf_file), sep="\t")
        sequence_length = "500KB"
        sequence_length = dna_client.SUPPORTED_SEQUENCE_LENGTHS[
            f"SEQUENCE_LENGTH_{sequence_length}"
        ]
        results = []

        for i, vcf_row in tqdm(vcf.iterrows(), total=len(vcf)):
            variant = genome.Variant(
                chromosome=str(vcf_row.CHROM),
                position=int(vcf_row.POS),
                reference_bases=vcf_row.REF,
                alternate_bases=vcf_row.ALT,
                name=vcf_row.variant_id,
            )
            interval = variant.reference_interval.resize(sequence_length)

            variant_scores = dna_model.score_variant(
                interval=interval,
                variant=variant,
                variant_scorers=[
                    variant_scorers.RECOMMENDED_VARIANT_SCORERS["RNA_SEQ"],
                    variant_scorers.RECOMMENDED_VARIANT_SCORERS["ATAC"],
                ],
                organism=dna_client.Organism.HOMO_SAPIENS,
            )
            results.append(variant_scores)

        q4_scores = variant_scorers.tidy_scores(results)

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/batch_variant_scoring.ipynb",
                "type": "novel",
                "question": "Create a VCF with variants chr1:1000000:A>T, chr2:2000000:C>G, chr3:3000000:T>A. Score using 500KB sequence length with RNA-seq and ATAC scorers. How many total scoring results are generated?",
                "answer": q4_scores.shape[0],
            }
        )

    with safe_question_block("Q5"):
        # Q5: Score variant chr15:75000000:C>T using PRO-cap predictions for
        # neural stem cells (CL:0000047). What is the raw_score for this cell type?
        sequence_length = "1MB"
        sequence_length = dna_client.SUPPORTED_SEQUENCE_LENGTHS[
            f"SEQUENCE_LENGTH_{sequence_length}"
        ]
        variant = genome.Variant(
            chromosome="chr15",
            position=75000000,
            reference_bases="C",
            alternate_bases="T",
            name="chr15:75000000:C>T",
        )
        interval = variant.reference_interval.resize(sequence_length)
        variant_scores = dna_model.score_variant(
            interval=interval,
            variant=variant,
            variant_scorers=[variant_scorers.RECOMMENDED_VARIANT_SCORERS["PROCAP"]],
            organism=dna_client.Organism.HOMO_SAPIENS,
        )
        df_scores = variant_scorers.tidy_scores(variant_scores)
        q5_answer = df_scores[df_scores["ontology_curie"] == "CL:0000047"]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/variant_scoring_ui.ipynb",
                "type": "novel",
                "question": "Score variant chr15:75000000:C>T using PRO-cap predictions for neural stem cells (CL:0000047). What is the raw_score for this cell type?",
                "answer": q5_answer.raw_score.values,
            }
        )

    with safe_question_block("Q6"):
        # Q6: Analyze variant chr9:98765432:T>C with CAGE predictions for muscle cells (CL:0000187).
        # What is the quantile_score specifically for cell type CL:0000187?
        sequence_length = "1MB"
        sequence_length = dna_client.SUPPORTED_SEQUENCE_LENGTHS[
            f"SEQUENCE_LENGTH_{sequence_length}"
        ]
        variant = genome.Variant(
            chromosome="chr9",
            position=98765432,
            reference_bases="T",
            alternate_bases="C",
            name="chr9:98765432:T>C",
        )
        interval = variant.reference_interval.resize(sequence_length)
        variant_scores = dna_model.score_variant(
            interval=interval,
            variant=variant,
            variant_scorers=[variant_scorers.RECOMMENDED_VARIANT_SCORERS["CAGE"]],
            organism=dna_client.Organism.HOMO_SAPIENS,
        )
        df_scores = variant_scorers.tidy_scores(variant_scores)
        q6_answer = df_scores[df_scores["ontology_curie"] == "CL:0000187"]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/variant_scoring_ui.ipynb",
                "type": "novel",
                "question": "Analyze variant chr9:98765432:T>C with CAGE predictions for muscle cells (CL:0000187). What is the quantile_score specifically for cell type CL:0000187?",
                "answer": q6_answer.quantile_score.values,
            }
        )

    with safe_question_block("Q7"):
        # Q7: Analyze gene expression (RNA-Seq) metadata for heart around the
        # APOL4 gene (chr22:36150498:36252898). What is the nonzero_mean value for
        # RNA-Seq (polyA plus, unstranded) in heart (UBERON:0000948)?
        interval = genome.Interval("chr22", 36_150_498, 36_252_898).resize(
            dna_client.SEQUENCE_LENGTH_1MB
        )
        output = dna_model.predict_interval(
            interval,
            requested_outputs={
                dna_client.OutputType.RNA_SEQ,
            },
            ontology_terms=["UBERON:0000948"],
        )
        rna_out = output.rna_seq.metadata
        q7_answer = rna_out.query("name.str.contains('polyA plus') and strand == '.'")

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/visualization_modality_tour.ipynb",
                "type": "novel",
                "question": "Analyze gene expression (RNA-Seq) metadata for heart around the APOL4 gene (chr22:36150498:36252898). What is the nonzero_mean value for RNA-Seq (polyA plus, unstranded) in heart (UBERON:0000948)?",
                "answer": q7_answer.nonzero_mean.values[0],
            }
        )

    with safe_question_block("Q8"):
        # Q8: Analyze histone ChIP-seq metadata for heart around the
        # APOL4 gene (chr22:36150498:36252898). What is the nonzero_mean value for
        # H3K4me3 in heart (UBERON:0000948)?
        interval = genome.Interval("chr22", 36_150_498, 36_252_898).resize(
            dna_client.SEQUENCE_LENGTH_1MB
        )
        output = dna_model.predict_interval(
            interval,
            requested_outputs={
                dna_client.OutputType.CHIP_HISTONE,
            },
            ontology_terms=["UBERON:0000948"],
        )
        output_chip = output.chip_histone.metadata
        q8_answer = output_chip.query("name.str.contains('H3K4me3')")

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/visualization_modality_tour.ipynb",
                "type": "novel",
                "question": "Analyze histone ChIP-seq metadata for heart around the APOL4 gene (chr22:36150498:36252898). What is the nonzero_mean value for H3K4me3 in heart (UBERON:0000948)?",
                "answer": q8_answer.nonzero_mean.values[0],
            }
        )

    with safe_question_block("Q9"):
        # Q9: Score variant chr15:75000000:C>T using PRO-cap predictions for
        # K562 cells (EFO:0002067). What is the raw_score for this cell type?
        sequence_length = "1MB"
        sequence_length = dna_client.SUPPORTED_SEQUENCE_LENGTHS[
            f"SEQUENCE_LENGTH_{sequence_length}"
        ]
        variant = genome.Variant(
            chromosome="chr15",
            position=75000000,
            reference_bases="C",
            alternate_bases="T",
            name="chr15:75000000:C>T",
        )
        interval = variant.reference_interval.resize(sequence_length)
        variant_scores = dna_model.score_variant(
            interval=interval,
            variant=variant,
            variant_scorers=[variant_scorers.RECOMMENDED_VARIANT_SCORERS["PROCAP"]],
            organism=dna_client.Organism.HOMO_SAPIENS,
        )
        df_scores = variant_scorers.tidy_scores(variant_scores)
        q9_answer = df_scores[df_scores["ontology_curie"] == "EFO:0002067"]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/variant_scoring_ui.ipynb",
                "type": "novel",
                "question": "Score variant chr15:75000000:C>T using PRO-cap predictions for K562 cells (EFO:0002067). What is the raw_score for this cell type?",
                "answer": q9_answer.raw_score.values[0],
            }
        )

    with safe_question_block("Q10"):
        # Q10: Analyze variant chr9:98765432:T>C with DNASE predictions for muscle cells
        # (CL:0000187). What is the quantile_score for muscle tissue?
        sequence_length = "1MB"
        sequence_length = dna_client.SUPPORTED_SEQUENCE_LENGTHS[
            f"SEQUENCE_LENGTH_{sequence_length}"
        ]
        variant = genome.Variant(
            chromosome="chr9",
            position=98765432,
            reference_bases="T",
            alternate_bases="C",
            name="chr9:98765432:T>C",
        )
        interval = variant.reference_interval.resize(sequence_length)
        variant_scores = dna_model.score_variant(
            interval=interval,
            variant=variant,
            variant_scorers=[variant_scorers.RECOMMENDED_VARIANT_SCORERS["DNASE"]],
            organism=dna_client.Organism.HOMO_SAPIENS,
        )
        df_scores = variant_scorers.tidy_scores(variant_scores)
        q10_answer = df_scores[df_scores["ontology_curie"] == "CL:0000187"]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/variant_scoring_ui.ipynb",
                "type": "novel",
                "question": "Analyze variant chr9:98765432:T>C with DNASE predictions for muscle cells (CL:0000187). What is the quantile_score for muscle tissue?",
                "answer": q10_answer.quantile_score.values[0],
            }
        )

    with safe_question_block("Q11"):
        # Q11: Analyze histone ChIP-seq metadata for neuronal stem cells.
        # What is the nonzero_mean value for H3K4me3 in neuronal stem cells
        # (CL:0000100)?
        output_metadata = dna_model.output_metadata(organism=dna_client.Organism.HOMO_SAPIENS)
        q11_answer = output_metadata.chip_histone[
            (output_metadata.chip_histone["ontology_curie"] == "CL:0000100")
            & (output_metadata.chip_histone["name"] == "CL:0000100 Histone ChIP-seq H3K4me3")
        ]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/visualization_modality_tour.ipynb",
                "type": "novel",
                "question": "Analyze histone ChIP-seq metadata for neuronal stem cells. What is the nonzero_mean value for H3K4me3 in neuronal stem cells (CL:0000100)?",
                "answer": q11_answer.nonzero_mean.values[0],
            }
        )

    with safe_question_block("Q12"):
        # Q12: Examine histone modifications in lung (UBERON:0002048).
        # What is the highest nonzero_mean value among H3K27ac predictions for lung?
        q12_answer = output_metadata.chip_histone[
            (output_metadata.chip_histone["ontology_curie"] == "UBERON:0002048")
            & (output_metadata.chip_histone["name"] == "UBERON:0002048 Histone ChIP-seq H3K27ac")
        ]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/visualization_modality_tour.ipynb",
                "type": "novel",
                "question": "Examine histone modifications in lung (UBERON:0002048). What is the highest nonzero_mean value among H3K27ac predictions?",
                "answer": q12_answer.nonzero_mean.max(),
            }
        )

    with safe_question_block("Q13"):
        # Q13: Make CAGE and DNASE predictions for sequence 'GATTACA'
        # (padded to 16384 length) for lung (UBERON:0002048) and brain (UBERON:0000955)
        # tissues. What is the nonzero_mean value for lung tissue in the DNASE metadata?
        q13_scores = dna_model.predict_sequence(
            sequence="GATTACA".center(16384, "N"),  # Pad to valid sequence length.
            requested_outputs=[
                dna_client.OutputType.DNASE,
                dna_client.OutputType.CAGE,
            ],
            ontology_terms=["UBERON:0002048", "UBERON:0000955"],
        )
        q13_answer = q13_scores.dnase.metadata
        q13_answer = q13_answer[q13_answer["name"] == "UBERON:0002048 DNase-seq"]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/quick_start.ipynb",
                "type": "novel",
                "question": "Make CAGE and DNASE predictions for sequence 'GATTACA' (padded to 16384 length) for lung (UBERON:0002048) and brain (UBERON:0000955) tissues. What is the nonzero_mean value for lung tissue in the DNASE metadata?",
                "answer": q13_answer.nonzero_mean.values[0],
            }
        )

    with safe_question_block("Q14"):
        # Q14: Score variant chr10:67394738:A>T using RNA-seq predictions for heart
        # (UBERON:0000948). What is the quantile_score for this cell type for polyA plus on
        # the positive strand for gene SIRT1?
        sequence_length = "1MB"
        sequence_length = dna_client.SUPPORTED_SEQUENCE_LENGTHS[
            f"SEQUENCE_LENGTH_{sequence_length}"
        ]
        variant = genome.Variant(
            chromosome="chr10",
            position=67394738,
            reference_bases="A",
            alternate_bases="T",
            name="chr10:67394738:A>T",
        )
        interval = variant.reference_interval.resize(sequence_length)
        variant_scores = dna_model.score_variant(
            interval=interval,
            variant=variant,
            variant_scorers=[variant_scorers.RECOMMENDED_VARIANT_SCORERS["RNA_SEQ"]],
            organism=dna_client.Organism.HOMO_SAPIENS,
        )
        df_scores = variant_scorers.tidy_scores(variant_scores)
        q14_answer = df_scores[
            (df_scores["ontology_curie"] == "UBERON:0000948")
            & (df_scores["gene_name"] == "SIRT1")
            & (df_scores["track_name"].str.contains("polyA plus"))
            & (df_scores["track_strand"] == "+")
        ]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/batch_variant_scoring.ipynb",
                "type": "novel",
                "question": "Score variant chr10:67394738:A>T using RNA-seq predictions for heart (UBERON:0000948). What is the quantile_score for this cell type for polyA plus on the positive strand for gene SIRT1?",
                "answer": q14_answer.quantile_score.values[0],
            }
        )

    with safe_question_block("Q15"):
        # Q15: Score variant chr19:8134523:G>A using ATAC-seq predictions for
        # lung (UBERON:0002048). What is the quantile_score for this cell type?
        sequence_length = "1MB"
        sequence_length = dna_client.SUPPORTED_SEQUENCE_LENGTHS[
            f"SEQUENCE_LENGTH_{sequence_length}"
        ]
        variant = genome.Variant(
            chromosome="chr19",
            position=8134523,
            reference_bases="G",
            alternate_bases="A",
            name="chr19:8134523:G>A",
        )
        interval = variant.reference_interval.resize(sequence_length)
        variant_scores = dna_model.score_variant(
            interval=interval,
            variant=variant,
            variant_scorers=[variant_scorers.RECOMMENDED_VARIANT_SCORERS["ATAC"]],
            organism=dna_client.Organism.HOMO_SAPIENS,
        )
        df_scores = variant_scorers.tidy_scores(variant_scores)
        q15_answer = df_scores[(df_scores["ontology_curie"] == "UBERON:0002048")]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/batch_variant_scoring.ipynb",
                "type": "novel",
                "question": "Score variant chr19:8134523:G>A using ATAC-seq predictions for lung (UBERON:0002048). What is the quantile_score for this cell type?",
                "answer": q15_answer.quantile_score.values[0],
            }
        )

    return questions


def main():
    """Main function to run the CLI script."""
    parser = argparse.ArgumentParser(
        description="Generate AG novel benchmarking CSV with questions and answers"
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output CSV file path (default: ag_novel_benchmark_YYYY-MM-DD.csv in AlphaGenome/benchmarking/data/)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    if args.verbose:
        print("Starting AG novel benchmarking data generation...")

    try:
        # Get questions and answers
        qas = get_ground_truth_labels_novel_ag()

        # Create DataFrame with additional columns
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Set default output path if not provided
        if args.output is None:
            # Get the script directory and navigate to the data directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(script_dir, "..", "data")
            data_dir = os.path.abspath(data_dir)

            # Create filename with date
            filename = f"ag_novel_benchmark_{current_date}.csv"
            args.output = os.path.join(data_dir, filename)

        df_data = []
        for qa in qas:
            df_data.append(
                {
                    "repo": qa["repo"],
                    "path": qa["path"],
                    "type": qa["type"],
                    "question": qa["question"],
                    "answer": qa["answer"],
                    "run_date": current_date,
                    "agent_response": "",  # Empty column for agent responses
                    "grade": "",  # Empty column for grades
                    "grade_comments": "",  # Empty column for grade comments
                }
            )

        df = pd.DataFrame(df_data)

        # Save to CSV
        df.to_csv(args.output, index=False)

        if args.verbose:
            print(f"Successfully generated {len(qas)} questions")
            print(f"Output saved to: {args.output}")
        else:
            print(f"Generated {args.output} with {len(qas)} questions")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
