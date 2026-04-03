import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

model_id = "meta-llama/Llama-3.2-1B-Instruct"

# Load tokenizer + model
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    dtype=torch.bfloat16,
    device_map="mps" if torch.backends.mps.is_available() else "cpu",
)

# Strong instruction framing (important for base model)
prompt = (
    "Answer the question clearly and concisely in 3 sentences.\n\n"
    "What are the potential common reasons for customer churn in the reviews?\n"
)

# Tokenize
inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

# Generate (deterministic to avoid rambling)
with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=500,
        do_sample=True,    # Greedy decoding (less rambling)
    )

# Decode only new tokens
generated_tokens = outputs[0][inputs["input_ids"].shape[-1]:]
response = tokenizer.decode(generated_tokens, skip_special_tokens=True)

print(response)