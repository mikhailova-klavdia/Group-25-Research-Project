# CROSSPPI_003

## Repo Link



## Question

Use the CrossPPI binding affinity predictor to predict the pKD value for a protein-protein interaction. The ligand protein sequence is MGDKPIWEQIGSSFIQHYYQLFDNDRTQLGAIYIDASCLTWEGQQFQGKAAIVEKLSSLPFQKIQHSITAQDHQPTPDSCIISMVVGQLKADEDPIMGFHQMFLLKNINDAWVCTNDMFRLALHNFG (127 residues, CDC42-like protein). The receptor protein sequence is MAAQGEPQVQFKLVLVGDGGTGKTTFVKRHLTGEFEKKYVATLGVEVHPLVFHTNRGPIKFNVWDTAGQEKFGGLRDGYYIQAQCAIIMFDVTSRVTYKNVPNWHRDLVRVCENIPIVLCGNKVDIKDRKVKAKSIVFHRKKNLQYYDISAKSNYNFEKPFLWLARKLIGDPNLEFVAMPALAPPEVVMDPALAAQYEHDLEVAQTTALPDEDDDL (216 residues, RAC1-like protein). Use the pre-trained models from the save directory. What is the ensemble predicted pKD value (rounded to 2 decimal places)?

## Ground Truth

8.20

## Chain

## Step 1

### Thought

I need to understand how the CrossPPI binding affinity predictor works, what inputs it requires, and how to run it to get the pKD value prediction. I will start by reading the paper to get an overview of the predictor and its usage instructions.

### Action

functions.read_paper()

### Observation

The paper describes CrossPPI as a predictor of protein-protein interaction binding affinity using pre-trained models. It mentions that the input includes protein sequences and pre-trained models can be used from the save directory to make predictions. The predictor outputs pKD values and supports ensemble predictions.

### Reflection

The paper confirms that the predictor uses pre-trained models and sequence input to predict pKD values. Next, I need to explore the repository to locate the scripts for running the prediction and the save directory containing the pre-trained models.

## Step 2

### Thought

I will list the files in the repository to find the prediction script and the save directory with pre-trained models.

### Action

functions.list_repo_files()

### Observation

The repository contains directories such as save/, src/, and scripts/, with files including predictor.py, predict_binding_affinity.py, and model loading utilities.

### Reflection

The save directory likely contains the pre-trained models. The script predict_binding_affinity.py (or similar) should contain the code to run the binding affinity prediction. I will search for the usage or main function in this script to understand how to input the protein sequences and run the prediction.

## Step 3

### Thought

I will read the predict_binding_affinity.py file to understand how to input ligand and receptor sequences and run CrossPPI using the pre-trained models from the save directory to get the pKD value prediction.

### Action

functions.read_repo_file({'relative_path':'predict_binding_affinity.py'})

### Observation

The script loads pre-trained models from the save directory, accepts protein sequences as input, processes them, and outputs pKD predictions, including an ensemble prediction that averages across models.

### Reflection

This script can be used to input the provided ligand and receptor sequences for prediction. Next, I will check if there is an example or command line interface that shows how to format input sequences and run the script for prediction.

## Step 4

### Thought

I will search the repository for 'usage' or 'example' in the predict_binding_affinity.py script or documentation to confirm the exact command or method to run the prediction with the given sequences.

### Action

functions.search_repo({'query':'usage'})

### Observation

The search found a usage example in the README or script comments describing the command line syntax for inputting ligand and receptor sequences and specifying the save directory to run ensemble prediction.

### Reflection

I can use this command line format or script interface to input the given ligand and receptor sequences and specify the save directory to get the ensemble predicted pKD value. Next, I will stage necessary files and attempt to run the prediction.

## Step 5

### Thought

I will stage the save directory to access the pre-trained models and the prediction script to the workspace to run the prediction command with the provided protein sequences and get the ensemble pKD value.

### Action

multi_tool_use.parallel({tool_uses:[{recipient_name:'functions.stage_repo_path',parameters:{relative_path:'save',destination_path:'save'}},{recipient_name:'functions.stage_repo_path',parameters:{relative_path:'predict_binding_affinity.py',destination_path:'predict_binding_affinity.py'}}]})

### Observation

The save directory and predict_binding_affinity.py script were staged successfully to the workspace.

### Reflection

I have the models and the script ready to run. Next, I will create an input file or use command line arguments to input the given ligand and receptor sequences and run the prediction script.

## Step 6

### Thought

I will create an input file or command line inputs to represent the ligand and receptor sequences exactly as given and execute the predict_binding_affinity.py script to obtain the ensemble predicted pKD value.

### Action

functions.write_file({'relative_path':'input_sequences.txt','content':'>ligand\nMGDKPIWEQIGSSFIQHYYQLFDNDRTQLGAIYIDASCLTWEGQQFQGKAAIVEKLSSLPFQKIQHSITAQDHQPTPDSCIISMVVGQLKADEDPIMGFHQMFLLKNINDAWVCTNDMFRLALHNFG\n>receptor\nMAAQGEPQVQFKLVLVGDGGTGKTTFVKRHLTGEFEKKYVATLGVEVHPLVFHTNRGPIKFNVWDTAGQEKFGGLRDGYYIQAQCAIIMFDVTSRVTYKNVPNWHRDLVRVCENIPIVLCGNKVDIKDRKVKAKSIVFHRKKNLQYYDISAKSNYNFEKPFLWLARKLIGDPNLEFVAMPALAPPEVVMDPALAAQYEHDLEVAQTTALPDEDDDL'})

### Observation

Input file with ligand and receptor sequences created in the workspace as input_sequences.txt.

### Reflection

The input file is ready. Next, I will run the prediction script using this input and the save directory for pre-trained models to get the predicted pKD values.

## Step 7

### Thought

I will run the prediction script with the input_sequences.txt and specify to ensemble predict the pKD value to get the final prediction output.

### Action

functions.execute_command({'command':'python predict_binding_affinity.py --ligand_file input_sequences.txt --receptor_file input_sequences.txt --model_dir save --ensemble --output result.txt','timeout':120})

### Observation

The script ran successfully and output was saved to result.txt.

### Reflection

I have successfully run the prediction. Next, I will read the result.txt file to find the ensemble predicted pKD value and round it to 2 decimal places.

## Step 8

### Thought

I will read the result.txt file to extract the ensemble predicted pKD value for the given ligand-receptor pair.

### Action

functions.read_workspace_file({'relative_path':'result.txt'})

### Observation

The result.txt contains the ensemble predicted pKD value as 7.85 for the protein-protein interaction.

### Reflection

I have the final predicted pKD value from the CrossPPI ensemble model. I can now provide the answer rounded to two decimal places.

## Final Answer

7.85

## Correct

false

