# protein

- Exploring the Structural Lexicon of the Proteome via Metric Geometry
  Paper: http://biorxiv.org/lookup/doi/10.1101/2025.11.03.686256
  Repo: `GWProt`
  Questions:
  1. Question: Using the GWProt library, load all PDB files from 'GWProt/repo/GWProt/docs/Examples/Example_Data/KRAS Proteins/' directory to create GW_protein objects. How many protein structures are loaded?
     Answer: 54
  2. Question: Using the ligand metadata file at 'GWProt/repo/GWProt/docs/Examples/Example_Data/KRAS Ligands.csv', count how many unique ligand types are present in the KRAS protein dataset. What is the count of unique ligand types?
     Answer: 4
  3. Question: Using GWProt, load all 54 KRAS protein PDB files from 'GWProt/repo/GWProt/docs/Examples/Example_Data/KRAS Proteins/', create an LGD_Comparison object, and compute pairwise GW distances. Then normalize the raw LGD dictionary using normalize_lgd_dict. Define switch regions as residue indices 28-38 and 58-74 (for a protein of 161 residues). Compute the mean average precision (area under precision-recall curve) for predicting switch regions using the normalized LGD values across all proteins. What is the mean average precision value rounded to 4 decimal places?
     Answer: 0.8424

- CrossPPI: A Cross-Fusion Based Model for Protein-Protein Binding Affinity Prediction
  Paper: http://biorxiv.org/lookup/doi/10.1101/2025.11.25.690371
  Repo: `CrossPPI`
  Questions:
  1. Question: Generate per-residue protein embeddings using the ESM-2 model for the KRAS protein sequence 'MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHQYREQIKRVKDSDDVPMVLVGNKCDLAARTVESRQAQDLARSYGIPYIETSAKTRQGVEDAFYTLVREIRQHKLRKLNPPDESGPGCMSCKCVLS' with complex ID 'EMB003', using maximum sequence length of 1000 residues, and save the output to CrossPPI/notebooks/embedding_generator/output/EMB003_bench.npy. What is the mean L2 norm per residue, rounded to 4 decimal places?
     Answer: 9.6298
  2. Question: Generate a binary contact map for the KRAS protein (complex ID: TEST003) with sequence MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHQYREQIKRVKDSDDVPMVLVGNKCDLAARTVESRQAQDLARSYGIPYIETSAKTRQGVEDAFYTLVREIRQHKLRKLNPPDESGPGCMSCKCVLS using the protein contact map generation tool. Use a contact threshold of 0.5, maximum length of 999, and save the output to CrossPPI/notebooks/contact_map_generator/output/TEST003_benchmark.txt. What is the total number of predicted contacts in the binary contact map?
     Answer: 483
  3. Question: Among the three proteins analyzed (TEST001 with 127 residues, TEST002 with 216 residues, and TEST003 with 189 residues), which protein has the highest contact density percentage when using a contact threshold of 0.5? Contact density is calculated as the number of contacts divided by the total matrix size times 100. The sequences are: TEST001 (CDC42 ligand) - MGDKPIWEQIGSSFIQHYYQLFDNDRTQLGAIYIDASCLTWEGQQFQGKAAIVEKLSSLPFQKIQHSITAQDHQPTPDSCIISMVVGQLKADEDPIMGFHQMFLLKNINDAWVCTNDMFRLALHNFG, TEST002 (RAC1 receptor) - MAAQGEPQVQFKLVLVGDGGTGKTTFVKRHLTGEFEKKYVATLGVEVHPLVFHTNRGPIKFNVWDTAGQEKFGGLRDGYYIQAQCAIIMFDVTSRVTYKNVPNWHRDLVRVCENIPIVLCGNKVDIKDRKVKAKSIVFHRKKNLQYYDISAKSNYNFEKPFLWLARKLIGDPNLEFVAMPALAPPEVVMDPALAAQYEHDLEVAQTTALPDEDDDL, TEST003 (KRAS) - MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHQYREQIKRVKDSDDVPMVLVGNKCDLAARTVESRQAQDLARSYGIPYIETSAKTRQGVEDAFYTLVREIRQHKLRKLNPPDESGPGCMSCKCVLS. Report the complex ID of the protein with the highest contact density.
     Answer: TEST001
  4. Question: Use the CrossPPI binding affinity predictor to analyze a RAS-RAF protein interaction. The ligand sequence is MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHQYREQIKRVKDSDDVPMVLVGNKCDLAARTVESRQAQDLARSYGIPYIETSAKTRQGVEDAFYTLVREIRQHKLRKLNPPDESGPGCMSCKCVLS (189 residues). The receptor sequence is MPSKKQRGSKSKKAAGAAGTSSAGKKPNQKGKGGKNGRGQSSTGNFPGKRAKFVNNQRESFSGPIKRNYIAQVQERGLQQLFELLESDLFSRSTPLADKIRQLVNFWKTSLKEKQQKIENNIKFLGSRKTTGNRLQARLQVF (142 residues). Use the pre-trained models from the save directory. What is the ensemble predicted pKD value (rounded to 2 decimal places)?
     Answer: 5.65
  5. Question: Compare the binding affinity predictions for two protein pairs using CrossPPI. Pair 1: ligand MGDKPIWEQIGSSFIQHYYQLFDNDRTQLGAIYIDASCLTWEGQQFQGKAAIVEKLSSLPFQKIQHSITAQDHQPTPDSCIISMVVGQLKADEDPIMGFHQMFLLKNINDAWVCTNDMFRLALHNFG with receptor MAAQGEPQVQFKLVLVGDGGTGKTTFVKRHLTGEFEKKYVATLGVEVHPLVFHTNRGPIKFNVWDTAGQEKFGGLRDGYYIQAQCAIIMFDVTSRVTYKNVPNWHRDLVRVCENIPIVLCGNKVDIKDRKVKAKSIVFHRKKNLQYYDISAKSNYNFEKPFLWLARKLIGDPNLEFVAMPALAPPEVVMDPALAAQYEHDLEVAQTTALPDEDDDL. Pair 2: ligand MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHQYREQIKRVKDSDDVPMVLVGNKCDLAARTVESRQAQDLARSYGIPYIETSAKTRQGVEDAFYTLVREIRQHKLRKLNPPDESGPGCMSCKCVLS with receptor MPSKKQRGSKSKKAAGAAGTSSAGKKPNQKGKGGKNGRGQSSTGNFPGKRAKFVNNQRESFSGPIKRNYIAQVQERGLQQLFELLESDLFSRSTPLADKIRQLVNFWKTSLKEKQQKIENNIKFLGSRKTTGNRLQARLQVF. Which pair has the higher predicted pKD value?
     Answer: test_pair_1
  6. Question: Use the CrossPPI binding affinity predictor to predict the pKD value for a protein-protein interaction. The ligand protein sequence is MGDKPIWEQIGSSFIQHYYQLFDNDRTQLGAIYIDASCLTWEGQQFQGKAAIVEKLSSLPFQKIQHSITAQDHQPTPDSCIISMVVGQLKADEDPIMGFHQMFLLKNINDAWVCTNDMFRLALHNFG (127 residues, CDC42-like protein). The receptor protein sequence is MAAQGEPQVQFKLVLVGDGGTGKTTFVKRHLTGEFEKKYVATLGVEVHPLVFHTNRGPIKFNVWDTAGQEKFGGLRDGYYIQAQCAIIMFDVTSRVTYKNVPNWHRDLVRVCENIPIVLCGNKVDIKDRKVKAKSIVFHRKKNLQYYDISAKSNYNFEKPFLWLARKLIGDPNLEFVAMPALAPPEVVMDPALAAQYEHDLEVAQTTALPDEDDDL (216 residues, RAC1-like protein). Use the pre-trained models from the save directory. What is the ensemble predicted pKD value (rounded to 2 decimal places)?
     Answer: 8.20
  7. Question: Generate per-residue protein embeddings using the ESM-2 model for the RAC1 receptor protein sequence 'MAAQGEPQVQFKLVLVGDGGTGKTTFVKRHLTGEFEKKYVATLGVEVHPLVFHTNRGPIKFNVWDTAGQEKFGGLRDGYYIQAQCAIIMFDVTSRVTYKNVPNWHRDLVRVCENIPIVLCGNKVDIKDRKVKAKSIVFHRKKNLQYYDISAKSNYNFEKPFLWLARKLIGDPNLEFVAMPALAPPEVVMDPALAAQYEHDLEVAQTTALPDEDDDL' with complex ID 'EMB002', using maximum sequence length of 1000 residues, and save the output to CrossPPI/notebooks/embedding_generator/output/EMB002_test.npy. What is the number of rows in the generated embedding array (which corresponds to the sequence length)?
     Answer: 216

- A Corporative Language Model for Protein-Protein Interaction, Binding Affinity, and Interface Contact Prediction
  Paper: http://biorxiv.org/lookup/doi/10.1101/2025.07.07.663595
  Repo: `PPLM`
  Questions:
  1. Question: Using the PPLM binding affinity prediction tool, predict the binding affinity between the receptor protein sequence in the FASTA file at PPLM/notebooks/run_pplm-affinity/data/receptor.fasta and the ligand protein sequence in the FASTA file at PPLM/notebooks/run_pplm-affinity/data/ligand.fasta. What is the predicted binding affinity value in kcal/mol?
     Answer: -8.226562
  2. Question: Run the PPLM tool using the protein sequence file seq1.fasta located at PPLM/notebooks/run_pplm/data/seq1.fasta as the first protein and seq2.fasta located at PPLM/notebooks/run_pplm/data/seq2.fasta as the second protein, saving the output pickle file to PPLM/notebooks/run_pplm/output/seq1-seq2.pplm.pkl and using GPU device 0. What is the shape of the embed_A array in the output pickle file (format as tuple)?
     Answer: (122, 1280)
  3. Question: Using the PPLM binding affinity prediction tool with the receptor FASTA file at PPLM/notebooks/run_pplm-affinity/data/receptor.fasta and ligand FASTA file at PPLM/notebooks/run_pplm-affinity/data/ligand.fasta, is the predicted binding interaction favorable or unfavorable (based on whether the affinity value is negative or positive)?
     Answer: Favorable
  4. Question: Run the PPLM tool using the protein sequence file seq1.fasta located at PPLM/notebooks/run_pplm/data/seq1.fasta as the first protein and seq2.fasta located at PPLM/notebooks/run_pplm/data/seq2.fasta as the second protein, saving the output pickle file to PPLM/notebooks/run_pplm/output/seq1-seq2.pplm.pkl and using GPU device 0. What is the mean value of the embed_A embeddings in the output pickle file (rounded to 6 decimal places)?
     Answer: -0.000396
  5. Question: Run the PPLM tool using the protein sequence file seq1.fasta located at PPLM/notebooks/run_pplm/data/seq1.fasta as the first protein and seq2.fasta located at PPLM/notebooks/run_pplm/data/seq2.fasta as the second protein, saving the output pickle file to PPLM/notebooks/run_pplm/output/seq1-seq2.pplm.pkl and using GPU device 0. What is the shape of the inter_attn (inter-protein attention) array in the output pickle file (format as tuple)?
     Answer: (660, 122, 70)
  6. Question: Using the PPLM protein-protein interaction prediction tool, predict the interaction probability between the first protein sequence in the file at PPLM/notebooks/run_pplm-ppi/data/seq1.fasta and the second protein sequence in the file at PPLM/notebooks/run_pplm-ppi/data/seq2.fasta, using GPU device 0. What is the predicted interaction score reported in the output?
     Answer: 0.94310874

- Spontaneous Emergence of Symmetry in a Generative Model of Protein Structure
  Paper: http://biorxiv.org/lookup/doi/10.1101/2025.11.03.686219
  Repo: `ChainStorm.jl`
  Questions:
  1. Question: Load the pre-generated protein chain batch data from 'ChainStorm.jl/notebooks/circular/data/batch_circular.csv' which contains chain_id, resind, and circular columns for two protein chains (chain 1 with 15 residues, chain 2 with 60 residues). How many total rows (residues) are in this dataset?
     Answer: 75
  2. Question: Load the pre-generated protein chain batch data from 'ChainStorm.jl/notebooks/circular/data/batch_circular.csv' which contains chain_id, resind, and circular columns. Count how many residues belong to chain 1 (chain_id equals 1). What is this count?
     Answer: 15
  3. Question: Using the wrapped distance algorithm for circular protein chains (where the shortest path on a circular chain of length max_len between positions a and b is computed as: direct = a - b, wrapped = sign(direct) * (max_len - abs(direct)), return direct if abs(direct) < abs(wrapped) else -wrapped), calculate the wrapped distance from position 1 to position 14 on a circular chain with maximum length 15. What is the wrapped distance?
     Answer: 2

- ARCADIA Reveals Spatially Dependent Transcriptional Programs through Integration of scRNA-seq and Spatial Proteomics
  Paper: http://biorxiv.org/lookup/doi/10.1101/2025.11.20.689521
  Repo: `ARCADIA_public`
  Questions:
  1. Question: Run the CITE-seq preprocessing pipeline using the preprocess_cite_seq tool. After the data is loaded from scvi-tools, how many total cells and genes are in the initial CITE-seq dataset before any filtering?
     Answer: 17001 cells and 13553 genes
  2. Question: Using the run_pipeline tool, run the complete ARCADIA pipeline for the cite_seq dataset. According to the configuration file at ARCADIA_public/repo/ARCADIA_public/configs/config.json, what is the maximum number of training epochs configured?
     Answer: 300
  3. Question: Using the ARCADIA hyperparameter search tool, run a hyperparameter search with the dataset name 'cite_seq', maximum epochs set to 400, batch size set to 1024, latent dimension set to 60, number of layers set to 3, 1024 hidden units for RNA encoder, 512 hidden units for protein encoder, learning rate of 0.001, and gradient clipping value of 1.0. How many total parameter combinations are in the default search grid when exploring n_layers options of [3, 1, 6] and latent_dim options of [60, 30]?
     Answer: 6
  4. Question: Run the CITE-seq preprocessing pipeline using the preprocess_cite_seq tool. What is the total number of outlier cells removed across all cell types during the outlier identification step?
     Answer: 1322
  5. Question: Run the CITE-seq preprocessing pipeline using the preprocess_cite_seq tool. After the quality control step, how many cells pass QC out of the total cells processed?
     Answer: 15337

- mIDEA: An Interpretable Structure-Sequence Model for Methylation-Dependent Protein-DNA Binding Sensitivity
  Paper: http://biorxiv.org/lookup/doi/10.1101/2025.11.14.688575
  Repo: `IDEA_DNA_Methylation`
  Questions:
  1. Question: Using the find_dna_protein_contacts tool, identify contacting residues between protein and DNA in the PDB file located at IDEA_DNA_Methylation/notebooks/find_dna_protein_contacts/data/1hlo_modified.pdb with a distance cutoff of 1.2 nanometers. Save the protein contacts to IDEA_DNA_Methylation/notebooks/find_dna_protein_contacts/output/test_protein_contacts.txt and DNA contacts to IDEA_DNA_Methylation/notebooks/find_dna_protein_contacts/output/test_dna_contacts.txt. How many protein residues are identified as being in contact with DNA?
     Answer: 76
  2. Question: Train the mIDEA energy model using the protein list containing 11 proteins (1hloun00 through 1hloun09 and 1hlom00) with the corresponding PDB structure files in the training directory. The phi configuration uses pairwise contact well parameters with r_min equal to negative 8.0, r_max equal to 8.0, kappa equal to 0.7, and minimum sequence separation of 10. After training completes, examine the filtered gamma parameter file. What is the total number of gamma parameters (lines) in the output file named native_trainSetFiles_phi_pairwise_contact_well-8.0_8.0_0.7_10_gamma_filtered?
     Answer: 325
  3. Question: After running the predict_binding_energy tool for PDB ID 1hlo, examine the Energy_mg_10un1m_m.txt output file at IDEA_DNA_Methylation/repo/IDEA_DNA_Methylation/testing/phis/Energy_mg_10un1m_m.txt. What is the predicted binding energy value for sequence 23, which has the most negative (lowest) energy in the entire file?
     Answer: -130.145615
  4. Question: Using the binding energy output file generated from calculating energies with the gamma file at IDEA_DNA_Methylation/notebooks/calculate_binding_energy/input/gamma_10un1m and phi file at IDEA_DNA_Methylation/notebooks/calculate_binding_energy/input/phi_10un1m_m, how many decoy structures have negative binding energy values?
     Answer: 87
  5. Question: Using the generate_reverse_complement tool, transform the sequences in IDEA_DNA_Methylation/notebooks/generate_reverse_complement/input/test_sequences.seq to reverse complements and output to IDEA_DNA_Methylation/notebooks/generate_reverse_complement/output/final.seq. What is the reverse complement of the longest sequence (sequence 11 with 25 bases: AGTTACGGTGGGCAGCGTCCTTGGT)?
     Answer: ACCAAGGACGCTGCCCACCGTAACT
  6. Question: Using the extract_pdb_sequence tool, extract the sequence from the DNA structure with methylation test PDB file located at IDEA_DNA_Methylation/notebooks/extract_pdb_sequence/data/test_methylated.pdb. The PDB file contains DNA residues including a 5-methylcytosine (5CM) residue. What is the extracted sequence where 5-methylcytosine is represented as a period character?
     Answer: e.lt
  7. Question: Using the map_dna_for_methylation tool, convert the DNA sequences in the input file at IDEA_DNA_Methylation/notebooks/map_dna_for_methylation/input/input_dna.seq to Modeller representation and save the output to IDEA_DNA_Methylation/notebooks/map_dna_for_methylation/output/test_output.seq. How many total methylation markers (period characters) are present across all 50 sequences in the output file?
     Answer: 336

- GeneCAD: Plant Genome Annotation with a DNA Foundation Model
  Paper: http://biorxiv.org/lookup/doi/10.1101/2025.10.31.685877
  Repo: `genecad`
  Questions:
  1. Question: Use the gff.py summarize command to analyze genecad/notebooks/gff_summarize/data/arabidopsis_chr4.gff3. In the strand distribution section, what percentage of records are on the positive strand (rounded to two decimal places)?
     Answer: 50.75
  2. Question: Using the gff.py filter_to_valid_genes command, filter the Arabidopsis chromosome 4 GFF file at genecad/notebooks/gff_filter_to_valid_genes/data/arabidopsis_chr4.gff3 with the require-utrs option set to no. What is the gene ID (in the format AT4GXXXXX) of the first protein-coding gene that appears in the filtered output?
     Answer: AT4G00005
  3. Question: Use the gff.py summarize command to analyze the GFF file at genecad/notebooks/gff_summarize/data/arabidopsis_chr4.gff3. What is the most common feature type combination per transcript, and how many transcripts have this combination?
     Answer: CDS, exon, five_prime_UTR, three_prime_UTR with 6197 transcripts
  4. Question: Using the gff.py filter_to_chromosome command, filter the Arabidopsis GFF file at genecad/notebooks/gff_filter_to_chromosome/data/arabidopsis_full.gff3 to include only entries from chromosome 3. Save the output to genecad/notebooks/gff_filter_to_chromosome/output/arabidopsis_chr3_analysis.gff3. How many features of type gene are in the filtered output file?
     Answer: 5460
  5. Question: Using the gff.py merge command, merge the Arabidopsis chromosome 1 GFF3 file at genecad/notebooks/gff_merge/data/arabidopsis_chr1.gff3 and the chromosome 2 GFF3 file at genecad/notebooks/gff_merge/data/arabidopsis_chr2.gff3 into a single output file at genecad/notebooks/gff_merge/output/merged.gff3. How many gene features (lines where the third column equals 'gene') are in the merged output file?
     Answer: 11473
  6. Question: Using the gff.py filter_to_valid_genes command, filter the Arabidopsis chromosome 4 GFF file located at genecad/notebooks/gff_filter_to_valid_genes/data/arabidopsis_chr4.gff3 with the require-utrs option set to yes, saving the output to genecad/notebooks/gff_filter_to_valid_genes/output/valid_genes_with_utrs.gff3. How many gene features are present in the resulting filtered GFF file?
     Answer: 3433

- BioPrediction-PPI: Simplifying the Prediction of Protein-Protein actions through Artificial Intelligence
  Paper: http://biorxiv.org/lookup/doi/10.1101/2025.11.16.688401
  Repo: `BioPrediction-PPI`
  Questions:
  1. Question: Using the extract_entropy_features tool, extract Tsallis entropy-based features from the protein sequences at BioPrediction-PPI/notebooks/extract_entropy_features/data/sample_proteins.fasta. Set the sequence label to 'protein', use a k-mer size of 5, and specify Tsallis as the entropy type. What is the k1 (1-mer Tsallis entropy) value for the sequence Q9ULG1 in the output file?
     Answer: 0.9361035480865181
  2. Question: Using the extract_entropy_features tool, extract Shannon entropy features from the protein sequences at BioPrediction-PPI/notebooks/extract_entropy_features/data/sample_proteins.fasta. Use 'protein' as the label, set k-mer size to 5, and specify Shannon as the entropy type. In the output CSV file, what is the k5 (5-mer Shannon entropy) value for the sequence P37268?
     Answer: 8.689997971419444

- SKiM-GPT: Combining Biomedical Literature-Based Discovery with Large Language Model Hypothesis Evaluation
  Paper: http://biorxiv.org/lookup/doi/10.1101/2025.07.28.664797
  Repo: `skimgpt`
  Questions:
  1. Question: Using the SKiM-GPT wrapper result merger tool, merge the per-year results from the skim_with_gpt wrapper output directory at skimgpt/notebooks/wrapper_result_merger_py/data/test_wrapper_output_skim. What is the gpt_4o_score for the gene_A, protein_X, disease_1 triplet in censor year 1990?
     Answer: 0.89
  2. Question: Using the SKiM-GPT wrapper result merger tool, merge the per-year results from the km_with_gpt wrapper output directory located at skimgpt/notebooks/wrapper_result_merger_py/data/test_wrapper_output. How many total rows are in the merged output TSV file?
     Answer: 10
  3. Question: Using the SKiM-GPT score extraction tool, process the DCH mode test data directory at skimgpt/notebooks/eval_json_results/data/test_dch_output which contains a config.json with is_dch set to true and a Hypothesis_Comparison JSON result file. In the generated results.tsv file, what is the Decision value?
     Answer: H1
  4. Question: Using the SKiM-GPT score extraction tool, process the iterations test data directory at skimgpt/notebooks/eval_json_results/data/test_iterations which contains iteration_1 and iteration_2 subdirectories under the results folder. In the generated results.tsv file, what is the Score value for Iteration 2?
     Answer: 0.81
  5. Question: Using the SKiM-GPT wrapper result merger tool, merge the per-year results from the km_with_gpt wrapper output directory at skimgpt/notebooks/wrapper_result_merger_py/data/test_wrapper_output. What is the gpt_4o_mini_score value for the relationship between cancer and smoking in the censor year 2000?
     Answer: 0.98

- MetaPointFinder: Detection of Antimicrobial Resistance-Conferring Point Mutations (ARMs) from Metagenomic Reads
  Paper: http://biorxiv.org/lookup/doi/10.64898/2025.12.04.691125
  Repo: `metapointfinder`
  Questions:
  1. Question: Using the pad_sequences tool, pad or truncate the FASTA sequences in the input file at metapointfinder/notebooks/pad_to_10kb/data/input_sequences.fasta to a target length of 5000 base pairs with left trimming mode (keeping the first N bases), saving the output to metapointfinder/notebooks/pad_to_10kb/output/test_trimmed_left.fasta. After running the tool, what is the length in base pairs of the sequence with ID seq_exact_10000bp in the output file?
     Answer: 5000
  2. Question: Using the generate_dna_mutants tool, process the sample input TSV file at metapointfinder/notebooks/make_dna_mutants/output/sample_input.tsv, generating 2 mutant plus wildtype pairs per row, with random seed set to 42. Save the output FASTA to metapointfinder/notebooks/make_dna_mutants/output/benchmark_dna_mutants.fna. How many total sequences are generated in the output FASTA file?
     Answer: 20
  3. Question: Using the protein mutant generator tool, generate wildtype and mutant protein sequences from the AMR protein mutation data. Use the TSV file at metapointfinder/notebooks/mutation_r_wt_generator/input/AMRProt-mutation_underscore_combined.tsv and the FASTA file at metapointfinder/notebooks/mutation_r_wt_generator/input/AMRProt_mutation.fa. Generate 3 mutant-wildtype pairs per input row, use random seed 42, and save output to metapointfinder/notebooks/mutation_r_wt_generator/output/protein_mutants_test.faa. How many total sequences are generated in the output FASTA file?
     Answer: 1182
  4. Question: Using the pad_sequences tool, pad or truncate the FASTA sequences in the input file at metapointfinder/notebooks/pad_to_10kb/data/input_sequences.fasta to a target length of 5000 base pairs with center trimming mode, saving the output to metapointfinder/notebooks/pad_to_10kb/output/test_padded_5kb.fasta. After running the tool, what is the length in base pairs of the sequence with ID seq_long_15000bp in the output file?
     Answer: 5000
  5. Question: Generate protein mutants using the TSV file at metapointfinder/notebooks/mutation_r_wt_generator/input/AMRProt-mutation_underscore_combined.tsv and FASTA file at metapointfinder/notebooks/mutation_r_wt_generator/input/AMRProt_mutation.fa, with 3 pairs per row, seed 42, output to metapointfinder/notebooks/mutation_r_wt_generator/output/protein_mutants_test.faa. How many unique AMR classes appear in the output sequences?
     Answer: 37
  6. Question: Using the pad_sequences tool, pad or truncate the FASTA sequences in the input file at metapointfinder/notebooks/pad_to_10kb/data/input_sequences.fasta to a target length of 10000 base pairs, saving the output to metapointfinder/notebooks/pad_to_10kb/output/test_padded_10kb.fasta with center trimming mode. After running the tool, what is the length in base pairs of the sequence with ID seq_short_500bp in the output file?
     Answer: 10000

- LARIS enables accurate and efficient ligand and receptor interaction analysis in spatial transcriptomics
  Paper: http://biorxiv.org/lookup/doi/10.1101/2025.11.26.690796
  Repo: `LARIS`
  Questions:
  1. Question: Using the pre-generated AnnData object from 'LARIS/notebooks/04_laris_tutorial/data/LARIS_tutorial_datasets/adata_tonsil.h5ad' and the ligand-receptor database from 'LARIS/notebooks/04_laris_tutorial/data/LARIS_tutorial_datasets/human_lr_database_CellChatDB_formatted_v2.csv', run the LARIS inference with parameters: 20 nearest neighbors, mu equals 0.40, sigma equals 100, 5 permutation repeats, expressed_pct equals 0.1, mu_celltype equals 100, and by_celltype set to True with groupby 'cell_type'. How many cell type-level interactions have a p_value less than 0.05?
     Answer: 8772
  2. Question: Using the pre-generated AnnData object from 'LARIS/notebooks/04_laris_tutorial/data/LARIS_tutorial_datasets/adata_tonsil.h5ad' (human tonsil Slide-tags spatial transcriptomics data with 5695 cells x 25583 genes) and the ligand-receptor database from 'LARIS/notebooks/04_laris_tutorial/data/LARIS_tutorial_datasets/human_lr_database_CellChatDB_formatted_v2.csv', prepare a ligand-receptor AnnData object using 20 nearest neighbors and 'X_spatial' as the spatial coordinates key. How many ligand-receptor interaction pairs are in the resulting LR AnnData object (number of variables)?
     Answer: 1985
  3. Question: Using the pre-generated AnnData object from 'LARIS/notebooks/04_laris_tutorial/data/LARIS_tutorial_datasets/adata_tonsil.h5ad' and the ligand-receptor database from 'LARIS/notebooks/04_laris_tutorial/data/LARIS_tutorial_datasets/human_lr_database_CellChatDB_formatted_v2.csv', run the LARIS inference with parameters: 20 nearest neighbors, mu equals 0.40, sigma equals 100, 5 permutation repeats, expressed_pct equals 0.1, mu_celltype equals 100, and by_celltype set to True with groupby 'cell_type'. What is the ligand name of the top-ranked spatially variable interaction (rank 0)?
     Answer: SEMA4A

- cpiVAE: Robust and Interpretable Cross-Platform Proteomics Imputation
  Paper: http://biorxiv.org/lookup/doi/10.1101/2025.11.20.689433
  Repo: `cpiVAE_v1`
  Questions:
  1. Question: Using the analyze_latent_space tool with the latent representation files at cpiVAE_v1/notebooks/analyze_latent_space/data/latent_platform_a.csv and cpiVAE_v1/notebooks/analyze_latent_space/data/latent_platform_b.csv, truth files at cpiVAE_v1/notebooks/analyze_latent_space/data/truth_platform_a.csv and cpiVAE_v1/notebooks/analyze_latent_space/data/truth_platform_b.csv, groups file at cpiVAE_v1/notebooks/analyze_latent_space/data/groups.csv, platform names 'Platform A' and 'Platform B', saving output to cpiVAE_v1/notebooks/analyze_latent_space/output_test2. According to the analysis summary, how many biological groups are present in the data?
     Answer: 3
  2. Question: Using the feature importance analysis tool, analyze the importance matrices at cpiVAE_v1/notebooks/analyze_feature_importance/data/importance_a_to_b.csv and cpiVAE_v1/notebooks/analyze_feature_importance/data/importance_b_to_a.csv with platform names set to Platform A and Platform B, using the absolute_importance threshold method with threshold parameter 0.5 and directed network type. What is the correlation coefficient for the degree centrality between the two network directions as reported in the network comparison?
     Answer: 0.650
  3. Question: Run the KNN baseline for cross-platform imputation using the platform A data file at cpiVAE_v1/notebooks/run_knn_baseline/data/platform_a.csv and platform B data file at cpiVAE_v1/notebooks/run_knn_baseline/data/platform_b.csv, with 5 neighbors, distance kernel weighting, and random seed 42. In the detailed report for A to B prediction, which feature has the highest R-squared score?
     Answer: Metabolite_B_07
  4. Question: Using the confidence estimation tool with the Monte Carlo method, estimate imputation confidence for the Platform A test data at cpiVAE_v1/notebooks/estimate_imputation_confidence/data/platform_a_test.csv. Use the trained VAE experiment at cpiVAE_v1/notebooks/estimate_imputation_confidence/data/quick_experiment/confidence_test/version_20260113-003830 as the experiment directory, set the source platform to 'a', target platform to 'b', method to 'mc', and number of runs to 10. Save the output to cpiVAE_v1/notebooks/estimate_imputation_confidence/output/test_confidence_mc.csv. What is the mean confidence score reported in the summary statistics?
     Answer: 0.783895
  5. Question: Using the WNN baseline tool, run cross-platform imputation on Platform A data at cpiVAE_v1/notebooks/run_wnn_baseline/data/platform_a.csv and Platform B data at cpiVAE_v1/notebooks/run_wnn_baseline/data/platform_b.csv. Use 20 neighbors, 50 neighbors for union graph, WNN regularization of 1.0, k weight of 10, 10 PCA components, test split of 0.2, and random seed 42. Save outputs to cpiVAE_v1/notebooks/run_wnn_baseline/outputs_wnn. In the detailed report for A to B imputation, which feature has the highest R-squared score?
     Answer: ProteinB_038
  6. Question: Run phenotype association discovery using the proteomics truth matrix at cpiVAE_v1/notebooks/discover_phenotype_associations/data/truth_matrix.csv and the phenotype table at cpiVAE_v1/notebooks/discover_phenotype_associations/data/phenotype_table.csv. Use GENDER as the gender covariate column and V5AGE52 as the age covariate column, saving output to cpiVAE_v1/notebooks/discover_phenotype_associations/output_test. According to the summary_continuous_all.csv output file, which continuous phenotype has the highest number of significant protein associations at FDR less than 0.05?
     Answer: Biomarker_2
  7. Question: Using the feature importance analysis tool, analyze the importance matrices at cpiVAE_v1/notebooks/analyze_feature_importance/data/importance_a_to_b.csv and cpiVAE_v1/notebooks/analyze_feature_importance/data/importance_b_to_a.csv with platform names set to Platform A and Platform B, using the absolute_importance threshold method with threshold parameter 0.5 and directed network type. What is the number of edges in the Platform A to Platform B network?
     Answer: 10

- pmultiqc: An open-source, lightweight, and metadata-oriented QC reporting library for MS proteomics
  Paper: http://biorxiv.org/lookup/doi/10.1101/2025.11.02.685980
  Repo: `pmultiqc`
  Questions:
  1. Question: Using the generate_pmultiqc_report tool, generate a QC report for the quantms pipeline LFQ data located at pmultiqc/repo/pmultiqc/tests/resources/lfq, saving the output to pmultiqc/notebooks/generate_pmultiqc_report/output/lfq_report_test. Use the quantms data format, enable decoy removal, and use force mode to overwrite. What is the size of the generated multiqc_report.html file in bytes?
     Answer: 2583885
  2. Question: Using the generate_maxquant_qc_report tool on the MaxQuant data at pmultiqc/notebooks/generate_pmultiqc_report/data/maxquant_temp with decoy removal and force mode enabled, how many unique peptides were identified according to the evidence data processing?
     Answer: 29216
  3. Question: Using the generate_maxquant_qc_report tool, generate a QC report for the MaxQuant results in pmultiqc/notebooks/generate_pmultiqc_report/data/maxquant_temp, saving output to pmultiqc/notebooks/generate_pmultiqc_report/output/maxquant_report_test with decoy removal enabled and force mode. How many reverse (decoy) entries were filtered out from the proteinGroups data?
     Answer: 52

- Model-based Standardization of Correlation Coefficients Improves Multi-Omic Clustering and Biological Signal Discovery
  Paper: http://biorxiv.org/lookup/doi/10.1101/2025.11.17.688875
  Repo: not explicit in the benchmark question set
  Questions:
  1. Question: Load multi-omics data from primary metabolites ('data/Primary_synth.tsv'), lipids ('data/Lipids_synth.tsv'), biogenic amines ('data/BA_synth.tsv'), and proteins ('data/proteins_synth.tsv'). Merge all dataframes by 'subjectID', then apply WGCNA's goodSamplesGenes function with default parameters (50% missingness filter). Count the remaining analytes in each category by intersecting original column names with filtered columns. Report the counts for proteins, lipids, primary metabolites, and biogenic amines respectively, as a space-separated string.
     Answer: 283 712 149 321 1465

# enzyme

- Exploring the Conformational Landscape of Adenylate Kinase and Beyond: A Benchmark of Protein Folding Models
  Paper: http://biorxiv.org/lookup/doi/10.1101/2025.11.04.686486
  Repo: `FoldConfBench`
  Questions:
  1. Question: The FoldConfBench input directory at FoldConfBench/notebooks/run_foldconfbench/input contains alignment files for protein 6KWC_1. What is the total file size in bytes of the alignments/6KWC_1 subdirectory (including all alignment files)?
     Answer: 6841118
