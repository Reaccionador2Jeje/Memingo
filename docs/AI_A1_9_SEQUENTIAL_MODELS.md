# AI A1.9 — Sequential models

Memingo's native CPU tensor engine can now compose dense layers into a small sequential neural model and train it with reverse-mode autograd.

## Meme-brain example

```mgo
vibe hidden = ai.dense(2, 4, "tanh", 21)
vibe output = ai.dense(4, 1, "sigmoid", 22)
vibe brain = ai.sequential([hidden, output])

vibe report = ai.train_loop(
    brain,
    [[0, 0], [0, 1], [1, 0], [1, 1]],
    [[0], [1], [1], [0]],
    100,
    0.1,
    "adam"
)
spill report.loss
spill ai.to_list(ai.forward(brain, [[0, 1]]))
```

## API

- `ai.dense(in_features, out_features, activation, seed?)`: create trainable weights and bias.
- `ai.sequential(layers)`: validate and compose dense layers.
- `ai.forward(model, inputs)`: run a rank-2 batch.
- `ai.parameters(model)`: get trainable tensors.
- `ai.train_loop(model, inputs, targets, epochs?, learning_rate?, optimizer?)`: full-batch supervised training.

Activation choices are `relu`, `sigmoid`, `tanh`, and `linear`. Optimizer choices are `sgd` and `adam`. The training report includes `epochs`, `loss`, `initial_batch_loss`, and `samples`.

## Limits

CPU-only, rank-2 batches, dense layers, full-batch training, first-order gradients. Epochs are limited to 10,000 per call. Mini-batch scheduling, dropout, convolution, recurrent/transformer blocks, GPU support, and optimizer checkpoint serialization are not included in A1.9.
