# Day 1 – Machine Learning Internship

## Iris Dataset Classification

This project demonstrates a beginner-level machine learning workflow using the built-in Iris dataset from scikit-learn.

### Objective

The goal is to:

- Load and explore a dataset
- Separate features and target
- Split data into training and testing sets
- Train a Decision Tree classification model
- Make predictions
- Evaluate the model using accuracy

### Tech Stack

- Python 3.x
- Jupyter Notebook
- NumPy
- pandas
- scikit-learn
- Git & GitHub

### Machine Learning Workflow

```text
Iris Dataset
     ↓
Feature / Target Separation
     ↓
Train/Test Split
     ↓
Decision Tree Training
     ↓
Prediction
     ↓
Accuracy Evaluation
```

### How to Run

1. Install Python/Anaconda.
2. Install the required packages:

```bash
pip install numpy pandas scikit-learn jupyter
```

3. Open `day1_iris_ml.ipynb` in Jupyter Notebook or VS Code.
4. Run the cells from top to bottom.
5. Check the printed accuracy and classification report.

### Model

The project uses `DecisionTreeClassifier` from scikit-learn.

The dataset is split into:

- 80% training data
- 20% testing data

A fixed `random_state=42` is used so the split and result are reproducible.

### Expected Result

The notebook should train successfully and print an accuracy score. The exact score can vary if the data split or model settings are changed.

### Learning Outcome

This exercise demonstrates the basic ML workflow:

**Data → Model Training → Prediction → Evaluation**

It also reinforces why test data should be kept separate from training data.

## Author

Muhammad Asif Nawaz
