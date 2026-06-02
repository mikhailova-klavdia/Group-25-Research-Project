import csv
from pathlib import Path

# Load CSV data — path relative to this script's location
_HERE = Path(__file__).parent
_CSV_PATH = _HERE / "Paper2AgentBench" / "eval" / "100_compbio_repos" / "300_questions.csv"

with open(_CSV_PATH, encoding='utf-8') as f:
    reader = csv.reader(f)
    rows = list(reader)

csv_data = rows[1:]  # 300 rows

# Group-25 duplicate indices (0-indexed into csv_data)
group25_csv_indices = {
    50: 'PPLM_001',
    92: 'PPLM_002',
    85: 'PPLM_003',
    102: 'PPLM_004',
    177: 'PPLM_005',
    236: 'PPLM_006',
    190: 'CROSSPPI_001',
    238: 'CROSSPPI_003',
    38: 'CROSSPPI_004',
    295: 'CROSSPPI_006',
    147: 'METAPOINT_001',
    219: 'METAPOINT_002',
    89: 'METAPOINT_003',
    159: 'METAPOINT_004',
    68: 'METAPOINT_005',
}

# Assign Q-IDs to non-Group-25 rows
q_counter = 1
csv_questions = []  # (question_id, biorxiv_link, question, ground_truth)
for idx, row in enumerate(csv_data):
    if idx in group25_csv_indices:
        continue
    qid = "Q{:03d}".format(q_counter)
    q_counter += 1
    csv_questions.append((qid, row[0], row[1], row[2]))

print("Number of non-Group-25 CSV questions:", len(csv_questions))


def score_question(question_text, biorxiv_link, ground_truth):
    q = question_text.lower()

    # Axis 1: Model weights / downloads (0-40)
    ax1 = 0
    # Very large (>5GB): LLMs, large foundation models
    if any(x in q for x in ['tcgabiolinks', 'download_geo_dataset', 'tcga-paad', 'tcga paad',
                             'download tcga', 'geo query', 'download geo']):
        ax1 = 40
    # Large (500MB-5GB): ESM-2, scGPT, RegFormer, USHER, Evo2HiC, CryoSiam SimSiam
    elif any(x in q for x in ['esm-2 model', 'esm2', 'embedding_generator',
                               'simsiam embeddings predict', 'simsiam_embeddings_predict',
                               'config_test.yaml', 'scgpt', 'regformer',
                               'usher alignment model', 'alignment_model.pt',
                               'evo2hic', 'enhance_hic_resolution',
                               't5-embedded', 't5 embedded', 'run_t5_mlp',
                               'dnabert2', 'tsmet5']):
        ax1 = 30
    # Medium (100-500MB): PPLM (ESM-2 based), CrossPPI (ESM-2 based), trained ML models,
    #                     mavenets MLP/MPN training, FADVI, ARCADIA, scRegulate,
    #                     CryoSiam spectral (loads embeddings), ScisTreeCNA inference
    elif any(x in q for x in ['pplm tool', 'run_pplm', 'run pplm', 'run the pplm',
                               'crossppi binding', 'use the crossppi', 'crosspi',
                               'cross-platform imputation', 'cpivae',
                               'pre-trained models from the save directory',
                               'pre-trained usher',
                               'train.*mlp', 'mlp model', 'mavenets.*train', 'train.*mavenets',
                               'train.*mpn', 'mpn model', 'mavenets_train_mpn',
                               'train.*fadvi', 'fadvi.*train', 'fadvi model',
                               'scregulate.*train', 'train.*scregulate',
                               'run the complete arcadia', 'arcadia pipeline',
                               'hyperparameter search.*arcadia',
                               'scistreecna inference', 'run scistreecna',
                               'run scistree2',
                               'xgboost models', 'per-window ancestry classifier',
                               'knn baseline', 'wnn baseline',
                               'confidence estimation.*mc',
                               'analyze_latent_space',
                               'feature importance analysis',
                               'discover_phenotype',
                               'compare.*batch correction',
                               'train.*random forest',
                               'train.*r.*model',
                               'run_pipeline_gmmat', 'gmmat gwas',
                               'saga.*run_pipeline',
                               'full tnbc hybrid optimization',
                               'tnbc.*simulations',
                               'idea.*energy model', 'train.*energy model',
                               'predict_binding_energy',
                               'mavenets library.*train',
                               'run.*complete.*recode',
                               'recode denoising', 'recode noise reduction',
                               'recode.*fit_transform',
                               'cite-seq preprocessing pipeline',
                               'preprocess_cite_seq',
                               'run_pipeline.*arcadia',
                               'stratifiedshapes.*wasserstein',
                               'wasserstein embeddings',
                               'mmd distance',
                               'umap embedding', 'compute.*umap',
                               'run umap', 'leiden clustering',
                               'louvain clustering',
                               'distortions.*mammoth', 'distortions.*pbmc',
                               'distortions.*c_elegans.*umap',
                               'pbmc3k.*umap',
                               'pca.*variance.*vst',
                               'collect.*prior.*scregulate',
                               'wgcna.*goodsamples',
                               'batch.*silhouette.*pca',
                               'laris inference',
                               'prepare.*ligand-receptor']):
        ax1 = 20
    # Small pre-trained weights or loaded pre-generated data
    elif any(x in q for x in ['pre-generated', 'pre_generated', 'pre-trained',
                               'pretrained', 'fadvi_save', 'load.*model',
                               'load.*from', 'load.*pre',
                               'optuna study', 'classification results',
                               'embedding.*npy', 'embeddings.npy',
                               'cell_labels.csv', 'random_test.csv',
                               'config.*predict', 'config_predict',
                               'execution_summary.json',
                               'config.*spectral', 'spectral clustering.*config',
                               'low_coverage_hic', 'high_resolution_reference',
                               'metadata.json', 'coordinates.json']):
        ax1 = 10
    else:
        ax1 = 0

    # Axis 2: Environment setup complexity (0-30)
    ax2 = 0
    # GPU/CUDA required
    if any(x in q for x in ['gpu device 0', 'gpu device', 'using gpu', 'cuda',
                             'simsiam embeddings predict', 'config_test.yaml']):
        ax2 = 30
    # PyTorch or multiple specialty packages
    elif any(x in q for x in ['pplm tool', 'run_pplm', 'run pplm', 'run the pplm',
                               'crossppi binding affinity predictor',
                               'use the crossppi binding',
                               'esm-2 model', 'esm2', 'embedding_generator',
                               'simsiam', 'cryosiam',
                               'scgpt', 'regformer cell embeddings', 'regformer drug',
                               'usher', 'evo2hic', 't5-embedded', 't5 embedded',
                               'mavenets.*train', 'train.*mavenets', 'mavenets library',
                               'train.*mpn', 'mpn model', 'mavenets_train_mpn',
                               'fadvi.*train', 'train.*fadvi',
                               'scregulate.*train', 'train.*scregulate',
                               'arcadia pipeline', 'run the complete arcadia',
                               'hyperparameter search.*arcadia',
                               'scistreecna inference',
                               'stratifiedshapes.*wasserstein',
                               'wasserstein embeddings',
                               'recode denoising', 'recode noise reduction',
                               'recode.*fit_transform',
                               'distortions.*mammoth.*umap', 'distortions.*pbmc.*umap',
                               'pbmc3k.*umap.*leiden',
                               'cpivae.*vae', 'train.*vae',
                               'laris inference.*run',
                               'idea.*energy model', 'train.*energy',
                               'predict_binding_energy.*pdb',
                               'run.*cite-seq.*pipeline',
                               'preprocess_cite_seq',
                               'compare.*batch correction.*pca',
                               'train.*random forest.*tcga',
                               'dnabert2', 'tsmet5',
                               'tcgabiolinks', 'download_geo']):
        ax2 = 20
    # One non-trivial specialty package
    elif any(x in q for x in ['pysam', 'biopython', 'scanpy', 'rdkit', 'datamol',
                               'anndata', 'loom file', '.h5ad', '.h5', 'biom',
                               'plink', 'phyloseq', 'deseq2', 'gmmat', 'wgcna',
                               'xgboost', 'silhouette', 'umap', 'leiden', 'louvain',
                               'screcode', 'tacco', 'laris', 'pathweigh',
                               'tcgabiolinks', 'rna-harmonization', 'harvest',
                               'openai', 'sragent', 'admixture', 'vcf',
                               'medchem', 'spatial transcriptomics',
                               'cite-seq', 'cite_seq', 'scatac', 'atac',
                               'dipgenie', 'breakinator',
                               'blobtk', 'mm2-ivh', 'samtools', 'bowtie', 'minimap',
                               'consensusmetada', 'metaboprep',
                               'tissuenarrator',
                               'gwprot', 'hypergraphembedding', 'jaccard kernel',
                               'edit kernel', 'node betweenness', 'graph2vec',
                               'skimgpt', 'skim-gpt',
                               'ibis-rsnp', 'ape precalculate',
                               'idea_dna', 'methylation', 'methylseqr',
                               'scistree', 'asvnet',
                               'svirlpool', 'chainstorm',
                               'kcftools', 'pathogensurveillance',
                               'hepcytedamage', 'hepatocyte', 'hdag',
                               'consensus_meta_da', 'collectri',
                               'scregulate', 'spectral clustering',
                               'cryosiam spectral', 'cryosiam semantic',
                               'gffai', 'anthropic provider',
                               'pmultiqc', 'generate_pmultiqc',
                               'generate_maxquant', 'maxquant',
                               'sentieon', 'dnascope',
                               'saga.*qq', 'saga.*manhattan', 'saga.*gwas',
                               'create_qq_plot', 'create_snp_density',
                               'create_circular_manhattan',
                               'foldconfbench', 'segma',
                               'asv', 'asvnet', 'kdistance',
                               'biprediction', 'bioprediction',
                               'extract_entropy', 'tsallis', 'shannon',
                               'copangraph', 'mixing_calcs', 'run_real_eval',
                               'gaf', 'gfa', 'dipgenie', 'vcf2gfa',
                               'run_dnascope', 'sentieon-cli',
                               'storm-seq', 'stormseq', 'loom',
                               'nascent', 'mature rna', 'simulation.*poisson',
                               'negative binomial', 'fpkm', 'scrnaseq',
                               'spatial transcriptome', 'spatialtranscriptome',
                               'gwas.*simulation', 'ols.*gwas',
                               'inflation ratio', 'heatmap.*inflation',
                               'rho_max_distribution',
                               'spaceBF', 'spacebf', 'spatial kernel',
                               'minimum spanning tree', 'mst',
                               'hepcytedamagescore', 'hepatocyte damage',
                               'rna-harmonization', 'rnaharmonization',
                               'tcga.*paad', 'geo.*download',
                               'batch correction method',
                               'combat', 'harmony', 'mnn',
                               'viral genome', 'virus.*clustering',
                               'bacteria.*genome', 'bacteria.*selection',
                               'run.*hierarchical', 'hierarchical.*linkage']):
        ax2 = 10
    else:
        ax2 = 0

    # Axis 3: Execution time (0-20)
    ax3 = 0
    # Very slow (>30 min): large model training, whole genomics pipelines
    if any(x in q for x in ['train.*10000 epoch', 'scregulate.*train',
                             'run.*plink quality control', 'plink.*qc.*kinship',
                             'saga.*plink', 'run plink',
                             'wgcna.*goodsamples',
                             'laris inference.*permutation',
                             'run the complete arcadia pipeline',
                             'run.*complete arcadia',
                             'all 54.*kras.*pdb.*lgd', 'lgd.*comparison',
                             'compute.*pairwise gw distance',
                             '54 kras protein pdb',
                             'run the full tnbc hybrid',
                             'full tnbc hybrid optimization',
                             'mavenets.*train.*mlp.*50.*epoch',
                             'train.*mlp.*t5.*50 epoch',
                             'train.*50 training epoch',
                             'scistreecna.*run scistreecna inference',
                             'run scistree2',
                             'recode.*stereo-seq.*recode noise',
                             'recode noise reduction.*stereo',
                             'run.*cite-seq preprocessing pipeline.*outlier',
                             'preprocess_cite_seq.*outlier']):
        ax3 = 20
    # Slow (5-30 min): model training, large clustering, complex pipelines
    elif any(x in q for x in ['train.*epoch', 'training.*epoch',
                               'xgboost models.*chromosome.*5fold',
                               'per-window ancestry classifier.*train',
                               'simsiam embeddings predict.*config_test',
                               'cryosiam.*simsiam.*predict',
                               'recode.*fit_transform',
                               'recode denoising',
                               'recode.*fit_transform.*atac',
                               'recode.*atac.*fit_transform',
                               'umap.*distortions.*c_elegans',
                               'c_elegans.*umap.*distortions',
                               'mammoth.*umap', 'umap.*mammoth',
                               'pbmc3k.*umap', 'umap.*pbmc3k',
                               'run.*gmmat', 'gmmat.*pipeline',
                               'run.*gmmat gwas',
                               'compare.*batch correction.*silhouette',
                               'combat.*batch.*silhouette',
                               'hepcytedamage.*r function', 'hdag.*r',
                               'hepatocyte.*damage.*r',
                               'run_pipeline_gmmat',
                               'breakinator.*paf.*tool',
                               'run breakinator',
                               'cite-seq.*pipeline.*qc',
                               'run.*cite-seq preprocessing',
                               'arcadia.*hyperparameter',
                               'mavenets.*train.*mlp',
                               'fadvi.*train.*epoch',
                               'train.*fadvi.*epoch',
                               'cpivae.*train', 'cpivae.*vae',
                               'train.*random forest.*tcga',
                               'viral genome.*hierarchical',
                               'virus.*hierarchical clustering',
                               'bacteria.*hierarchical',
                               'run.*hierarchical.*virus',
                               'laris.*inference']):
        ax3 = 15
    # Moderate (1-5 min): pipeline runs, multi-step tools
    elif any(x in q for x in ['generate.*pmultiqc', 'pmultiqc.*report',
                               'generate_pmultiqc', 'generate_maxquant',
                               'maxquant.*qc report',
                               'dipgenie.*gfa.*reads',
                               'run dipgenie',
                               'using.*pplm.*binding affinity',
                               'pplm binding affinity prediction tool',
                               'run the pplm tool',
                               'run pplm tool',
                               'crossppi binding affinity predictor',
                               'use the crossppi',
                               'esm-2 model.*embedding',
                               'embedding_generator',
                               'generate.*embeddings.*esm',
                               'generate per-residue protein embeddings',
                               'generate a binary contact map',
                               'contact map generation',
                               'run.*sentieon',
                               'sentieon-cli.*dnascope',
                               'dnascope.*dry_run',
                               'run.*gffai',
                               'gffai tool.*anthropic',
                               'gwas simulation', 'ols.*gwas simulation',
                               'run.*ols-based gwas',
                               'get_rho_max_distribution',
                               'run.*gwas.*analysis', 'gwas.*run',
                               'run.*saga.*gmmat',
                               'run.*gmmat',
                               'create.*qq plot', 'create_qq_plot',
                               'create.*manhattan', 'create_circular_manhattan',
                               'create_snp_density',
                               'run.*database preparation',
                               '16s.*database preparation',
                               'blobtk filter', 'blobtk taxonomy',
                               'blobtk validate', 'blobtk.*snail',
                               'blobtk.*plot',
                               'extract.*subgraph.*gfa',
                               'mixing_calcs_bac',
                               'run_real_eval',
                               'align_feature_sequences',
                               'vcf_to_fasta',
                               'ibis-rsnp.*make_filelist',
                               'run.*04_make_filelist',
                               'ape precalculatethresholds',
                               'segma.*process_sequences',
                               'extract.*entropy features',
                               'breakinator.*analyze.*paf',
                               'merge_breakpoints',
                               'mm2-ivh.*align',
                               'using mm2-ivh',
                               'calculate.*pocp',
                               'assign.*context_references',
                               'assign_context_references',
                               'assign_mapping_reference',
                               'initial_classification.*sendsketch',
                               'run initial_classification',
                               'check_samplesheet',
                               'align.*feature.*sequence',
                               'run.*dna.*protein contact',
                               'find_dna_protein_contacts',
                               'run.*binding energy',
                               'calculate_binding_energy',
                               'train.*idea energy',
                               'spectral clustering tool',
                               'cryosiam spectral',
                               'semantic_to_centers',
                               'using.*svirlpool database.*extract',
                               'svirlpool.*cut_reads',
                               'run.*svirlpool',
                               'jaccard kernel tool',
                               'using.*jaccardkernel',
                               'edit distance matrix',
                               'using.*editkernel',
                               'node betweenness',
                               'using.*nodebetweennessembedding',
                               'graph2vec.*optuna',
                               'using.*graph2vec',
                               'bag.*hyperedges.*embedding',
                               'run.*ibis', 'ibis.*annotation',
                               'run.*consensus.*meta_da',
                               'consensusmetada.*build',
                               'build.*phyloseq',
                               'using.*metaboprep',
                               'run.*gwp.*lgd',
                               'gwprot.*lgd', 'gwprot.*load.*pdb',
                               'load.*54.*kras',
                               'run.*foldconfbench',
                               'foldconfbench.*input',
                               'saga.*run.*pipeline',
                               'run.*pipeline.*saga',
                               'run.*snakemake',
                               'ovo scheduler',
                               'incytokine.*cytokine analysis',
                               'run.*incytokine',
                               'run.*genecad.*gff.*filter',
                               'gff.*filter_to_chromosome',
                               'gff.*merge.*command',
                               'gff.*filter_to_valid',
                               'gff.*summarize.*command',
                               'run.*gff.*command',
                               'run.*geneontology',
                               'run.*pathway.*pathweigh',
                               'pathway activity.*pathweigh',
                               'run.*spatial.*sentence',
                               'build.*spatial sentence',
                               'tissuenarrator.*spatial sentence',
                               'run.*scistree', 'scistree2',
                               'using.*scistree',
                               'run.*asvnet', 'asvnet.*kdistance',
                               'using.*asvnet',
                               'run.*dipgenie',
                               'vcf2gfa.*conversion',
                               'run.*vcf2gfa',
                               'using.*dipgenie',
                               'concatenate_genomes',
                               'virus_generate_selection',
                               'generate_all_selection',
                               'run_centroid',
                               'bacteria_generate_selection',
                               'convert_matrix.*cli',
                               'run.*hierarchical.*clustering',
                               'virus.*hierarchical.*clustering',
                               'using.*hierarchical.*clustering',
                               'using.*run_centroid',
                               'using.*centroid.*tool',
                               'run.*sr.*agent', 'using.*sragent',
                               'sragent.*comprehensive',
                               'run.*cryosiam']):
        ax3 = 10
    # Fast (<30 sec): simple tool runs, quick computations
    elif any(x in q for x in ['using.*tool.*', 'run.*script',
                               'generate.*dataset', 'create.*dataset',
                               'using.*breakinator tool', 'breakinator tool',
                               'using.*merge_breakpoints',
                               'using.*blobtk filter',
                               'load.*pre-generated', 'load.*pre_generated',
                               'read.*file', 'examine.*file',
                               'load.*file', 'parse.*file',
                               'filter.*file', 'count.*file',
                               'extract.*file', 'process.*file',
                               'calculate.*', 'compute.*',
                               'using.*kcftools', 'kcftools.*',
                               'using.*gff.py', 'gff.py.*',
                               'using.*blobtk', 'blobtk.*',
                               'using.*svirlpool', 'svirlpool.*',
                               'using.*mm2-ivh', 'mm2.*',
                               'using.*breakinator', 'breakinator.*',
                               'using.*pathogensurveillance',
                               'using.*check_samplesheet']):
        ax3 = 5
    else:
        ax3 = 0

    # Axis 4: I/O and filesystem complexity (0-10)
    ax4 = 0
    # Complex: downloads, intermediate files, external data
    if any(x in q for x in ['download_geo_dataset', 'download tcga', 'tcgabiolinks',
                             'download.*database', 'download.*ncbi',
                             '16s.*database preparation pipeline',
                             'run.*database preparation',
                             'snakemake.*workflow',
                             'workflow.*profile.*config',
                             'ovo scheduler']):
        ax4 = 10
    # Multiple files, navigation
    elif any(x in q for x in ['18 deg tables', '18 deg', '18 differentially',
                               'six deseq2', '6 files', 'six files',
                               'multiple files', 'three files', '54.*pdb',
                               'all.*pdb files', 'all pdb files',
                               'merge.*files', 'merge.*multiple',
                               'concatenate.*genomes', 'combine.*three',
                               'three.*kcf files', 'three kcf',
                               'combine.*kcf',
                               'four raw reference', '4 raw',
                               'all four.*databases', '4 databases',
                               'two platforms', 'platform a.*platform b',
                               'both platforms', 'two protein',
                               'two files', 'load.*and.*and',
                               'expression matrix.*metadata.*highly',
                               'load.*from.*and.*from',
                               'genomes directory.*selections directory',
                               'reference.*selections',
                               'gff files.*pirate',
                               'data.*and.*metadata.*and',
                               'both.*files',
                               '18.*tables',
                               'all 18',
                               'per-year results',
                               'multiple.*directories',
                               'config.*multiple',
                               'several.*files']):
        ax4 = 5
    else:
        ax4 = 0

    total = ax1 + ax2 + ax3 + ax4
    return total, ax1, ax2, ax3, ax4


# Now define rationale generator
def make_rationale(question_text, biorxiv_link, score, ax1, ax2, ax3, ax4):
    q = question_text.lower()
    parts = []

    if ax1 >= 30:
        parts.append("requires large model download (ESM-2, scGPT or similar >500MB foundation model)")
    elif ax1 == 20:
        parts.append("involves medium-weight ML model (PPLM/CrossPPI ESM-2 based, MLP/MPN training)")
    elif ax1 == 10:
        parts.append("uses small pre-trained weights or pre-generated embeddings already in repo")
    else:
        parts.append("pure file I/O, no model weights needed")

    if ax2 >= 20:
        parts.append("complex environment with PyTorch or multiple specialty bioinformatics packages")
    elif ax2 == 10:
        parts.append("one non-trivial package required (scanpy, RDKit, pysam, etc.)")
    else:
        parts.append("standard Python/R libraries suffice")

    if ax3 >= 15:
        parts.append("slow runtime due to model training epochs or large-scale pipeline")
    elif ax3 >= 10:
        parts.append("moderate runtime for pipeline execution or multi-step tool invocation")
    elif ax3 == 5:
        parts.append("fast execution with simple computations")
    else:
        parts.append("near-instant execution")

    return "; ".join(parts[:2]) + "."


# Score all CSV questions
scored_csv = []
for (qid, link, question, gt) in csv_questions:
    total, ax1, ax2, ax3, ax4 = score_question(question, link, gt)
    rationale = make_rationale(question, link, total, ax1, ax2, ax3, ax4)
    scored_csv.append({
        'question_id': qid,
        'biorxiv_link': link,
        'question': question,
        'ground_truth': gt,
        'difficulty_score': total,
        'rationale': rationale,
        'ax1': ax1, 'ax2': ax2, 'ax3': ax3, 'ax4': ax4
    })

# Print distribution
scores_list = [x['difficulty_score'] for x in scored_csv]
from collections import Counter
dist = Counter(scores_list)
print("Score distribution (285 CSV questions):")
for s in sorted(dist.keys()):
    print("  {}: {} questions".format(s, dist[s]))

print("\nMin: {}, Max: {}".format(min(scores_list), max(scores_list)))
print("\nFirst 5 items:")
for item in scored_csv[:5]:
    print("  {}: score={} ({},{},{},{}) | {}".format(
        item['question_id'], item['difficulty_score'],
        item['ax1'], item['ax2'], item['ax3'], item['ax4'],
        item['question'][:70]))
