# CROSSPPI_004

## Repo Link



## Question

Generate per-residue protein embeddings using the ESM-2 model for the KRAS protein sequence MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHQYREQIKRVKDSDDVPMVLVGNKCDLAARTVESRQAQDLARSYGIPYIETSAKTRQGVEDAFYTLVREIRQHKLRKLNPPDESGPGCMSCKCVLS with complex ID TEST003, using maximum sequence length of 1000 residues. What is the mean value of the first residue embedding vector (rounded to 4 decimal places)?

## Ground Truth

9.6298

## Chain

## Step 1

### Thought

To answer the question, I need to generate per-residue protein embeddings using the ESM-2 model for the given KRAS protein sequence and then calculate the mean value of the first residue embedding vector. First, I will check the paper or repository documentation to see if it mentions using the ESM-2 model and how to generate per-residue embeddings, especially for sequences up to 1000 residues.

### Action

functions.read_paper()

### Observation

The paper discusses ESM-2 models for protein sequence embeddings. It mentions using transformer models trained on protein sequences to generate embeddings, including for each residue. There is description of model architectures and embeddings extraction methods.

### Reflection

The paper covers the usage of the ESM-2 model for generating per-residue embeddings. I will now check the repository files to find relevant scripts or notebooks that demonstrate how to generate these embeddings, focusing on ESM-2 model usage with sequence length up to 1000.

## Step 2

### Thought

I will list repository files to identify scripts or notebooks related to generating embeddings with ESM-2 model.

### Action

functions.list_repo_files()

### Observation

Repository files include scripts like esm/script1.py, esm/embed.py, esm/esm2.py, and notebooks such as generating_embeddings.ipynb.

### Reflection

There appears to be a script for embeddings generation and possibly a notebook with instructions. I will check the embedding script esm/embed.py first for functionality to generate per-residue embeddings with sequence length control.

## Step 3

### Thought

Read esm/embed.py to see if it contains code for generating per-residue embeddings from ESM-2, handling sequence length limit, and outputting embeddings vectors.

### Action

functions.read_repo_file({"relative_path":"esm/embed.py"})

### Observation

The script esm/embed.py loads ESM-2 model, processes input sequences, and produces embeddings. It supports per-residue embeddings and has options for sequence length. Embeddings are output per residue as tensors, and it seems to provide a function to generate these.

### Reflection

The script can generate per-residue embeddings from a given protein sequence using ESM-2. I will stage this script to workspace to try running it with the KRAS sequence and using max sequence length 1000 to retrieve the embeddings.

## Step 4

### Thought

I will stage esm/embed.py to the workspace so I can run embedding extraction on the KRAS sequence using ESM-2 with the specified max sequence length 1000.

### Action

functions.stage_repo_path({"relative_path":"esm/embed.py","destination_path":null})

### Observation

Staging of esm/embed.py completed.

### Reflection

With the embedding extraction script staged, I need to create a small script or directly run a command to generate embeddings for the KRAS sequence and extract the first residue's embedding mean value.

## Step 5

### Thought

Prepare a Python script to run esm/embed.py or invoke relevant functions in it to generate the embeddings for sequence MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHQYREQIKRVKDSDDVPMVLVGNKCDLAARTVESRQAQDLARSYGIPYIETSAKTRQGVEDAFYTLVREIRQHKLRKLNPPDESGPGCMSCKCVLS with complex ID TEST003 and max sequence length 1000, and then calculate and print the mean of the first residue embedding.

### Action

functions.write_file({"relative_path":"run_embedding.py","content":"import torch\nfrom esm import pretrained\n\n# Load ESM-2 model and alphabet\nmodel, alphabet = pretrained.esm2_t33_650M_UR50D()\nmodel.eval()\n\nsequence = 'MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHQYREQIKRVKDSDDVPMVLVGNKCDLAARTVESRQAQDLARSYGIPYIETSAKTRQGVEDAFYTLVREIRQHKLRKLNPPDESGPGCMSCKCVLS'\nmax_len = 1000\n\n# Ensure sequence length is less than max_len\nassert len(sequence) <= max_len, 'Sequence length exceeds max_len'\n\n# Batch converter for single sequence\nbatch_converter = alphabet.get_batch_converter()\ndata = [('TEST003', sequence)]\nbatch_labels, batch_strs, batch_tokens = batch_converter(data)\n\nwith torch.no_grad():\n    results = model(batch_tokens, repr_layers=[model.num_layers], return_contacts=False)\n\n# Get per-residue embeddings from the last layer\nemeddings = results['representations'][model.num_layers]  # (batch_size, seq_len, feature_dim)\n\n# Remove BOS and EOS tokens for per-residue embeddings\nper_residue_embeddings = emeddings[0, 1:len(sequence)+1, :]\n\nfirst_residue_embedding = per_residue_embeddings[0]\nmean_first_residue = first_residue_embedding.mean().item()\n\nprint(f'Mean of the first residue embedding vector: {mean_first_residue:.4f}')\n"})

### Observation

run_embedding.py created successfully.

### Reflection

I have created a script to load the ESM-2 model, encode the KRAS sequence, get per-residue embeddings, and compute the mean of the first residue's embedding vector. Next, I will run this script.

## Step 6

### Thought

Run run_embedding.py to get the mean value of the first residue embedding vector.

### Action

functions.execute_command({"command":"python run_embedding.py","timeout":120})

### Observation

Mean of the first residue embedding vector: -0.0306

### Reflection

The script ran successfully, producing the mean of the first residue embedding vector as -0.0306. This is the answer to the question.

## Final Answer

-0.0306

## Correct

false

