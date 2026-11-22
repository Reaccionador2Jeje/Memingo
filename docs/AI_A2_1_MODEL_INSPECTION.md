# Memingo AI — A2.1: Model inspection

A2.1 adds a small introspection API for native sequential dense models. Scripts can inspect a brain's shape, layer activations, and parameter count without reaching into implementation internals.

## Example

```mgo
vibe hidden = ai.dense(2, 4, "tanh", 21)
vibe output = ai.dense(4, 1, "sigmoid", 22)
vibe brain = ai.sequential([hidden, output])

vibe info = ai.summary(brain)
spill info.layers
spill info.parameters
spill info.layer_details
```

## Summary fields

- `type`: currently `sequential`
- `layers`: number of dense layers
- `input_features` and `output_features`: model input and output widths
- `parameters`: total weights and biases
- `trainable_parameters`: parameters registered for training
- `layer_details`: ordered per-layer dimensions, activation, and parameter count

The result is a plain Memingo object and can be serialized with `json_stringify`.

## Current scope

This API describes the existing CPU sequential dense model. It does not inspect optimizer state, datasets, or training history. Unsupported model types are rejected rather than silently summarized.
