#!/usr/bin/env python3
"""
AG Tutorial Labeler CLI - Command-line executable script

This script extracts all questions and answers from the AG tutorial benchmarking
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


def get_ground_truth_labels_tutorial_ag():
    """
    Extract all questions and answers from the AG tutorial benchmarking.
    Returns a list of dictionaries with question data.
    """
    questions = []

    # Initialize DNA model
    dna_model = dna_client.create(os.getenv("ALPHAGENOME_API_KEY"))

    with safe_question_block("Q1"):
        # Q1: Create a variant at chr22:36201698 with reference base 'A' and alternate base 'C'.
        # Predict its effect on RNA-seq in Colon - Transverse tissue (UBERON:0001157) using a
        # 1MB interval. Which gene shows the most visible expression change?
        variant = genome.Variant(
            chromosome="chr22", position=36201698, reference_bases="A", alternate_bases="C"
        )
        interval = variant.reference_interval.resize(dna_client.SEQUENCE_LENGTH_1MB)
        variant_scorer = variant_scorers.RECOMMENDED_VARIANT_SCORERS["RNA_SEQ"]
        variant_scores = dna_model.score_variant(
            interval=interval, variant=variant, variant_scorers=[variant_scorer]
        )
        q1_scores = variant_scorers.tidy_scores([variant_scores], match_gene_strand=True)
        q1_answer = q1_scores[q1_scores["ontology_curie"] == "UBERON:0001157"]
        q1_answer = q1_answer.loc[q1_answer["quantile_score"].abs().idxmax()]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/quick_start.ipynb",
                "type": "tutorial",
                "question": "Create a variant at chr22:36201698 with reference base 'A' and alternate base 'C'. Predict its effect on RNA-seq in Colon - Transverse tissue (UBERON:0001157) using a 1MB interval. Which gene shows the most visible expression change?",
                "answer": q1_answer.gene_name,
            }
        )

    with safe_question_block("Q2"):
        # Q2: Make CAGE and DNASE predictions for sequence 'GATTACA' (padded to 16384 length) for
        # lung (UBERON:0002048) and brain (UBERON:0000955) tissues. What is the nonzero_mean value for
        # brain tissue in the CAGE metadata?
        q2_scores = dna_model.predict_sequence(
            sequence="GATTACA".center(16384, "N"),  # Pad to valid sequence length.
            requested_outputs=[
                dna_client.OutputType.DNASE,
                dna_client.OutputType.CAGE,
            ],
            ontology_terms=["UBERON:0002048", "UBERON:0000955"],
        )
        q2_answer = q2_scores.cage.metadata
        q2_answer = q2_answer[q2_answer["name"] == "hCAGE UBERON:0000955"]
        q2_answer = q2_answer[q2_answer["strand"] == "+"]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/quick_start.ipynb",
                "type": "tutorial",
                "question": "Make CAGE and DNASE predictions for sequence 'GATTACA' (padded to 16384 length) for lung (UBERON:0002048) and brain (UBERON:0000955) tissues. What is the nonzero_mean value for brain tissue in the CAGE metadata?",
                "answer": q2_answer.nonzero_mean.values[0],
            }
        )

    with safe_question_block("Q3"):
        # Q3: Make DNase-seq predictions for sequence 'GATTACA' (padded to 16384 length) for lung tissue
        # (UBERON:0002048). What is the nonzero_mean value in the dnase metadata?
        q3_answer = q2_scores.dnase.metadata
        q3_answer = q3_answer[q3_answer["name"] == "UBERON:0002048 DNase-seq"]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/quick_start.ipynb",
                "type": "tutorial",
                "question": "Make DNase-seq predictions for sequence 'GATTACA' (padded to 16384 length) for lung tissue (UBERON:0002048). What is the nonzero_mean value in the dnase metadata?",
                "answer": q3_answer.nonzero_mean.values[0],
            }
        )

    with safe_question_block("Q4"):
        # Q4: Score variant chr22:36201698:A>C using the recommended RNA_SEQ variant scorer. What is
        # the quantile score for the RBFOX2 gene in neuronal stem cell?
        sequence_length = "1MB"
        sequence_length = dna_client.SUPPORTED_SEQUENCE_LENGTHS[
            f"SEQUENCE_LENGTH_{sequence_length}"
        ]
        variant = genome.Variant(
            chromosome="chr22",
            position=36201698,
            reference_bases="A",
            alternate_bases="C",
            name="chr22:36201698:A>C",
        )
        interval = variant.reference_interval.resize(sequence_length)
        variant_scores = dna_model.score_variant(
            interval=interval,
            variant=variant,
            variant_scorers=[variant_scorers.RECOMMENDED_VARIANT_SCORERS["RNA_SEQ"]],
            organism=dna_client.Organism.HOMO_SAPIENS,
        )
        df_scores = variant_scorers.tidy_scores(variant_scores)
        q4_answer = df_scores[
            (df_scores["ontology_curie"] == "CL:0000047") & (df_scores["gene_name"] == "RBFOX2")
        ]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/quick_start.ipynb",
                "type": "tutorial",
                "question": "Score variant chr22:36201698:A>C using the recommended RNA_SEQ variant scorer. What is the quantile score for the RBFOX2 gene in neuronal stem cell?",
                "answer": q4_answer.quantile_score.values[0],
            }
        )

    with safe_question_block("Q5"):
        # Q5: Perform in silico mutagenesis on a 256-base region within chr20:3753000-3753400 using a
        # 16KB context window. Score variants using DNase accessibility with 501bp width and difference
        # mean aggregation. How many total variants are scored?
        sequence_interval = genome.Interval("chr20", 3_753_000, 3_753_400)
        sequence_interval = sequence_interval.resize(dna_client.SEQUENCE_LENGTH_16KB)
        ism_interval = sequence_interval.resize(256)
        dnase_variant_scorer = variant_scorers.CenterMaskScorer(
            requested_output=dna_client.OutputType.DNASE,
            width=501,
            aggregation_type=variant_scorers.AggregationType.DIFF_MEAN,
        )
        variant_scores = dna_model.score_ism_variants(
            interval=sequence_interval,
            ism_interval=ism_interval,
            variant_scorers=[dnase_variant_scorer],
        )

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/quick_start.ipynb",
                "type": "tutorial",
                "question": "Perform in silico mutagenesis on a 256-base region within chr20:3753000-3753400 using a 16KB context window. Score variants using DNase accessibility with 501bp width and difference mean aggregation. How many total variants are scored?",
                "answer": len(variant_scores),
            }
        )

    with safe_question_block("Q6"):
        # Q6: Run ISM analysis on chr20 with a 256-base mutagenesis region for DNase predictions.
        # Extract scores for K562 cell line and create a contribution matrix. What are the dimensions
        # of the resulting score matrix?
        def extract_k562(adata):
            values = adata.X[:, adata.var["ontology_curie"] == "EFO:0002067"]
            assert values.size == 1
            return values.flatten()[0]

        ism_result = ism.ism_matrix(
            [extract_k562(x[0]) for x in variant_scores],
            variants=[v[0].uns["variant"] for v in variant_scores],
        )

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/quick_start.ipynb",
                "type": "tutorial",
                "question": "Run ISM analysis on chr20 with a 256-base mutagenesis region for DNase predictions. Extract scores for K562 cell line and create a contribution matrix. What are the dimensions of the resulting score matrix?",
                "answer": str(ism_result.shape),
            }
        )

    with safe_question_block("Q7"):
        # Q7: Score variant chr3:58394738:A>T using ATAC-seq predictions for motor neuron cells (CL:0000100).
        # What is the quantile_score for this cell type?
        vcf_file = """variant_id\tCHROM\tPOS\tREF\tALT
chr3_58394738_A_T_b38\tchr3\t58394738\tA\tT
chr8_28520_G_C_b38\tchr8\t28520\tG\tC
chr16_636337_G_A_b38\tchr16\t636337\tG\tA
chr16_1135446_G_T_b38\tchr16\t1135446\tG\tT
"""
        vcf = pd.read_csv(StringIO(vcf_file), sep="\t")
        required_columns = ["variant_id", "CHROM", "POS", "REF", "ALT"]
        for column in required_columns:
            if column not in vcf.columns:
                raise ValueError(f"VCF file is missing required column: {column}.")
        organism = "human"
        sequence_length = "1MB"
        sequence_length = dna_client.SUPPORTED_SEQUENCE_LENGTHS[
            f"SEQUENCE_LENGTH_{sequence_length}"
        ]
        score_rna_seq = True
        score_cage = True
        score_procap = True
        score_atac = True
        score_dnase = True
        score_chip_histone = True
        score_chip_tf = True
        score_polyadenylation = True
        score_splice_sites = True
        score_splice_site_usage = True
        score_splice_junctions = True
        organism_map = {
            "human": dna_client.Organism.HOMO_SAPIENS,
            "mouse": dna_client.Organism.MUS_MUSCULUS,
        }
        organism = organism_map[organism]
        scorer_selections = {
            "rna_seq": score_rna_seq,
            "cage": score_cage,
            "procap": score_procap,
            "atac": score_atac,
            "dnase": score_dnase,
            "chip_histone": score_chip_histone,
            "chip_tf": score_chip_tf,
            "polyadenylation": score_polyadenylation,
            "splice_sites": score_splice_sites,
            "splice_site_usage": score_splice_site_usage,
            "splice_junctions": score_splice_junctions,
        }
        all_scorers = variant_scorers.RECOMMENDED_VARIANT_SCORERS
        selected_scorers = [
            all_scorers[key] for key in all_scorers if scorer_selections.get(key.lower(), False)
        ]
        unsupported_scorers = [
            scorer
            for scorer in selected_scorers
            if (
                organism.value
                not in variant_scorers.SUPPORTED_ORGANISMS[scorer.base_variant_scorer]
            )
            | (
                (scorer.requested_output == dna_client.OutputType.PROCAP)
                & (organism == dna_client.Organism.MUS_MUSCULUS)
            )
        ]
        if len(unsupported_scorers) > 0:
            print(
                f"Excluding {unsupported_scorers} scorers as they are not supported for {organism}."
            )
            for unsupported_scorer in unsupported_scorers:
                selected_scorers.remove(unsupported_scorer)

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
                variant_scorers=selected_scorers,
                organism=organism,
            )
            results.append(variant_scores)
        df_scores = variant_scorers.tidy_scores(results)
        df_scores["variant_id"] = [str(var_id) for var_id in df_scores["variant_id"]]
        q7_answer = df_scores[
            (df_scores["variant_id"] == "chr3:58394738:A>T")
            & (df_scores["ontology_curie"] == "CL:0000100")
            & (df_scores["track_name"] == "CL:0000100 ATAC-seq")
        ]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/batch_variant_scoring.ipynb",
                "type": "tutorial",
                "question": "Score variant chr3:58394738:A>T using ATAC-seq predictions for motor neuron cells (CL:0000100). What is the quantile_score for this cell type?",
                "answer": q7_answer.quantile_score.values[0],
            }
        )

    with safe_question_block("Q8"):
        # Q8: Perform batch variant scoring on chr3:58394738:A>T for natural killer cells (CL:0000623)
        # using ATAC-seq. What is the quantile_score?
        q8_answer = df_scores[
            (df_scores["variant_id"] == "chr3:58394738:A>T")
            & (df_scores["ontology_curie"] == "CL:0000623")
            & (df_scores["track_name"] == "CL:0000623 ATAC-seq")
        ]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/batch_variant_scoring.ipynb",
                "type": "tutorial",
                "question": "Perform batch variant scoring on chr3:58394738:A>T for natural killer cells (CL:0000623) using ATAC-seq. What is the quantile_score?",
                "answer": q8_answer.quantile_score.values[0],
            }
        )

    with safe_question_block("Q9"):
        # Q9: Create a VCF with variants chr3:58394738:A>T, chr8:28520:G>C, chr16:636337:G>A,
        # and chr16:1135446:G>T. Score using 1MB sequence length with all available scorers. How many total
        # scoring results are generated?
        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/batch_variant_scoring.ipynb",
                "type": "tutorial",
                "question": "Create a VCF with variants chr3:58394738:A>T, chr8:28520:G>C, chr16:636337:G>A, and chr16:1135446:G>T. Score using 1MB sequence length with all available scorers. How many total scoring results are generated?",
                "answer": df_scores.shape[0],
            }
        )

    with safe_question_block("Q10"):
        # Q10: Score variant chr16:1135446:G>T using RNA-seq predictions for suprapubic skin tissue
        # (UBERON:0036149). What is the highest quantile_score among the lncRNA genes?
        q10_answer = df_scores[
            (df_scores["variant_id"] == "chr16:1135446:G>T")
            & (df_scores["ontology_curie"] == "UBERON:0036149")
            & (df_scores["gene_type"] == "lncRNA")
        ]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/batch_variant_scoring.ipynb",
                "type": "tutorial",
                "question": "Score variant chr16:1135446:G>T using RNA-seq predictions for suprapubic skin tissue (UBERON:0036149). What is the highest quantile_score among the lncRNA genes?",
                "answer": q10_answer.quantile_score.max(),
            }
        )

    with safe_question_block("Q11"):
        # Q11: Perform batch variant scoring on chr16:1135446:G>T for suprapubic skin tissue using
        # RNA-seq gene mask scorer. What is the quantile_score for gene ENSG00000292431?
        q11_answer = df_scores[
            (df_scores["variant_id"] == "chr16:1135446:G>T")
            & (df_scores["ontology_curie"] == "UBERON:0036149")
            & (df_scores["gene_id"] == "ENSG00000292431")
        ]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/batch_variant_scoring.ipynb",
                "type": "tutorial",
                "question": "Perform batch variant scoring on chr16:1135446:G>T for suprapubic skin tissue using RNA-seq gene mask scorer. What is the quantile_score for gene ENSG00000292431?",
                "answer": q11_answer.quantile_score.values[0],
            }
        )

    with safe_question_block("Q12"):
        # Q12: Score variant chr22:36201698:A>C using the interactive UI with all available scorers.
        # How many total scoring results are generated across all modalities and cell types?
        organism = "human"
        organism_map = {
            "human": dna_client.Organism.HOMO_SAPIENS,
            "mouse": dna_client.Organism.MUS_MUSCULUS,
        }
        organism = organism_map[organism]
        variant_chromosome = "chr22"
        variant_position = 36201698
        variant_reference_bases = "A"
        variant_alternate_bases = "C"
        variant = genome.Variant(
            chromosome=variant_chromosome,
            position=variant_position,
            reference_bases=variant_reference_bases,
            alternate_bases=variant_alternate_bases,
        )
        sequence_length = "1MB"
        sequence_length = dna_client.SUPPORTED_SEQUENCE_LENGTHS[
            f"SEQUENCE_LENGTH_{sequence_length}"
        ]
        interval = variant.reference_interval.resize(sequence_length)
        variant_scores = dna_model.score_variant(
            interval=interval,
            variant=variant,
            variant_scorers=list(variant_scorers.RECOMMENDED_VARIANT_SCORERS.values()),
        )
        df_scores = variant_scorers.tidy_scores(variant_scores)
        df_scores["variant_id"] = [str(var_id) for var_id in df_scores["variant_id"]]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/variant_scoring_ui.ipynb",
                "type": "tutorial",
                "question": "Score variant chr22:36201698:A>C using the interactive UI with all available scorers. How many total scoring results are generated across all modalities and cell types?",
                "answer": df_scores.shape[0],
            }
        )

    with safe_question_block("Q13"):
        # Q13: Score variant chr22:36201698:A>C for T-cells using ATAC-seq predictions (CL:0000084).
        # What is the quantile_score for this cell type?
        q13_answer = df_scores[
            (df_scores["variant_id"] == "chr22:36201698:A>C")
            & (df_scores["ontology_curie"] == "CL:0000084")
            & (df_scores["track_name"] == "CL:0000084 ATAC-seq")
        ]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/variant_scoring_ui.ipynb",
                "type": "tutorial",
                "question": "Score variant chr22:36201698:A>C for T-cells using ATAC-seq predictions (CL:0000084). What is the quantile_score for this cell type?",
                "answer": q13_answer.quantile_score.values[0],
            }
        )

    with safe_question_block("Q14"):
        # Q14: Analyze variant chr22:36201698:A>C with ATAC-seq for B cells (CL:0000236).
        # What is the quantile_score for B cell chromatin accessibility?
        q14_answer = df_scores[
            (df_scores["variant_id"] == "chr22:36201698:A>C")
            & (df_scores["ontology_curie"] == "CL:0000236")
            & (df_scores["track_name"] == "CL:0000236 ATAC-seq")
        ]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/variant_scoring_ui.ipynb",
                "type": "tutorial",
                "question": "Analyze variant chr22:36201698:A>C with ATAC-seq for B cells (CL:0000236). What is the quantile_score for B cell chromatin accessibility?",
                "answer": q14_answer.quantile_score.values[0],
            }
        )

    with safe_question_block("Q15"):
        # Q15: Examine histone modifications in transverse colon tissue (UBERON:0001157).
        # What is the nonzero_mean value among H3K36me3 predictions?
        output_metadata = dna_model.output_metadata(organism=dna_client.Organism.HOMO_SAPIENS)
        q15_answer = output_metadata.chip_histone[
            (output_metadata.chip_histone["ontology_curie"] == "UBERON:0001157")
            & (output_metadata.chip_histone["name"] == "UBERON:0001157 Histone ChIP-seq H3K36me3")
        ]

        questions.append(
            {
                "repo": "https://github.com/google-genomics-alpha/alphagenome",
                "path": "colab/visualization_modality_tour.ipynb",
                "type": "tutorial",
                "question": "Examine histone modifications in transverse colon tissue (UBERON:0001157). What is the nonzero_mean value among H3K36me3 predictions?",
                "answer": q15_answer.nonzero_mean.max(),
            }
        )

    return questions


def main():
    """Main function to run the CLI script."""
    parser = argparse.ArgumentParser(
        description="Generate AG tutorial benchmarking CSV with questions and answers"
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output CSV file path (default: ag_tutorial_benchmark_YYYY-MM-DD.csv in AlphaGenome/benchmarking/data/)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    if args.verbose:
        print("Starting AG tutorial benchmarking data generation...")

    try:
        # Get questions and answers
        qas = get_ground_truth_labels_tutorial_ag()

        # Create DataFrame with additional columns
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Set default output path if not provided
        if args.output is None:
            # Get the script directory and navigate to the data directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(script_dir, "..", "data")
            data_dir = os.path.abspath(data_dir)

            # Create filename with date
            filename = f"ag_tutorial_benchmark_{current_date}.csv"
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
