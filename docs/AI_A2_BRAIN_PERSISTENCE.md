# Memingo AI — A2: Saveable meme brains

A2 makes the A1.9 sequential model reusable across runs. A Memingo "brain" can now be saved as a portable, versioned `.mgoai` file and loaded back into a trainable sequential model.

## Example

```mgo
vibe hidden = ai.dense(2, 4, "tanh", 21)
vibe output = ai.dense(4, 1, "sigmoid", 22)
vibe brain = ai.sequential([hidden, output])

ai.save_brain(brain, "models/my-brain.mgoai")
vibe loaded = ai.load_brain("models/my-brain.mgoai")
spill ai.to_list(ai.forward(loaded, [[0, 1]]))
```

## What is stored

- Dense layer order and dimensions
- Activation for each layer
- Weight matrices and bias vectors

Loading recreates trainable tensors with gradient tracking enabled. It validates the file before returning the model. Saving uses a temporary file and atomic replacement to avoid leaving a half-written checkpoint.

## File contract

- Format identifier: `memingo.sequential`
- Format version: `1`
- Extension convention: `.mgoai`
- Maximum file size: 16 MiB
- Maximum layers: 128
- Maximum parameters: 1,000,000
- Only dense sequential layers are supported in this version
- File paths must remain inside the active project directory

Malformed JSON, unknown format/version, invalid activation, disconnected layers, wrong parameter shapes, non-finite values, and oversized models are rejected.

## Public API

- `ai.save_brain(model, path)`
- `ai.load_brain(path)`

## Not included yet

A2 stores model architecture and weights, not optimizer state, Adam moments, dataset data, or training history. Training resume/checkpoint support and package sharing are later stages.
