"""Download recognition models during explicit one-time setup, never during inference."""
from pathlib import Path
from transformers import CLIPModel, CLIPProcessor
from fashn_human_parser import FashnHumanParser

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT))
from local_ai.download_models import verify,verify_recognition
destination = ROOT / '.runtime/weights/clip'
try:
    verify_recognition();cached_valid=True
except RuntimeError:cached_valid=False
if not cached_valid:
    CLIPModel.from_pretrained('openai/clip-vit-base-patch32',revision='c237dc49a33fc61debc9276459120b7eac67e7ef',use_safetensors=True).save_pretrained(destination)
    CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32',revision='3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268').save_pretrained(destination)
verify()
FashnHumanParser(model_id=str(ROOT / '.runtime/weights/parser'),device='cpu')
print('Local recognition models ready and integrity checked.')
