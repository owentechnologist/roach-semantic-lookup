from project_utils import load_augmentation_text

# --- Example usage ---
if __name__ == "__main__":
    print("\nLOADING RAG DATA FROM ragdata.json into the vdb.llm_enrichment table...")
    load_augmentation_text()
    print("\nDONE!")
