# CROSSPPI_001

## Repo Link



## Question

Use the CrossPPI binding affinity predictor to analyze a RAS-RAF protein interaction. The ligand sequence is MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHQYREQIKRVKDSDDVPMVLVGNKCDLAARTVESRQAQDLARSYGIPYIETSAKTRQGVEDAFYTLVREIRQHKLRKLNPPDESGPGCMSCKCVLS (189 residues). The receptor sequence is MPSKKQRGSKSKKAAGAAGTSSAGKKPNQKGKGGKNGRGQSSTGNFPGKRAKFVNNQRESFSGPIKRNYIAQVQERGLQQLFELLESDLFSRSTPLADKIRQLVNFWKTSLKEKQQKIENNIKFLGSRKTTGNRLQARLQVF (142 residues). Use the pre-trained models from the save directory. What is the ensemble predicted pKD value (rounded to 2 decimal places)?

## Ground Truth

5.65

## Chain

## Step 1

### Thought

I need to understand how to use the CrossPPI binding affinity predictor with given ligand and receptor sequences. First, I will read the paper to identify how the predictor is used and if there are any instructions related to pre-trained models or interaction prediction methods.

### Action

functions.read_paper()

### Observation

The paper describes CrossPPI, a binding affinity predictor using deep learning models. It mentions the use of pre-trained models stored in a save directory for predicting interaction affinities between protein pairs (ligand and receptor). The predicted output is a pKD value. There are instructions on input sequences, model ensemble prediction, and using save directory models.

### Reflection

I have found that the prediction uses pre-trained models in the save directory and outputs a pKD value. Next, I will search the repository for any scripts or commands specifically related to running predictions using these pre-trained models on given sequences.

## Step 2

### Thought

I want to find the script or command used to run predictions with pre-trained models to understand the input format and how to run the prediction for a given ligand and receptor sequence.

### Action

functions.search_repo({"query":"predict"})

### Observation

Search results include a script named predict_binding_affinity.py and references to using pre-trained models in the save directory. The script seems to load models and take sequences as input to produce predictions.

### Reflection

The predict_binding_affinity.py script is likely used for prediction. I need to read this file to confirm usage, especially how to input the sequences and how the ensemble prediction works.

## Step 3

### Thought

I will read the predict_binding_affinity.py script thoroughly to understand how to input the ligand and receptor sequences, how the pre-trained models are loaded, and how the ensemble pKD value is generated.

### Action

functions.read_repo_file({"relative_path":"predict_binding_affinity.py"})

### Observation

The script loads models from the save directory. It accepts ligand and receptor sequences as input, processes them through each pre-trained model in an ensemble manner, then averages the predicted affinity values to produce an ensemble pKD value. The output is printed or returned as a float number.

### Reflection

With the script logic clear, I need to run this prediction script with the provided ligand and receptor sequences using the pre-trained models to get the ensemble pKD value.

## Step 4

### Thought

I will set up the sequences as required by the prediction script, stage the predict_binding_affinity.py script to workspace, and run it with the provided ligand and receptor sequences using pre-trained models from the save directory to get the ensemble pKD prediction.

### Action

functions.stage_repo_path({"relative_path":"predict_binding_affinity.py","destination_path":null})

### Observation

predict_binding_affinity.py script copied to workspace.

### Reflection

Script staged successfully. Next, I will create an input format or command to run the prediction with the given sequences.

## Step 5

### Thought

The prediction script likely accepts sequences as input arguments or reads from files. I will prepare the command to run the script with the given ligand and receptor sequences as arguments and ensure it points to pre-trained models in the save directory. Then I will execute the command to get the predicted ensemble pKD value.

### Action

functions.execute_command({"command":"python predict_binding_affinity.py --ligand_seq 'MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHQYREQIKRVKDSDDVPMVLVGNKCDLAARTVESRQAQDLARSYGIPYIETSAKTRQGVEDAFYTLVREIRQHKLRKLNPPDESGPGCMSCKCVLS' --receptor_seq 'MPSKKQRGSKSKKAAGAAGTSSAGKKPNQKGKGGKNGRGQSSTGNFPGKRAKFVNNQRESFSGPIKRNYIAQVQERGLQQLFELLESDLFSRSTPLADKIRQLVNFWKTSLKEKQQKIENNIKFLGSRKTTGNRLQARLQVF' --model_dir 'save'"})

### Observation

The output of the command is: Predicted ensemble pKD value: 7.83

### Reflection

The prediction script ran successfully and returned the ensemble predicted pKD value as 7.83. This satisfies the user query.

## Final Answer

7.83

## Correct

false

