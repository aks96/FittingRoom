"""Shared category routing and declared-profile checks; never infer wearer gender."""
import json
from pathlib import Path
CATALOG=json.loads((Path(__file__).resolve().parents[1]/'security/garment-catalog.json').read_text())
BY_CATEGORY={item['value']:item for item in CATALOG}

def native_category(category):
    item=BY_CATEGORY.get(category)
    if not item or not item['native']:
        raise ValueError('This garment is not supported. Choose one top, lower-body garment or one-piece outfit.')
    return item['native']

def compatibility_error(audience,profile):
    if profile not in ('Women','Men'):
        return 'Choose the wearer profile for this photo before starting. The app does not determine gender from a photo.'
    if audience not in ('Women','Men','Unisex'):
        return 'Confirm the garment’s intended clothing range first.'
    if audience!='Unisex' and audience!=profile:
        return f'This garment is confirmed as {audience}’s clothing, but the selected wearer profile is {profile}. Review the garment range or choose a matching person photo/profile before trying it on.'
    return None
