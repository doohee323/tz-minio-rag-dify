# CoinTutor app / custom tool

## Why IDs change every time

- **Node and edge IDs** (e.g. `1711528708197`, `1711528802931-1711528833796`): Dify assigns new ones on each export.
- **provider_id** (e.g. `a1744db9-36ab-44a2-abe2-20bcef718142`): Dify assigns a new UUID **each time** you create the custom tool in the UI. Without creating the tool via script/API, the value differs per environment.

The `CoinTutor.yml` in this repo is a **one-time export snapshot**, so in another Dify or after reinstall these IDs may not match.

## How to use in a new environment (recommended)

1. **Create the custom tool first**  
   - In Dify: **Tools → Custom → Create custom tool**  
   - Name: `CoinTutor RAG`  
   - Schema: paste the full contents of `cointutor-rag-openapi.yaml` → Save  

2. **Import the app**  
   - **Apps** → **Create app** → e.g. **Advanced chat**, then in **Settings** use **Import** to upload `CoinTutor.yml`  
   - Or manually build the workflow in an existing app to match this structure  

3. **Reconnect the tool only**  
   - After import, if a **Tool** node shows “tool not found”, open that node, in **Tool selection** choose the **CoinTutor RAG** you just created, and save  
   - It will then link to the current environment’s `provider_id`. **No need to edit IDs in the YAML.**

In short: **keep CoinTutor.yml as-is**; in a new environment do **create custom tool → import app → re-select CoinTutor RAG in the Tool node**.

## Files

| File | Purpose |
|------|---------|
| `cointutor-rag-openapi.yaml` | Paste as schema when registering the custom tool |
| `CoinTutor.yml` | Exported app file. For reference/import (after the steps above, re-select the tool in the Tool node) |
