# A2.2 — Resumable training checkpoints

Memingo can save a sequential dense model together with its optimizer configuration
and state, then restore both to continue training.

```mgo
vibe hidden = ai.dense(2, 4, "tanh", 21)
vibe output = ai.dense(4, 1, "sigmoid", 22)
vibe brain = ai.sequential([hidden, output])
vibe optimizer = ai.adam(ai.parameters(brain), 0.01)

# Run your training steps with ai.backward and ai.step(optimizer).

ai.save_checkpoint(brain, optimizer, "models/xor.mgochk")
vibe restored = ai.load_checkpoint("models/xor.mgochk")
vibe brain_again = restored.model
vibe optimizer_again = restored.optimizer
```

The checkpoint format is versioned and includes the model's architecture/weights,
optimizer kind and learning rate, parameter shapes, and Adam's beta/epsilon
configuration, timestep, and first/second moment arrays. SGD stores its
configuration. Writes use a unique temporary file and atomic replacement.

Checkpoint paths are confined to the project directory. Files are limited to
32 MB, and model data is passed through the existing model loader's validation.
The checkpoint API currently supports sequential dense models with SGD or Adam.
Training data, gradients, epoch history, random-generator state, and mini-batch
sampler state are not stored; provide the same data and training order when
resuming if you want comparable results.
