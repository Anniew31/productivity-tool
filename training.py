from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer

model_name = "distilbert-base-uncased"
tokenizer = AutoTokenizer.from_pretrained(model_name)

ds = load_dataset("snats/url-classifications", data_files ="equally_distributed.csv")["train"]  # example dataset

ds_tok = ds.remove_columns([c for c in ds.column_names if c not in ["url", "classification"]])
ds_tok = ds_tok.filter(lambda x: x["url"] is not None and x["classification"] is not None)

splits = ds_tok.train_test_split(test_size=0.2, seed=42)
tmp = splits["test"].train_test_split(test_size=0.5, seed=42)
train_ds = splits["train"]
val_ds = tmp["train"]
test_ds = tmp["test"]

labels = sorted(set(train_ds["classification"]))
label2id = {l:i for i,l in enumerate(labels)}
id2label = {i:l for l,i in label2id.items()}

def encode_labels(batch):
    batch["labels"] = label2id[batch["classification"]]
    return batch

train_ds = train_ds.map(encode_labels)
val_ds   = val_ds.map(encode_labels)
test_ds  = test_ds.map(encode_labels)
from transformers import AutoTokenizer

model_name = "google/canine-s"  
tokenizer = AutoTokenizer.from_pretrained(model_name)

def tokenize(batch):
    return tokenizer(batch["url"], truncation=True, padding="max_length", max_length=128)

train_tok = train_ds.map(tokenize, batched=True)
val_tok   = val_ds.map(tokenize, batched=True)
test_tok  = test_ds.map(tokenize, batched=True)

cols = ["input_ids", "attention_mask", "labels"]
train_tok.set_format(type="torch", columns=cols)
val_tok.set_format(type="torch", columns=cols)
test_tok.set_format(type="torch", columns=cols)
import numpy as np
import evaluate
from transformers import AutoModelForSequenceClassification, TrainingArguments, Trainer

accuracy = evaluate.load("accuracy")

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return accuracy.compute(predictions=preds, references=labels)

model = AutoModelForSequenceClassification.from_pretrained(
    model_name,
    num_labels=len(labels),
    id2label=id2label,
    label2id=label2id,
)

args = TrainingArguments(
    output_dir="url-clf",
    learning_rate=2e-5,
    per_device_train_batch_size=32,
    per_device_eval_batch_size=64,
    num_train_epochs=3,
    eval_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="accuracy",
    fp16=True,  
    report_to="none",
)

trainer = Trainer(
    model=model,
    args=args,
    train_dataset=train_tok,
    eval_dataset=val_tok,
    compute_metrics=compute_metrics,
)

trainer.train()
model.save_pretrained("makeathon_model")
print(trainer.evaluate(test_tok))