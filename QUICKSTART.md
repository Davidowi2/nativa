# Nativa — Quick Start Guide

## What's Ready

✅ Project structure created at `C:\Users\Legacy\Documents\Nativa\`
✅ Context files: Architecture, Library-docs, Build-plan, Progress-tracker
✅ Colab notebook: `colab-training.ipynb` (abliterate + fine-tune + convert)
✅ Data collection: EURUSD (517 bars), XAUUSD (503 bars), BTC (1000 bars)
✅ Training dataset: 2541 examples (balanced BUY/SELL/HOLD)
✅ Dataset zipped: `nativa_dataset.zip` (221KB)

## What David Needs to Do

### Step 1: Create HuggingFace Token
1. Go to https://huggingface.co/settings/tokens
2. Create a new token (type: "Write")
3. Copy the token

### Step 2: Open Google Colab
1. Go to https://colab.research.google.com
2. Click "New Notebook"
3. Runtime → Change runtime type → GPU (T4)
4. Upload `colab-training.ipynb`

### Step 3: Run the Notebook
1. Run Cell 1 (install dependencies) — ~2 min
2. Run Cell 2 (check GPU) — verify T4
3. Run Cell 3 (download Qwen3.5-4B) — ~10 min
4. Run Cell 4 (test refusals) — ~2 min
5. Run Cell 5 (abliterate) — ~15-20 min
6. Run Cell 6 (upload dataset) — upload nativa_dataset.zip
7. Run Cell 7 (fine-tune) — ~30-60 min
8. Run Cell 8 (merge LoRA) — ~5 min
9. Run Cell 9 (convert to GGUF) — ~10 min
10. Run Cell 10 (quantize) — ~5 min
11. Run Cell 11 (download GGUF) — ~5 min
12. Run Cell 12 (upload to HuggingFace) — use your token

### Step 4: Deploy on VPS
1. Copy `nativa-Q4_K_M.gguf` to `C:\Tools\models\`
2. Run: `C:\Tools\llamacpp\llama-server.exe -m C:\Tools\models\nativa-Q4_K_M.gguf -c 32768 -t 10 --jinja --host 127.0.0.1 --port 8080 --no-warmup -ngl 0 --spec-type none`
3. Test: `curl http://localhost:8080/v1/chat/completions -d '{"messages":[{"role":"user","content":"What is EURUSD doing?"}]}'`

### Estimated Time: 2-3 hours on Colab (free T4)

### Notes
- The dataset is balanced (847 BUY, 847 SELL, 847 HOLD)
- Training data includes EURUSD, XAUUSD, BTCUSDT
- Risk management rules are encoded in the system prompt
- The model will be uncensored (abliterated) for trading decisions