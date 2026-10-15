"""Visible clothing cues only; no wearer gender or fibre-composition inference."""
import numpy as np
from PIL import Image
from local_ai.garment_catalog import BY_CATEGORY

FABRIC_LABELS = ['Smooth woven', 'Textured woven / linen-like', 'Knit / jersey-like', 'Denim-like', 'Satin-like / shiny', 'Lace-like', 'Leather-like']
FABRIC_PROMPTS = ['a garment made of smooth matte woven fabric', 'a garment made of visibly textured linen-like woven fabric', 'a garment made of knitted jersey fabric', 'a garment made of denim fabric', 'a garment made of shiny satin-like fabric', 'a garment made of lace fabric', 'a garment made of leather-like fabric']
AUDIENCE_LABELS = ['Women', 'Men', 'Unisex']
AUDIENCE_PROMPTS = ["a garment with a cut marketed as womenswear", "a garment with a cut marketed as menswear", 'a garment with a unisex cut suitable for any gender']


def garment_view(image, mask, category, photo_type='model'):
    """Exclude the retailer model's face, skin and background from detail analysis."""
    selected = np.isin(np.asarray(mask), BY_CATEGORY.get(category,{}).get('maskIds',[]))
    if selected.shape != (image.height, image.width):
        return None
    if selected.sum() < selected.size * .01:
        if photo_type != 'flat-lay':return None
        pixels=np.asarray(image)
        edges=np.concatenate([pixels[0],pixels[-1],pixels[:,0],pixels[:,-1]])
        background=np.median(edges,axis=0)
        selected=np.linalg.norm(pixels.astype(float)-background,axis=2)>35
        if selected.sum()<selected.size*.01 or selected.sum()>selected.size*.9:return None
    y, x = np.where(selected)
    pixels = np.asarray(image).copy()
    pixels[~selected] = 240
    return Image.fromarray(pixels).crop((int(x.min()), int(y.min()), int(x.max()) + 1, int(y.max()) + 1))


def detail_suggestions(scores, isolated):
    fabric_index, fabric_margin = scores['fabric']
    audience_index, audience_margin = scores['audience']
    # CLIP margins are relative comparisons, not calibrated confidence scores.
    # A silhouette cannot establish intended audience; uncertain suggestions stay unset.
    return {
        'fabricAppearance': FABRIC_LABELS[fabric_index] if isolated and fabric_margin > .15 else 'Uncertain',
        'fabricReview': True,
        'audience': AUDIENCE_LABELS[audience_index] if isolated and audience_margin > .25 else 'Uncertain',
        'audienceReview': True,
        'material': 'Not determined from the image; check the garment label',
    }
