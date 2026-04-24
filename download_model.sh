#!/bin/bash

# Create directory
mkdir -p ./model_cache/all-MiniLM-L6-v2
mkdir ./model_cache/all-MiniLM-L6-v2/1_Pooling
mkdir ./model_cache/all-MiniLM-L6-v2/onnx
mkdir ./model_cache/all-MiniLM-L6-v2/openvio

cd ./model_cache/all-MiniLM-L6-v2

# Base URL
BASE_URL="https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main"

# Download all essential files
files=(
    "config.json"
    "data_config.json"
    "model.safetensors"
    "pytorch_model.bin"
    "rust_model.ot"
    "tf_model.h5"
    "train_script.py"
    "tokenizer.json"
    "tokenizer_config.json"
    "vocab.txt"
    "sentence_bert_config.json"
    "config_sentence_transformers.json"
    "special_tokens_map.json"
    "modules.json"
    "README.md"
    "1_Pooling/config.json"
    "onnx/model.onnx"
    "onnx/model_O1.onnx"
    "onnx/model_O2.onnx"
    "onnx/model_O3.onnx"
    "onnx/model_O4.onnx"
    "onnx/model_qint8_arm64.onnx"
    "onnx/model_qint8_avx512.onnx"  
    "onnx/model_qint8_avx512_vnni.onnx" 
    "onnx/model_quint8_avx2.onnx"
    "openvio/openvino_model.bin"
    "openvio/openvino_model.xml"
    "openvio/openvino_model_qint8_quantized.bin"
    "openvio/openvino_model_qint8_quantized.xml"
)

for file in "${files[@]}"; do
    echo "Downloading $file..."
    curl -L -o "$file" "$BASE_URL/$file"
done

echo "Download complete!"

