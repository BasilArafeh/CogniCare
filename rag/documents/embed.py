import chromadb
from openai import OpenAI
import json
from dotenv import load_dotenv
import os 
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)
chroma_client = chromadb.Client()

collection = chroma_client.get_or_create_collection(
    name="documents_collection"
)

def embed_text(text):
    return client.embeddings.create(
        model="text-embedding-3-large",
        input=text
    ).data[0].embedding



def load_and_store(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)

    for chunk in data:
        text_to_embed = chunk["embedding_text"]

        embedding = embed_text(text_to_embed)

        collection.add(
            ids=[chunk["id"]],
            documents=[text_to_embed],
            embeddings=[embedding],
            metadatas=[{
                "title": chunk["title"],
                "section": chunk["section"],
                "category": chunk["category"],
                "source": chunk["file_name"]
            }]
        )

    print(f"Embedded and stored {len(data)} chunks")


if __name__ == "__main__":
    
    collection.delete(where={})

    load_and_store("chunks.json")